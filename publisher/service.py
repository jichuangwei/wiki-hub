"""Narrow GitHub App bridge. No repository writes and no caller-selected URLs."""
from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import time
import uuid
import zipfile

from scripts.archive_report import archive_report
from scripts.archive_dispatch import read_inputs
from scripts.build_site import ReportParser, parse_issue, render_mail_body

REPO = "jichuangwei/wiki-hub"
WORKFLOW = "archive-report.yml"
PAGE = "https://jichuangwei.github.io/wiki-hub/"


class GitHub:
    def __init__(self, client, app_id: str, installation_id: str, private_key: str):
        self.client = client
        self.app_id = app_id
        self.installation_id = installation_id
        self.private_key = private_key

    def request(self, method, path, **kwargs):
        import jwt
        now = int(time.time())
        signed = jwt.encode({"iat": now - 60, "exp": now + 540, "iss": self.app_id},
                            self.private_key, algorithm="RS256")
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2026-03-10"}
        token_response = self.client.post(
            f"https://api.github.com/app/installations/{self.installation_id}/access_tokens",
            headers={**headers, "Authorization": f"Bearer {signed}"},
            json={"repositories": ["wiki-hub"],
                  "permissions": {"actions": "write", "contents": "read"}})
        if token_response.status_code != 201:
            raise RuntimeError(f"GitHub App authorization failed ({token_response.status_code})")
        response = self.client.request(method, f"https://api.github.com/repos/{REPO}/{path}",
            headers={**headers, "Authorization": f"Bearer {token_response.json()['token']}"}, **kwargs)
        # Never return GitHub request/response bodies containing credentials in errors.
        if response.status_code >= 400 and response.status_code != 404:
            raise RuntimeError(f"GitHub operation failed ({response.status_code}); query status before retry")
        return response


class Publisher:
    def __init__(self, github, client, database: Path):
        self.github, self.client, self.database = github, client, database
        database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS publications (request_id TEXT PRIMARY KEY, "
                       "start TEXT UNIQUE, end TEXT, digest TEXT, state TEXT, run_id INTEGER)")

    def connect(self):
        db = sqlite3.connect(self.database, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def publish(self, start: str, end: str, html: str) -> dict:
        read_inputs({"inputs": {"start": start, "end": end, "html": html}})
        # Reuse precisely the validation that runs inside Actions. Temporary HTML only.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.html"
            source.write_bytes(html.encode("utf-8"))
            archived, _ = archive_report(source, start, end, root=root / "reports")
            render_mail_body(html, parse_issue(archived).categories)
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
        request_id = uuid.uuid4().hex
        if sum(map(len, (start, end, html, request_id))) > 65535:
            raise ValueError("Combined workflow inputs exceed 65535 characters")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM publications WHERE start=?", (start,)).fetchone()
            if previous:
                if previous["digest"] != digest or previous["end"] != end:
                    raise ValueError("This week already has a different publication; correction requires review")
                return {"request_id": previous["request_id"], "state": previous["state"],
                        "run_id": previous["run_id"], "next_tool": "get_publication_status"}
            db.execute("INSERT INTO publications VALUES (?, ?, ?, ?, 'dispatch_unknown', NULL)",
                       (request_id, start, end, digest))
        # Reserve before the HTTP request. Lost responses and concurrent retries cannot double-dispatch.
        try:
            response = self.github.request("POST", f"actions/workflows/{WORKFLOW}/dispatches",
                json={"ref": "main", "inputs": {"start": start, "end": end, "html": html,
                                                 "request_id": request_id}})
            if response.status_code not in (200, 204):
                raise RuntimeError("Dispatch was not accepted")
            run_id = response.json().get("workflow_run_id") if response.status_code == 200 else None
            with self.connect() as db:
                db.execute("UPDATE publications SET state='dispatched', run_id=? WHERE request_id=?",
                           (run_id, request_id))
            return {"request_id": request_id, "state": "dispatched", "run_id": run_id,
                    "next_tool": "get_publication_status"}
        except Exception:
            return {"request_id": request_id, "state": "dispatch_unknown",
                    "next_tool": "get_publication_status",
                    "message": "Acceptance unconfirmed. Query this request; do not dispatch again."}

    def status(self, request_id: str) -> dict:
        if not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise ValueError("Invalid request ID")
        with self.connect() as db:
            row = db.execute("SELECT * FROM publications WHERE request_id=?", (request_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown request ID")
        run_id = row["run_id"]
        if run_id is None:
            # Compatibility with older dispatch responses (204); correlate unique run-name, never latest run.
            for page in range(1, 11):
                runs = self.github.request("GET", f"actions/workflows/{WORKFLOW}/runs",
                    params={"event": "workflow_dispatch", "branch": "main", "per_page": 100,
                            "page": page}).json()["workflow_runs"]
                matches = [r for r in runs if r.get("display_title") == f"Archive report {request_id}"]
                if matches:
                    if len(matches) != 1:
                        raise RuntimeError("Ambiguous publication runs")
                    run_id = matches[0]["id"]
                    break
                if len(runs) < 100:
                    break
            if run_id is None:
                return {"request_id": request_id, "state": row["state"], "commit_sha": None,
                        "pages": "unverified", "message": "Matching run not found; do not auto-retry"}
            with self.connect() as db:
                db.execute("UPDATE publications SET run_id=? WHERE request_id=?", (run_id, request_id))
        run = self.github.request("GET", f"actions/runs/{run_id}").json()
        if (run.get("display_title") != f"Archive report {request_id}" or
                run.get("event") != "workflow_dispatch" or run.get("head_branch") != "main" or
                run.get("path", "").split("@")[0] != f".github/workflows/{WORKFLOW}"):
            raise RuntimeError("Run does not match publication")
        result = {"request_id": request_id, "run_id": run_id, "action_url": run["html_url"],
                  "state": "action_failed" if run.get("conclusion") in ("failure", "cancelled", "timed_out") else "pending",
                  "action_status": run["status"], "action_conclusion": run.get("conclusion"),
                  "commit_sha": None, "pages": "unverified", "online_verified": False}
        artifacts = self.github.request("GET", f"actions/runs/{run_id}/artifacts").json()["artifacts"]
        artifact = next((a for a in artifacts if a["name"] == f"publication-{request_id}"
                         and not a["expired"]), None)
        if not artifact:
            return result
        response = self.github.request("GET", f"actions/artifacts/{artifact['id']}/zip")
        if len(response.content) > 65536:
            raise RuntimeError("Unexpected publication artifact size")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            info = archive.getinfo("publication.json")
            if info.file_size > 8192:
                raise RuntimeError("Unexpected publication metadata size")
            metadata = json.loads(archive.read(info))
        revision = metadata.get("revision", "")
        if (metadata.get("request_id") != request_id or metadata.get("sha256") != row["digest"] or
                metadata.get("start") != row["start"] or metadata.get("end") != row["end"] or
                not re.fullmatch(r"[a-f0-9]{40}", revision)):
            raise RuntimeError("Publication metadata mismatch")
        path = (f"content/news/reports/ai-agent-frontend/{row['start'][:4]}/"
                f"ai-agent-frontend-weekly-{row['start']}-to-{row['end']}.html")
        content = self.github.request("GET", f"contents/{path}", params={"ref": revision}).json()
        body = base64.b64decode(content["content"])
        if hashlib.sha256(body).hexdigest() != row["digest"]:
            raise RuntimeError("Archived content mismatch")
        result["commit_sha"] = revision
        if run["status"] != "completed" or run.get("conclusion") != "success":
            return result
        result["pages"] = "deployed"
        result["state"] = "deployed_unverified"
        try:
            online = self.client.get(PAGE)
        except Exception:
            result["message"] = "Pages deployed; online request failed. Query status again."
            return result
        if online.status_code != 200:
            return result
        match = re.search(r'<section class="weekly-report" data-week="' + row["start"] +
                          r'"[^>]*>(.*?)</section>', online.text, re.S)
        if not match:
            return result
        expected = ReportParser()
        expected.feed(body.decode("utf-8"))
        rendered = render_mail_body(body.decode("utf-8"), expected.categories)
        result["online_verified"] = bool(expected.articles) and match.group(1).strip() == rendered.strip()
        result["page_url"] = PAGE
        result["state"] = "published" if result["online_verified"] else "deployed_unverified"
        return result
