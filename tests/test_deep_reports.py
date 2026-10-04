import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.archive_report import archive_report
from scripts.build_site import DEEP_CATEGORY, EXPECTED_CATEGORIES, build, parse_issue, render
from scripts.build_task_prompt import template_fragments


def deep_html(count=3):
    fragments = template_fragments()
    shell = fragments["邮件主模板"]
    values = {key: "测试内容" for key in re.findall(r"\{\{([^}]+)\}\}", shell)}
    values.update(DATE_RANGE="2026.08.31–09.06", WEEK_NO="36")
    rows = [render(fragments["栏目模板"], {"SECTION_LABEL": f"01 · {DEEP_CATEGORY}"})]
    for index in range(count):
        item = render(fragments["NEWS ITEM 资讯模板"], {
            "TAG_1": "研究进展", "TAG_2": "开源", "DATE": "2026-09-01", "FULL_TITLE": f"深度资料 {index}",
            "FULL_SUMMARY": "摘要", "IMPACT": "影响", "OPTIONAL_IMAGES": "",
            "OPTIONAL_PRODUCT_SCENARIO": '<p><strong>证据强弱：</strong>厂商评测，待独立核验</p>'
                                         '<p><strong>前端实践：</strong>在真实仓库复现实验</p>',
            "SOURCE_LINKS": '<a href="https://example.com/source">一手来源</a>',
        })
        rows.append(item)
    values["SECTIONS_HTML"] = "".join(rows)
    return render(shell, values)


class DeepReportTests(unittest.TestCase):
    def test_combined_report_preserves_categories_and_enforces_counts(self):
        fragments = template_fragments()
        def combined_html(news_count=2, deep_count=3):
            shell = fragments["邮件主模板"]
            values = {key: "测试内容" for key in re.findall(r"\{\{([^}]+)\}\}", shell)}
            values.update(DATE_RANGE="2026.08.31–09.06", WEEK_NO="36")
            rows = []
            for number, category in enumerate([*EXPECTED_CATEGORIES, DEEP_CATEGORY], 1):
                rows.append(render(fragments["栏目模板"], {"SECTION_LABEL": f"{number:02d} · {category}"}))
                for index in range(deep_count if category == DEEP_CATEGORY else news_count):
                    rows.append(render(fragments["NEWS ITEM 资讯模板"], {
                        "TAG_1": "研究进展", "TAG_2": "开源", "DATE": "2026-09-01", "FULL_TITLE": f"{category} {index}",
                        "FULL_SUMMARY": "摘要", "IMPACT": "影响", "OPTIONAL_IMAGES": "",
                        "OPTIONAL_PRODUCT_SCENARIO": '<p><strong>证据强弱：</strong>证据</p><p><strong>前端实践：</strong>实践</p>' if category == DEEP_CATEGORY else "",
                        "SOURCE_LINKS": '<a href="https://example.com/source">来源</a>',
                    }))
            values["SECTIONS_HTML"] = "".join(rows)
            return render(shell, values)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.html"
            source.write_text(combined_html(), encoding="utf-8")
            path, _ = archive_report(source, "2026-08-31", "2026-09-06", root=root / "reports")
            issue = parse_issue(path)
            self.assertEqual(issue.categories, [*EXPECTED_CATEGORIES, DEEP_CATEGORY])
            self.assertEqual(len(issue.articles), 13)
            with patch("scripts.build_site.REPORTS", root / "reports"):
                build(root / "site")
            output = (root / "site/news/index.html").read_text()
            for category in issue.categories:
                self.assertIn(f'data-filter="{category}"', output)
            for html in (combined_html(news_count=1), combined_html(deep_count=2),
                         combined_html().replace("证据强弱", "其他")):
                source.write_text(html, encoding="utf-8")
                with self.assertRaises(ValueError):
                    archive_report(source, "2026-08-31", "2026-09-06", root=root / "invalid")

    def test_archive_and_site_accept_deep_format(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.html"
            source.write_text(deep_html(), encoding="utf-8")
            reports = root / "reports"
            path, _ = archive_report(source, "2026-08-31", "2026-09-06", root=reports)
            self.assertEqual(len(parse_issue(path).articles), 3)
            with patch("scripts.build_site.REPORTS", reports):
                build(root / "site")
            output = (root / "site/news/index.html").read_text()
            self.assertIn('data-week="2026-08-31"', output)
            self.assertIn("证据强弱", output)
            self.assertIn("前端实践", output)

    def test_deep_count_and_required_analysis_are_enforced(self):
        for html in (deep_html(2), deep_html(6), deep_html().replace("证据强弱", "其他")):
            with self.subTest(html=html[:40]), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "input.html"
                source.write_text(html, encoding="utf-8")
                with self.assertRaises(ValueError):
                    archive_report(source, "2026-08-31", "2026-09-06", root=Path(directory) / "reports")
