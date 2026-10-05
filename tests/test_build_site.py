import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts.build_site import ARTICLE_REDIRECTS, NOTES, PRACTICES, REPORTS, ReportParser, build, parse_issue, render_mail_body, week_slug

CURRENT_REPORT = REPORTS / "ai-agent-frontend/2026/week-39.html"
WEEK38_REPORT = REPORTS / "ai-agent-frontend/2026/week-38.html"


def current_sections(sections):
    """Only the visible section labels change; keep every paragraph intact."""
    result = []
    for label, text in sections:
        if label.startswith("为什么值得关注") or re.match(r"对(?:前端|Agent).*影响", label):
            label = "影响与分析"
        elif label == "适用场景与理由":
            label = "适用场景"
        result.append((label, text))
    return result


class BuildSiteTests(unittest.TestCase):
    def test_week_path_uses_iso_week_year(self):
        self.assertEqual(week_slug(date(2025, 12, 29)), "2026-week-1")
        self.assertEqual(week_slug(date(2026, 9, 21)), "2026-week-39")

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
            expected_week_pages = {
                output / f"news/{week_slug(parse_issue(path).start)}/index.html"
                for path in REPORTS.glob("*/*/*.html")
            }
            expected_note_pages = {
                output / f"notes/{path.stem}/index.html"
                for path in NOTES.glob("*.md")
            }
            expected_practice_pages = {
                output / f"practices/{path.stem}/index.html"
                for path in PRACTICES.glob("*.md")
            }
            expected_redirect_pages = {
                output / old_path / "index.html" for old_path, new_path in ARTICLE_REDIRECTS.items()
                if output / new_path / "index.html" in expected_practice_pages
            }
            self.assertEqual(set(pages), {
                output / "index.html", output / "news/index.html", output / "notes/index.html", output / "practices/index.html",
            } | expected_week_pages | expected_note_pages | expected_practice_pages | expected_redirect_pages)
            landing = (output / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('http-equiv="refresh"', landing)
            self.assertIn('id="latest-heading"', landing)
            self.assertIn('href="news/2026-week-39/"', landing)
            self.assertIn('practices/chatgpt-automated-content-publishing/', landing)
            self.assertIn('notes/qq-mail-dark-mode-colors/', landing)
            home = (output / "news/index.html").read_text(encoding="utf-8")
            notes = (output / "notes/index.html").read_text(encoding="utf-8")
            self.assertEqual(home.count('data-kind="news"'), len(parse_issue(CURRENT_REPORT).articles))
            self.assertIn('href="../news/2026-week-39/" role="option" data-week="2026-09-21" data-week-path="2026-week-39"', home)
            self.assertIn('href="../news/2026-week-38/" role="option" data-week="2026-09-14" data-week-path="2026-week-38"', home)
            self.assertNotIn("<select", home)
            self.assertIn('data-category="AI/大模型"', home)
            self.assertNotIn('class="detail-dialog"', home)
            self.assertNotIn('class="news-card"', home)
            self.assertIn('class="site-header"', home)
            self.assertIn('href="../news/" aria-current="page"', home)
            self.assertIn('href="../notes/"', home)
            self.assertIn('href="../news/"', notes)
            self.assertIn('href="../notes/" aria-current="page"', notes)
            self.assertIn("QQ 邮箱深色模式与浏览器预览的文字颜色不一致", notes)
            self.assertIn('href="qq-mail-dark-mode-colors/"', notes)
            self.assertNotIn("github-pages-subpath-assets", notes)
            self.assertNotIn('class="notes-title"', notes)
            self.assertLess(notes.index('<h2>QQ 邮箱'), notes.index('<p>QQ 邮箱会自动转换'))
            self.assertLess(notes.index('<p>QQ 邮箱会自动转换'), notes.index('<time datetime="2026-10-04"'))
            detail = (output / "notes/qq-mail-dark-mode-colors/index.html").read_text(encoding="utf-8")
            self.assertRegex(detail, r'<h2(?: id="[^"]+")?>现象</h2>')
            self.assertIn('class="note-body"', detail)
            self.assertIn('href="../../assets/wiki-hub.css', detail)
            self.assertIn('class="content-empty" id="empty-state" hidden', home)
            self.assertIn('class="content-empty-icon"', home)
            self.assertIn("一句话总结", home)
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
            self.assertLess(home.index('>AI 资讯干货</h1>'), home.index('第 39 周&nbsp;&nbsp;/'))
            self.assertNotIn("{{", home)

    def test_practice_navigation_and_migrated_article_link(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            build(output)
            listing = (output / "practices/index.html").read_text(encoding="utf-8")
            detail = (output / "practices/chatgpt-automated-content-publishing/index.html").read_text(encoding="utf-8")
            redirect = (output / "notes/chatgpt-scheduled-weekly-report-publishing/index.html").read_text(encoding="utf-8")
            self.assertIn('href="../practices/" aria-current="page">实践经验', listing)
            self.assertIn('href="../" aria-current="page">实践经验', detail)
            self.assertIn('href="../../notes/">踩坑记录', detail)
            self.assertIn('href="chatgpt-automated-content-publishing/"', listing)
            self.assertIn('content="0;url=../../practices/chatgpt-automated-content-publishing/"', redirect)
            self.assertNotIn('chatgpt-scheduled-weekly-report-publishing/',
                             (output / "notes/index.html").read_text(encoding="utf-8"))
            self.assertNotIn("{{", detail)

    def test_week_switch_has_two_sets_of_items(self):
        source = CURRENT_REPORT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports" / "ai-agent-frontend" / "2026"
            reports.mkdir(parents=True)
            (reports / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            next_week = reports / "week-40.html"
            next_week.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            with patch("scripts.build_site.REPORTS", root / "reports"):
                build(root / "site")
            home = (root / "site/news/index.html").read_text(encoding="utf-8")
            self.assertEqual(home.count('data-kind="news"'), 12)
            self.assertEqual(home.count('class="weekly-report"'), 1)
            self.assertIn('data-week="2026-09-28" aria-label="第 40 周 · 2026.09.28—10.04">', home)
            older = (root / "site/news/2026-week-39/index.html").read_text(encoding="utf-8")
            self.assertIn('data-week="2026-09-21" aria-label="第 39 周 · 2026.09.21—09.27">', older)
            self.assertIn('href="../../news/2026-week-40/" role="option" data-week="2026-09-28" data-week-path="2026-week-40" aria-selected="false"', older)
            self.assertIn('href="../../news/2026-week-39/" role="option" data-week="2026-09-21" data-week-path="2026-week-39" aria-selected="true"', older)
            self.assertIn('href="../../assets/wiki-hub.css', older)
            self.assertIn('href="../../notes/"', older)

    def test_mail_layout_preserves_every_article_and_source(self):
        source = CURRENT_REPORT
        issue = parse_issue(source)
        body = render_mail_body(source.read_text(encoding="utf-8"), issue.categories)
        parser = ReportParser()
        parser.feed(body)
        self.assertEqual(parser.highlights, issue.highlights)
        self.assertEqual([(a.title, a.sections, a.sources) for a in parser.articles],
                         [(a.title, current_sections(a.sections), a.sources) for a in issue.articles])
        self.assertEqual(body.count('data-kind="news"'), 12)
        self.assertEqual(body.count('class="news-date'), 12)
        self.assertEqual(body.count('class="mail-summary"'), 3)
        dates = re.findall(r'<div class="news-date[^>]*>(.*?)</div>', body)
        self.assertTrue(all(re.fullmatch(r'\d+\s*月\s*\d+(?:、\d+)*\s*日', value) for value in dates))
        self.assertIn('修复：9 月 25 日', body)
        self.assertIn('white-space:nowrap', body)
        self.assertNotIn('bgcolor="#edf1f7"', body)
        self.assertIn('text-align:left', body)
        self.assertIn('margin-right:8px', body)
        self.assertNotIn('text-align:center', body)
        self.assertNotIn('padding:0 0 4px 4px;', body)
        self.assertNotIn('decimal-leading-zero', body)
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
                         [(a.title, current_sections(a.sections), a.sources) for a in issue.articles])
        self.assertEqual(body.count('data-kind="news"'), 10)
        self.assertEqual(body.count('data-kind="section"'), 5)
        conclusion = re.search(r'<h2\b[^>]*>一句话总结', body)
        self.assertIsNotNone(conclusion)
        self.assertNotIn('data-category=', body[conclusion.start():])
        self.assertEqual(WEEK38_REPORT.read_bytes(), original)

    def test_historical_images_use_current_template_without_changing_archive(self):
        for week in (37, 38, 39):
            source = REPORTS / f"ai-agent-frontend/2026/week-{week}.html"
            original = source.read_bytes()
            issue = parse_issue(source)
            body = render_mail_body(original.decode("utf-8"), issue.categories)
            self.assertNotIn('width="33.33%"', body)
            original_images = re.findall(r'<img\b[^>]*>', original.decode("utf-8"))
            rendered_images = re.findall(r'<img\b[^>]*>', body)
            self.assertEqual(len(original_images), len(rendered_images))
            for before, after in zip(original_images, rendered_images):
                for attribute in ('src', 'alt'):
                    self.assertEqual(re.search(fr'{attribute}="([^"]*)"', before).group(1),
                                     re.search(fr'{attribute}="([^"]*)"', after).group(1))
                self.assertIn('width:100%;max-width:420px;height:auto', after)
                self.assertIn('width="420"', after)
                image_url = re.search(r'src="([^"]*)"', after).group(1)
                self.assertIn(f'href="{image_url}"', body)
            self.assertEqual(body.count('class="image-slot"'), len(original_images))
            self.assertEqual(source.read_bytes(), original)

    def test_week37_images_are_served_locally_under_pages_subpath(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build(output)
            page = (output / "news/2026-week-37/index.html").read_text(encoding="utf-8")
            for filename in ('qwencloud-conference.jpeg', 'qwen-drive-architecture.png'):
                asset = f'assets/news/2026-week-37/{filename}'
                self.assertIn(f'src="../../{asset}"', page)
                self.assertTrue((output / asset).is_file())
            self.assertNotIn('src="https://yqintl.alicdn.com/', page)

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
            with patch("scripts.build_site.NEWS", news.parent), patch("scripts.build_site.REPORTS", reports), patch("scripts.build_site.NOTES", root / "notes"), patch("scripts.build_site.PRACTICES", root / "practices"):
                build(root / "site")
            home = (root / "site/news/index.html").read_text(encoding="utf-8")
            self.assertIn('data-week="2026-09-28"', home)
            self.assertIn('data-category="产业观察"', home)
            self.assertEqual(len(list((root / "site").rglob("*.html"))), 5)
            self.assertIn('class="content-empty"', (root / "site/notes/index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
