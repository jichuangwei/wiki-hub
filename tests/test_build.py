import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from scripts.build import REPORTS, build, parse_issue


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


class BuildSiteTests(unittest.TestCase):
    def test_existing_issue_extracts_complete_news(self):
        path = next(REPORTS.glob("*/*.html"))
        issue = parse_issue(path)
        self.assertEqual(issue.slug, "2026-09-21-to-2026-09-27")
        self.assertEqual(len(issue.categories), 5)
        self.assertEqual(len(issue.articles), 12)
        self.assertEqual(len(issue.highlights), 3)
        self.assertTrue(all(article.summary and article.sources for article in issue.articles))

    def test_generated_pages_have_article_links_and_no_placeholders(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            issues = build(output)
            self.assertEqual(len(issues), 1)
            homepage = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("AI 开发雷达", homepage)
            self.assertIn("news/2026-09-21-to-2026-09-27/story-01.html", homepage)
            self.assertNotIn("{{", homepage)

            news_pages = list((output / "news").glob("*/*.html"))
            self.assertEqual(len(news_pages), 12)
            article = (output / "news/2026-09-21-to-2026-09-27/story-01.html").read_text(encoding="utf-8")
            self.assertIn("原始来源", article)
            self.assertIn("OpenAI", article)
            self.assertNotIn("{{", article)

            report = (output / "reports/2026/2026-09-21-to-2026-09-27.html").read_text(encoding="utf-8")
            self.assertIn('id="story-01"', report)
            self.assertIn("返回 AI 开发雷达", report)

            for page in [output / "index.html", *news_pages, output / "reports/2026/2026-09-21-to-2026-09-27.html"]:
                parser = LinkParser()
                parser.feed(page.read_text(encoding="utf-8"))
                for href in parser.links:
                    url = urlsplit(href)
                    if not url.path or url.scheme or url.netloc:
                        continue
                    target = (page.parent / url.path).resolve()
                    self.assertTrue(target.is_relative_to(output.resolve()), href)
                    self.assertTrue(target.is_file(), f"Broken link: {page} -> {href}")


if __name__ == "__main__":
    unittest.main()
