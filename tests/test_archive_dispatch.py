import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json

from scripts.archive_dispatch import main, read_inputs
from scripts.build_site import REPORTS


class ArchiveDispatchTests(unittest.TestCase):
    def test_missing_and_oversized_inputs_are_rejected(self):
        for values in ({}, {"start": "2026-09-21", "end": "2026-09-27", "html": 12},
                       {"start": "2026-09-21", "end": "2026-09-27", "html": "x" * 65536}):
            with self.assertRaises(ValueError):
                read_inputs({"inputs": values})

    def test_dispatch_preserves_html_and_retry_does_not_overwrite(self):
        source = REPORTS / "ai-agent-frontend/2026/ai-agent-frontend-weekly-2026-09-21-to-2026-09-27.html"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event, env = root / "event.json", root / "env"
            event.write_text(json.dumps({"inputs": {
                "start": "2026-09-21", "end": "2026-09-27", "html": original.decode("utf-8"),
            }}), encoding="utf-8")
            from scripts.archive_report import archive_report
            def archive(*args):
                return archive_report(*args, root=root / "reports")
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
