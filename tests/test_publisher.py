import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import zipfile

from publisher.service import Publisher
from scripts.build_site import DEEP_CATEGORY, render_mail_body
from test_deep_reports import deep_html


def response(data=None, status=200, content=b"", text=""):
    return Mock(status_code=status, json=lambda: data, content=content, text=text)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.github, self.client = Mock(), Mock()
        self.publisher = Publisher(self.github, self.client, Path(self.directory.name) / "db.sqlite3")
        self.html = deep_html()

    def publish(self):
        self.github.request.return_value = response({"workflow_run_id": 42})
        return self.publisher.publish("2026-08-31", "2026-09-06", self.html)

    def test_retry_and_conflict_never_double_dispatch(self):
        first = self.publish()
        second = self.publisher.publish("2026-08-31", "2026-09-06", self.html)
        self.assertEqual(first["request_id"], second["request_id"])
        self.github.request.assert_called_once()
        payload = self.github.request.call_args.kwargs["json"]
        self.assertEqual(payload["ref"], "main")
        self.assertEqual(payload["inputs"]["html"], self.html)
        with self.assertRaises(ValueError):
            self.publisher.publish("2026-08-31", "2026-09-06", self.html + "\n")

    def test_timeout_is_not_success_and_retry_does_not_dispatch(self):
        self.github.request.side_effect = TimeoutError()
        first = self.publisher.publish("2026-08-31", "2026-09-06", self.html)
        self.assertEqual(first["state"], "dispatch_unknown")
        self.assertEqual(self.publisher.publish("2026-08-31", "2026-09-06", self.html)["state"],
                         "dispatch_unknown")
        self.github.request.assert_called_once()

    def test_invalid_report_never_calls_github(self):
        with self.assertRaises(ValueError):
            self.publisher.publish("2026-08-31", "2026-09-06", deep_html(2))
        self.github.request.assert_not_called()

    def replacement_api(self, request_id, conclusion="failure", archive_status=404, repo_status=200):
        def api(method, path, **kwargs):
            if method == "POST":
                return response({"workflow_run_id": 43})
            if path.endswith("/artifacts"):
                return response({"artifacts": []})
            if path == "":
                return response({}, status=repo_status)
            if path.startswith("contents/"):
                return response({}, status=archive_status)
            return response({"display_title": f"Archive report {request_id}",
                "event": "workflow_dispatch", "head_branch": "main",
                "path": ".github/workflows/archive-report.yml", "status": "completed" if conclusion else "in_progress",
                "conclusion": conclusion, "html_url": "https://github.com/jichuangwei/wiki-hub/actions/runs/42"})
        self.github.request.reset_mock()
        self.github.request.side_effect = api

    def test_reviewed_failed_replacement_preserves_audit_and_retries_once(self):
        old = self.publish()["request_id"]
        self.replacement_api(old)
        newer = self.publisher.publish("2026-08-31", "2026-09-06", self.html + "\n", old, "Human approved reviewed HTML")
        self.assertNotEqual(old, newer["request_id"])
        self.assertEqual(newer["run_id"], 43)
        self.assertEqual(self.publisher.status(old)["replacement_request_id"], newer["request_id"])
        retry = self.publisher.publish("2026-08-31", "2026-09-06", self.html + "\n", old, "Same review")
        self.assertEqual(retry["request_id"], newer["request_id"])
        self.assertEqual(sum(call.args[0] == "POST" for call in self.github.request.call_args_list), 1)
        with self.publisher.connect() as db:
            audit = db.execute("SELECT * FROM publication_replacements").fetchone()
        self.assertEqual(json.loads(audit["previous_record"])["publication"]["request_id"], old)
        with self.assertRaises(ValueError):
            self.publisher.publish("2026-08-31", "2026-09-06", self.html + "\n\n", old, "Changed again")

    def test_replacement_accepts_authenticated_missing_repo_metadata(self):
        old = self.publish()["request_id"]
        self.replacement_api(old, "failure", 404, 404)
        newer = self.publisher.publish("2026-08-31", "2026-09-06", self.html + "\n", old, "Approved retry")
        self.assertNotEqual(old, newer["request_id"])

    def test_replacement_refuses_pending_success_archived_and_access_errors(self):
        old = self.publish()["request_id"]
        for conclusion, archive_status, repo_status in [(None, 404, 200), ("success", 404, 200),
                ("failure", 200, 200), ("failure", 403, 200)]:
            with self.subTest(conclusion=conclusion, archive_status=archive_status, repo_status=repo_status):
                self.replacement_api(old, conclusion, archive_status, repo_status)
                with self.assertRaises((ValueError, RuntimeError)):
                    self.publisher.publish("2026-08-31", "2026-09-06", self.html + "\n", old, "Human review")
                self.assertFalse(any(call.args[0] == "POST" for call in self.github.request.call_args_list))
                with self.publisher.connect() as db:
                    self.assertEqual(db.execute("SELECT request_id FROM publications").fetchone()[0], old)

    def test_replacement_requires_review_and_exact_request(self):
        old = self.publish()["request_id"]
        with self.assertRaises(ValueError):
            self.publisher.publish("2026-08-31", "2026-09-06", self.html, old)
        with self.assertRaises(ValueError):
            self.publisher.publish("2026-08-31", "2026-09-06", self.html, "f" * 32, "Human review")

    def test_replacement_timeout_keeps_one_new_request(self):
        old = self.publish()["request_id"]
        self.replacement_api(old)
        api = self.github.request.side_effect
        def timeout(method, path, **kwargs):
            if method == "POST":
                raise TimeoutError()
            return api(method, path, **kwargs)
        self.github.request.side_effect = timeout
        newer = self.publisher.publish("2026-08-31", "2026-09-06", self.html + "\n", old, "Human review")
        self.assertEqual(newer["state"], "dispatch_unknown")
        self.assertEqual(self.publisher.publish("2026-08-31", "2026-09-06", self.html + "\n", old,
                         "Human review")["request_id"], newer["request_id"])
        self.assertEqual(sum(call.args[0] == "POST" for call in self.github.request.call_args_list), 1)

    def test_replacement_resolves_legacy_dispatch_before_write_lock(self):
        old = self.publish()["request_id"]
        with self.publisher.connect() as db:
            db.execute("UPDATE publications SET run_id=NULL")
        self.replacement_api(old)
        api = self.github.request.side_effect
        def legacy(method, path, **kwargs):
            if path == "actions/workflows/archive-report.yml/runs":
                return response({"workflow_runs": [{"id": 42, "display_title": f"Archive report {old}"}]})
            return api(method, path, **kwargs)
        self.github.request.side_effect = legacy
        newer = self.publisher.publish("2026-08-31", "2026-09-06", self.html, old, "Approved retry on fixed workflow")
        self.assertEqual(newer["run_id"], 43)

    def test_historical_run_cannot_be_reported_as_this_publication(self):
        request = self.publish()
        self.github.request.return_value = response({"display_title": "Historical run", "event": "workflow_dispatch",
            "head_branch": "main", "path": ".github/workflows/archive-report.yml"})
        with self.assertRaises(RuntimeError):
            self.publisher.status(request["request_id"])

    def test_commit_deploy_and_online_are_verified_separately(self):
        request = self.publish()
        request_id = request["request_id"]
        with self.publisher.connect() as db:
            row = db.execute("SELECT * FROM publications").fetchone()
        revision = "a" * 40
        metadata = {"request_id": request_id, "start": row["start"], "end": row["end"],
                    "sha256": row["digest"], "revision": revision}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("publication.json", json.dumps(metadata))
        run = {"display_title": f"Archive report {request_id}", "event": "workflow_dispatch",
               "head_branch": "main", "path": ".github/workflows/archive-report.yml",
               "html_url": "https://github.com/jichuangwei/wiki-hub/actions/runs/42",
               "status": "completed", "conclusion": "success"}
        def api(*args, **kwargs):
            path = args[1]
            if path.endswith("/artifacts"):
                return response({"artifacts": [{"id": 1, "name": f"publication-{request_id}", "expired": False}]})
            if path.endswith("/zip"):
                return response(content=buffer.getvalue())
            if path.startswith("contents/"):
                self.assertEqual(kwargs["params"]["ref"], revision)
                return response({"content": base64.b64encode(self.html.encode()).decode()})
            return response(run)
        self.github.request.side_effect = api
        self.client.get.return_value = response(text="wrong week")
        status = self.publisher.status(request_id)
        self.assertEqual(status["commit_sha"], revision)
        self.assertEqual(status["state"], "deployed_unverified")
        rendered = render_mail_body(self.html, [DEEP_CATEGORY])
        self.client.get.return_value = response(text=f'<section class="weekly-report" data-week="2026-08-31">{rendered}</section>')
        self.assertEqual(self.publisher.status(request_id)["state"], "published")
        self.client.get.assert_called_with("https://jichuangwei.github.io/wiki-hub/news/2026-week-36/")
        self.client.get.side_effect = TimeoutError()
        self.assertEqual(self.publisher.status(request_id)["state"], "deployed_unverified")
        run["conclusion"] = "failure"
        self.assertEqual(self.publisher.status(request_id)["pages"], "unverified")
