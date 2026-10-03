import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.archive_report import archive_report
from scripts.build_site import DEEP_CATEGORY, build, parse_issue, render
from scripts.build_task_prompt import template_fragments


def deep_html(count=3):
    fragments = template_fragments()
    shell = fragments["邮件主模板"]
    values = {key: "测试内容" for key in re.findall(r"\{\{([^}]+)\}\}", shell)}
    values.update(DATE_RANGE="2026.08.31–09.06", WEEK_NO="36")
    rows = [render(fragments["栏目模板"], {"SECTION_LABEL": f"01 · {DEEP_CATEGORY}"})]
    for index in range(count):
        item = render(fragments["NEWS ITEM 资讯模板"], {
            "SOURCE_NAME": "测试机构", "DATE": "2026-09-01", "FULL_TITLE": f"深度资料 {index}",
            "FULL_SUMMARY": "摘要", "IMPACT": "影响", "OPTIONAL_IMAGES": "",
            "OPTIONAL_PRODUCT_SCENARIO": '<p><strong>证据强弱：</strong>厂商评测，待独立核验</p>'
                                         '<p><strong>前端实践：</strong>在真实仓库复现实验</p>',
            "SOURCE_LINKS": '<a href="https://example.com/source">一手来源</a>',
        })
        rows.append(item)
    values["SECTIONS_HTML"] = "".join(rows)
    return render(shell, values)


class DeepReportTests(unittest.TestCase):
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
