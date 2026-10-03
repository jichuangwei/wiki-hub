import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json
import hashlib
import subprocess

from scripts.archive_dispatch import main, read_inputs
from scripts.build_site import REPORTS


class ArchiveDispatchTests(unittest.TestCase):
    def test_missing_and_oversized_inputs_are_rejected(self):
        for values in ({}, {"start": "2026-09-21", "end": "2026-09-27", "html": 12},
                       {"start": "2026-09-21", "end": "2026-09-27", "html": "x" * 65536}):
            with self.assertRaises(ValueError):
                read_inputs({"inputs": values})

    def test_dispatch_preserves_html_and_retry_does_not_overwrite(self):
        source = REPORTS / "ai-agent-frontend/2026/week-39.html"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event, env = root / "event.json", root / "env"
            event.write_text(json.dumps({"inputs": {
                "start": "2026-09-21", "end": "2026-09-27", "html": original.decode("utf-8"),
            }}), encoding="utf-8")
            from scripts.archive_report import archive_report
            def archive(*args, **kwargs):
                kwargs.setdefault("root", root / "reports")
                return archive_report(*args, **kwargs)
            with patch.dict("os.environ", {"GITHUB_EVENT_PATH": str(event), "GITHUB_ENV": str(env)}), \
                 patch("scripts.archive_dispatch.archive_report", side_effect=archive):
                main()
                target = root / "reports/ai-agent-frontend/2026" / source.name
                self.assertEqual(target.read_bytes(), original)
                main()
                self.assertEqual(target.read_bytes(), original)
                changed = json.loads(event.read_text())
                changed["inputs"]["html"] += "\n"
                event.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    main()
                self.assertEqual(target.read_bytes(), original)
            self.assertIn("REPORT_START=2026-09-21\nREPORT_END=2026-09-27\n", env.read_text())

    def test_reviewed_archive_update_checks_digest_before_write(self):
        from scripts.archive_report import archive_report
        from test_deep_reports import deep_html
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.html"
            source.write_text(deep_html(), encoding="utf-8")
            target, _ = archive_report(source, "2026-08-31", "2026-09-06", root=root / "reports")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            source.write_text(deep_html() + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                archive_report(source, "2026-08-31", "2026-09-06", root=root / "reports", expected_sha256="f" * 64)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), digest)
            archive_report(source, "2026-08-31", "2026-09-06", root=root / "reports", expected_sha256=digest)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            with self.assertRaises(ValueError):
                archive_report(source, "2026-08-31", "2026-09-06", root=root / "reports", expected_sha256=digest)

    def test_action_refuses_mismatched_previous_commit_and_applies_reviewed_update(self):
        from scripts.archive_report import archive_report
        from test_deep_reports import deep_html
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.html"
            original = deep_html().encode()
            source.write_bytes(original)
            target, _ = archive_report(source, "2026-08-31", "2026-09-06", root=root / "reports")
            values = {"start": "2026-08-31", "end": "2026-09-06", "html": deep_html() + "\n",
                      "expected_sha256": hashlib.sha256(original).hexdigest(),
                      "expected_revision": "a" * 40, "review_reason": "Human approved"}
            event, env = root / "event.json", root / "env"
            event.write_text(json.dumps({"inputs": values}))
            def archive(*args, **kwargs):
                kwargs.setdefault("root", root / "reports")
                return archive_report(*args, **kwargs)
            with patch.dict("os.environ", {"GITHUB_EVENT_PATH": str(event), "GITHUB_ENV": str(env)}), \
                 patch("scripts.archive_dispatch.archive_report", side_effect=archive), \
                 patch("scripts.archive_dispatch.subprocess.check_output", return_value=b"changed") as git_show:
                with self.assertRaises(ValueError):
                    main()
                self.assertEqual(target.read_bytes(), original)
                self.assertFalse(env.exists())
                git_show.return_value = original
                main()
                self.assertEqual(target.read_text(), values["html"])
                git_show.assert_called_with(["git", "show", "a" * 40 +
                    ":content/news/reports/ai-agent-frontend/2026/week-36.html"], stderr=subprocess.DEVNULL)
                target.write_bytes(original)
                git_show.side_effect = [subprocess.CalledProcessError(128, "git show"), original]
                main()
                self.assertEqual(target.read_text(), values["html"])
                git_show.assert_called_with(["git", "show", "a" * 40 +
                    ":content/news/reports/ai-agent-frontend/2026/ai-agent-frontend-weekly-2026-08-31-to-2026-09-06.html"],
                    stderr=subprocess.DEVNULL)

    def test_incomplete_update_metadata_is_rejected(self):
        inputs = {"start": "2026-08-31", "end": "2026-09-06", "html": "body", "expected_sha256": "f" * 64}
        with self.assertRaises(ValueError):
            read_inputs({"inputs": inputs})

    def test_newline_in_date_does_not_reach_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event, env = root / "event.json", root / "env"
            event.write_text(json.dumps({"inputs": {
                "start": "2026-09-21\nINJECTED=yes", "end": "2026-09-27", "html": "<html></html>",
            }}), encoding="utf-8")
            with patch.dict("os.environ", {"GITHUB_EVENT_PATH": str(event), "GITHUB_ENV": str(env)}):
                with self.assertRaises(ValueError):
                    main()
            self.assertFalse(env.exists())
