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
        self.client.get.side_effect = TimeoutError()
        self.assertEqual(self.publisher.status(request_id)["state"], "deployed_unverified")
        run["conclusion"] = "failure"
        self.assertEqual(self.publisher.status(request_id)["pages"], "unverified")
