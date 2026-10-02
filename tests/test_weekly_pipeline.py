import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.archive_report import archive_report
from scripts.build_site import REPORTS, build, parse_issue, render, EXPECTED_CATEGORIES
from scripts.build_task_prompt import build_prompt, template_fragments

CURRENT_REPORT = REPORTS / "ai-agent-frontend/2026/ai-agent-frontend-weekly-2026-09-21-to-2026-09-27.html"


class WeeklyPipelineTests(unittest.TestCase):
    def test_archive_retry_preserves_bytes_and_rejects_overwrite(self):
        source = CURRENT_REPORT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "reports"
            path, created = archive_report(source, "2026-09-21", "2026-09-27", root=root)
            self.assertTrue(created)
            self.assertEqual(path.read_bytes(), source.read_bytes())
            self.assertFalse(archive_report(source, "2026-09-21", "2026-09-27", root=root)[1])
            correction = Path(directory) / "correction.html"
            correction.write_text(source.read_text() + "\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                archive_report(correction, "2026-09-21", "2026-09-27", root=root)
            self.assertEqual(path.read_bytes(), source.read_bytes())

    def test_invalid_week_is_not_archived(self):
        source = CURRENT_REPORT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "reports"
            with self.assertRaises(ValueError):
                archive_report(source, "2026-09-22", "2026-09-28", root=root)
            self.assertFalse(root.exists())

    def test_repository_template_can_generate_archivable_mail_and_new_week(self):
        prompt = build_prompt()
        self.assertLessEqual(len(prompt), 20000)
        self.assertNotIn("<!doctype", prompt)
        self.assertIn("templates/reports/ai-agent-frontend-weekly-email.html", prompt)
        fragments = template_fragments()
        def snippet(label):
            return fragments[label]
        values = {name: "测试内容" for name in re.findall(r"\{\{([^}]+)\}\}", snippet("邮件主模板"))}
        values["DATE_RANGE"] = "2026.09.28–10.04"
        values["WEEK_NO"] = "40"
        sections = []
        for index, category in enumerate(EXPECTED_CATEGORIES, 1):
            sections.append(render(snippet("栏目模板"), {"SECTION_LABEL": f"{index:02d} · {category}"}))
            for item in range(2):
                sections.append(render(snippet("NEWS ITEM 资讯模板"), {
                    "SOURCE_NAME": "测试来源", "DATE": "2026-09-29", "FULL_TITLE": f"测试资讯 {index}-{item}",
                    "FULL_SUMMARY": "测试摘要", "IMPACT": "测试影响", "OPTIONAL_IMAGES": "",
                    "OPTIONAL_PRODUCT_SCENARIO": "", "SOURCE_LINKS": '<a href="https://example.com/source">测试来源</a>',
                }))
        values["SECTIONS_HTML"] = "".join(sections)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "mail.html"
            source.write_text(render(snippet("邮件主模板"), values), encoding="utf-8")
            reports = root / "reports"
            archived, _ = archive_report(source, "2026-09-28", "2026-10-04", root=reports)
            self.assertEqual(len(parse_issue(archived).articles), 10)
            archive_report(CURRENT_REPORT, "2026-09-21", "2026-09-27", root=reports)
            with patch("scripts.build_site.REPORTS", reports):
                build(root / "site")
            home = (root / "site/index.html").read_text()
            self.assertIn('role="option" data-week="2026-09-28" aria-selected="true"', home)
            self.assertIn('role="option" data-week="2026-09-21" aria-selected="false"', home)
            self.assertEqual(home.count('data-kind="news"'), 22)
            self.assertEqual(archived.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
