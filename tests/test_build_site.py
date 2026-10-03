import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_site import REPORTS, ReportParser, build, parse_issue, render_mail_body

CURRENT_REPORT = REPORTS / "ai-agent-frontend/2026/ai-agent-frontend-weekly-2026-09-21-to-2026-09-27.html"
WEEK38_REPORT = REPORTS / "ai-agent-frontend/2026/ai-agent-frontend-weekly-2026-09-14-to-2026-09-20.html"


class BuildSiteTests(unittest.TestCase):
    def test_existing_report_contains_twelve_verified_items(self):
        issue = parse_issue(CURRENT_REPORT)
        self.assertEqual(issue.slug, "2026-09-21-to-2026-09-27")
        self.assertEqual(len(issue.categories), 5)
        self.assertEqual(len(issue.articles), 12)
        self.assertTrue(all(article.summary and article.sources for article in issue.articles))

    def test_build_generates_news_and_notes_with_the_latest_week(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build(output)
            pages = list(output.rglob("*.html"))
            self.assertEqual(set(pages), {output / "index.html", output / "news/index.html", output / "notes/index.html"})
            self.assertIn('content="0;url=news/"', (output / "index.html").read_text(encoding="utf-8"))
            home = (output / "news/index.html").read_text(encoding="utf-8")
            notes = (output / "notes/index.html").read_text(encoding="utf-8")
            expected = sum(len(parse_issue(path).articles) for path in REPORTS.glob("*/*/*.html"))
            self.assertEqual(home.count('data-kind="news"'), expected)
            self.assertIn('class="week-option" type="button" role="option" data-week="2026-09-21"', home)
            self.assertNotIn("<select", home)
            self.assertIn('data-category="AI/大模型"', home)
            self.assertNotIn('class="detail-dialog"', home)
            self.assertNotIn('class="news-card"', home)
            self.assertIn('class="site-header"', home)
            self.assertIn('href="../news/" aria-current="page"', home)
            self.assertIn('href="../notes/"', home)
            self.assertIn('href="../news/"', notes)
            self.assertIn('href="../notes/" aria-current="page"', notes)
            self.assertIn("暂无记录", notes)
            self.assertIn('class="content-empty" id="empty-state" hidden', home)
            self.assertIn('class="content-empty"', notes)
            self.assertIn('class="content-empty-icon"', home)
            self.assertIn('class="content-empty-icon"', notes)
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
            self.assertLess(home.index('>AI 资讯干货</h1>'), home.index('第 39 周</div>'))
            self.assertNotIn("{{", home)

    def test_week_switch_has_two_sets_of_items(self):
        source = CURRENT_REPORT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports" / "ai-agent-frontend" / "2026"
            reports.mkdir(parents=True)
            (reports / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            next_week = reports / "ai-agent-frontend-weekly-2026-09-28-to-2026-10-04.html"
            next_week.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            with patch("scripts.build_site.REPORTS", root / "reports"):
                build(root / "site")
            home = (root / "site/news/index.html").read_text(encoding="utf-8")
            self.assertEqual(home.count('data-kind="news"'), 24)
            self.assertEqual(home.count('class="weekly-report"'), 2)
            self.assertIn('data-week="2026-09-28" aria-label="第 40 周 · 2026.09.28—10.04">', home)
            self.assertIn('data-week="2026-09-21" aria-label="第 39 周 · 2026.09.21—09.27" hidden>', home)
            self.assertIn('role="option" data-week="2026-09-28"', home)
            self.assertIn('role="option" data-week="2026-09-21"', home)

    def test_mail_layout_preserves_every_article_and_source(self):
        source = CURRENT_REPORT
        issue = parse_issue(source)
        body = render_mail_body(source.read_text(encoding="utf-8"), issue.categories)
        parser = ReportParser()
        parser.feed(body)
        self.assertEqual([(a.title, a.sections, a.sources) for a in parser.articles],
                         [(a.title, a.sections, a.sources) for a in issue.articles])
        self.assertEqual(body.count('data-kind="news"'), 12)
        self.assertEqual(body.count('data-kind="section"'), 5)

    def test_week38_mail_keeps_content_and_filters_all_articles(self):
        original = WEEK38_REPORT.read_bytes()
        issue = parse_issue(WEEK38_REPORT)
        self.assertEqual(len(issue.articles), 10)
        self.assertEqual(len(issue.categories), 5)
        self.assertEqual(len(issue.highlights), 3)
        self.assertEqual(issue.summary, " ".join(issue.highlights))
        body = render_mail_body(original.decode("utf-8"), issue.categories)
        parser = ReportParser()
        parser.feed(body)
        self.assertEqual([(a.title, a.sections, a.sources) for a in parser.articles],
                         [(a.title, a.sections, a.sources) for a in issue.articles])
        self.assertEqual(body.count('data-kind="news"'), 10)
        self.assertEqual(body.count('data-kind="section"'), 5)
        conclusion = re.search(r'<h2\b[^>]*>一句话趋势总结', body)
        self.assertIsNotNone(conclusion)
        self.assertNotIn('data-category=', body[conclusion.start():])
        self.assertEqual(WEEK38_REPORT.read_bytes(), original)

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
            home = (root / "site/news/index.html").read_text(encoding="utf-8")
            self.assertIn('data-week="2026-09-28"', home)
            self.assertIn('data-category="产业观察"', home)
            self.assertEqual(len(list((root / "site").rglob("*.html"))), 3)


if __name__ == "__main__":
    unittest.main()
