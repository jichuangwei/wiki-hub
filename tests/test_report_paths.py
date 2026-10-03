import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.archive_report import archive_report
from scripts.build_site import REPORTS, parse_issue
from scripts.report_paths import repository_paths
from publisher.service import Publisher


class ReportPathTests(unittest.TestCase):
    def test_cross_year_archive_uses_iso_year_and_recovers_dates(self):
        source = REPORTS / 'ai-agent-frontend/2026/week-39.html'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target, _ = archive_report(source, '2025-12-29', '2026-01-04', root=root)
            self.assertEqual(target.relative_to(root).as_posix(), 'ai-agent-frontend/2026/week-1.html')
            issue = parse_issue(target)
            self.assertEqual(str(issue.start), '2025-12-29')
            self.assertEqual(str(issue.end), '2026-01-04')
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_legacy_archive_retry_reuses_existing_content(self):
        source = REPORTS / 'ai-agent-frontend/2026/week-39.html'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'ai-agent-frontend/2026/ai-agent-frontend-weekly-2026-09-21-to-2026-09-27.html'
            old.parent.mkdir(parents=True)
            old.write_bytes(source.read_bytes())
            self.assertEqual(parse_issue(old).start, parse_issue(source).start)
            target, created = archive_report(source, '2026-09-21', '2026-09-27', root=root)
            self.assertEqual(target, old)
            self.assertFalse(created)
            self.assertFalse((old.parent / 'week-39.html').exists())

    def test_publisher_reads_legacy_path_at_original_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            github = Mock()
            missing, found = Mock(status_code=404), Mock(status_code=200)
            github.request.side_effect = [missing, found]
            publisher = Publisher(github, Mock(), Path(directory) / 'db.sqlite3')
            self.assertIs(publisher.archive_response('2026-08-31', '2026-09-06', 'a' * 40), found)
            for call, path in zip(github.request.call_args_list, repository_paths('2026-08-31', '2026-09-06')):
                self.assertEqual(call.args, ('GET', f'contents/{path}'))
                self.assertEqual(call.kwargs['params'], {'ref': 'a' * 40})
