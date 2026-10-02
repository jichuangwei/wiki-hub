import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_site import REPORTS, ReportParser, build, parse_issue, render_mail_body


class BuildSiteTests(unittest.TestCase):
    def test_existing_report_contains_twelve_verified_items(self):
        issue = parse_issue(next(REPORTS.glob("*/*/*.html")))
        self.assertEqual(issue.slug, "2026-09-21-to-2026-09-27")
        self.assertEqual(len(issue.categories), 5)
        self.assertEqual(len(issue.articles), 12)
        self.assertTrue(all(article.summary and article.sources for article in issue.articles))

    def test_build_generates_only_a_homepage_with_the_latest_week(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build(output)
            pages = list(output.rglob("*.html"))
            self.assertEqual(pages, [output / "index.html"])
            home = pages[0].read_text(encoding="utf-8")
            self.assertEqual(home.count('data-kind="news"'), 12)
            self.assertIn('class="week-option" type="button" role="option" data-week="2026-09-21"', home)
            self.assertNotIn("<select", home)
            self.assertIn('data-category="AI/大模型"', home)
            self.assertNotIn('class="detail-dialog"', home)
            self.assertNotIn('class="news-card"', home)
            self.assertNotIn('class="site-header"', home)
            self.assertIn("一句话趋势总结", home)
            self.assertIn("本周动手验证", home)
            self.assertIn("团队行动建议", home)
            self.assertNotIn("<details", home)
            self.assertNotIn("<footer", home)
            self.assertNotIn("header-note", home)
            self.assertNotIn("WEEKLY NEWS", home)
            self.assertNotIn("最新资讯</h1>", home)
            self.assertNotIn('id="news-search"', home)
            self.assertNotIn('class="detail-open"', home)
            self.assertLess(home.index('class="category-tabs"'), home.index('id="week-trigger"'))
            self.assertIn("OpenAI 发布公告", home)
            self.assertNotIn("{{", home)

    def test_week_switch_has_two_sets_of_items(self):
        source = next(REPORTS.glob("*/*/*.html"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports" / "ai-agent-frontend" / "2026"
            reports.mkdir(parents=True)
            (reports / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            next_week = reports / "ai-agent-frontend-weekly-2026-09-28-to-2026-10-04.html"
            next_week.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            with patch("scripts.build_site.REPORTS", root / "reports"):
                build(root / "site")
            home = (root / "site/index.html").read_text(encoding="utf-8")
            self.assertEqual(home.count('data-kind="news"'), 24)
            self.assertEqual(home.count('class="weekly-report"'), 2)
            self.assertIn('data-week="2026-09-28" aria-label="第 40 周 · 2026.09.28—10.04">', home)
            self.assertIn('data-week="2026-09-21" aria-label="第 39 周 · 2026.09.21—09.27" hidden>', home)
            self.assertIn('role="option" data-week="2026-09-28"', home)
            self.assertIn('role="option" data-week="2026-09-21"', home)

    def test_mail_layout_preserves_every_article_and_source(self):
        source = next(REPORTS.glob("*/*/*.html"))
        issue = parse_issue(source)
        body = render_mail_body(source.read_text(encoding="utf-8"), issue.categories)
        parser = ReportParser()
        parser.feed(body)
        self.assertEqual([(a.title, a.sections, a.sources) for a in parser.articles],
                         [(a.title, a.sections, a.sources) for a in issue.articles])
        self.assertEqual(body.count('data-kind="news"'), 12)
        self.assertEqual(body.count('data-kind="section"'), 5)

    def test_independent_news_can_supply_a_week_without_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            news = root / "items" / "2026"
            news.mkdir(parents=True)
            (news / "industry-update.json").write_text('''{
              "date": "2026-09-30", "category": "产业观察", "title": "独立资讯示例",
              "source_name": "官方发布", "sections": [
                {"title": "摘要", "text": "可独立收录的资讯。"}
              ], "sources": [{"label": "原始来源", "url": "https://example.com/source"}]
            }''', encoding="utf-8")
            reports = root / "reports"
            reports.mkdir()
            with patch("scripts.build_site.NEWS", news.parent), patch("scripts.build_site.REPORTS", reports):
                build(root / "site")
            home = (root / "site/index.html").read_text(encoding="utf-8")
            self.assertIn('data-week="2026-09-28"', home)
            self.assertIn('data-category="产业观察"', home)
            self.assertEqual(len(list((root / "site").rglob("*.html"))), 1)


if __name__ == "__main__":
    unittest.main()
