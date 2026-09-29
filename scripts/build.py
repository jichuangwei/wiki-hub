#!/usr/bin/env python3
"""Build the static news site from archived weekly email reports."""

from __future__ import annotations

import argparse
import html
import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "content" / "reports"
WEB = ROOT / "web"
DIST = ROOT / "dist"
REPORT_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-to-(\d{4}-\d{2}-\d{2})\.html$")
EXPECTED_CATEGORIES = (
    "AI/大模型",
    "Coding Agent/Agent 产品",
    "Agent 开发技术与工程",
    "前端开发与生态",
    "AI 产业与开发者生态",
)


def clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def valid_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


@dataclass
class Article:
    category: str
    category_number: str
    title: str = ""
    meta: str = ""
    sections: list[tuple[str, str]] = field(default_factory=list)
    sources: list[tuple[str, str]] = field(default_factory=list)
    image_url: str = ""
    image_alt: str = ""
    anchor: str = ""

    @property
    def summary(self) -> str:
        for label, body in self.sections:
            if label.startswith("摘要"):
                return body
        return self.sections[0][1] if self.sections else ""


@dataclass
class Issue:
    source: Path
    start: date
    end: date
    title: str
    summary: str
    highlights: list[str]
    articles: list[Article]
    categories: list[str]

    @property
    def slug(self) -> str:
        return f"{self.start.isoformat()}-to-{self.end.isoformat()}"

    @property
    def report_href(self) -> str:
        return f"reports/{self.start.year}/{self.slug}.html"

    @property
    def date_label(self) -> str:
        return f"{self.start:%Y.%m.%d} — {self.end:%m.%d}"

    @property
    def week_number(self) -> int:
        return self.start.isocalendar().week


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] | None = None
        self.title = ""
        self.preheader_parts: list[str] | None = None
        self.preheader = ""
        self.section_parts: list[str] | None = None
        self.category = ""
        self.category_number = ""
        self.categories: list[str] = []
        self.focus_strong_parts: list[str] | None = None
        self.await_focus_list = False
        self.in_focus_list = False
        self.focus_item_parts: list[str] | None = None
        self.highlights: list[str] = []
        self.story: Article | None = None
        self.story_td_depth = 0
        self.div_parts: list[str] | None = None
        self.heading_parts: list[str] | None = None
        self.paragraph: dict | None = None
        self.strong_parts: list[str] | None = None
        self.link: dict | None = None
        self.articles: list[Article] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "title":
            self.title_parts = []
        if tag == "div" and "display:none" in (attr.get("style") or "") and not self.preheader:
            self.preheader_parts = []
        if tag == "span" and self.story is None:
            self.section_parts = []
        if tag == "strong" and self.story is None and not self.categories:
            self.focus_strong_parts = []
        if tag == "ul" and self.await_focus_list:
            self.in_focus_list = True
            self.await_focus_list = False
        if tag == "li" and self.in_focus_list:
            self.focus_item_parts = []

        if tag == "td":
            if self.story is not None:
                self.story_td_depth += 1
            elif "story" in (attr.get("class") or "").split():
                self.story = Article(self.category, self.category_number)
                self.story_td_depth = 1

        if self.story is None:
            return
        if tag == "div" and not self.story.meta:
            self.div_parts = []
        elif tag == "h2" and not self.story.title:
            self.heading_parts = []
        elif tag == "p":
            self.paragraph = {"text": [], "label": "", "links": []}
        elif tag == "strong" and self.paragraph is not None:
            self.strong_parts = []
        elif tag == "a" and self.paragraph is not None:
            self.link = {"url": attr.get("href") or "", "text": []}
        elif tag == "img" and not self.story.image_url:
            src = attr.get("src") or ""
            if valid_https(src):
                self.story.image_url = src
                self.story.image_alt = attr.get("alt") or self.story.title

    def handle_data(self, data: str) -> None:
        for parts in (
            self.title_parts,
            self.preheader_parts,
            self.section_parts,
            self.focus_strong_parts,
            self.focus_item_parts,
            self.div_parts,
            self.heading_parts,
            self.strong_parts,
        ):
            if parts is not None:
                parts.append(data)
        if self.paragraph is not None:
            self.paragraph["text"].append(data)
        if self.link is not None:
            self.link["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_parts is not None:
            self.title = clean("".join(self.title_parts))
            self.title_parts = None
        elif tag == "div" and self.preheader_parts is not None:
            self.preheader = clean("".join(self.preheader_parts))
            self.preheader_parts = None
        elif tag == "span" and self.section_parts is not None:
            section = clean("".join(self.section_parts))
            match = re.match(r"^(0[1-5])\s*·\s*(.+)$", section)
            if match:
                self.category_number, self.category = match.groups()
                self.categories.append(self.category)
            self.section_parts = None
        elif tag == "strong" and self.focus_strong_parts is not None:
            if clean("".join(self.focus_strong_parts)) == "本期聚焦":
                self.await_focus_list = True
            self.focus_strong_parts = None
        elif tag == "li" and self.focus_item_parts is not None:
            self.highlights.append(clean("".join(self.focus_item_parts)))
            self.focus_item_parts = None
        elif tag == "ul" and self.in_focus_list:
            self.in_focus_list = False

        if self.story is None:
            return
        if tag == "div" and self.div_parts is not None:
            self.story.meta = clean("".join(self.div_parts))
            self.div_parts = None
        elif tag == "h2" and self.heading_parts is not None:
            self.story.title = clean("".join(self.heading_parts))
            self.heading_parts = None
        elif tag == "strong" and self.strong_parts is not None and self.paragraph is not None:
            self.paragraph["label"] = clean("".join(self.strong_parts)).rstrip("：:")
            self.strong_parts = None
        elif tag == "a" and self.link is not None and self.paragraph is not None:
            self.paragraph["links"].append((clean("".join(self.link["text"])), self.link["url"]))
            self.link = None
        elif tag == "p" and self.paragraph is not None:
            label = self.paragraph["label"]
            whole = clean("".join(self.paragraph["text"]))
            body = whole[len(label):].lstrip("：: ") if label and whole.startswith(label) else whole
            if label == "来源":
                self.story.sources.extend(self.paragraph["links"])
            elif body:
                self.story.sections.append((label or "内容", body))
            self.paragraph = None
        elif tag == "td":
            self.story_td_depth -= 1
            if self.story_td_depth == 0:
                self.story.anchor = f"story-{len(self.articles) + 1:02d}"
                self.articles.append(self.story)
                self.story = None


def parse_issue(path: Path) -> Issue:
    match = REPORT_NAME.fullmatch(path.name)
    if not match:
        raise ValueError(f"Unexpected report filename: {path}")
    start, end = (date.fromisoformat(part) for part in match.groups())
    if start.weekday() != 0 or end.weekday() != 6 or (end - start).days != 6:
        raise ValueError(f"Report range must be a full Monday–Sunday week: {path}")
    if path.parent.name != str(start.year):
        raise ValueError(f"Report is in the wrong year directory: {path}")
    source = path.read_text(encoding="utf-8")
    if re.search(r"\{\{[^}]+\}\}", source):
        raise ValueError(f"Unfilled template placeholder: {path}")
    parser = ReportParser()
    parser.feed(source)
    if parser.categories != list(EXPECTED_CATEGORIES):
        raise ValueError(f"Missing or out-of-order categories in {path}: {parser.categories}")
    if not parser.articles:
        raise ValueError(f"No news articles found in {path}")
    for article in parser.articles:
        if not article.title or not article.summary or not article.sources:
            raise ValueError(f"Incomplete article in {path}: {article.title!r}")
        if any(not valid_https(url) for _, url in article.sources):
            raise ValueError(f"Non-HTTPS source link in {path}: {article.title}")
    if not parser.preheader:
        raise ValueError(f"Missing report preheader in {path}")
    return Issue(path, start, end, parser.title, parser.preheader, parser.highlights, parser.articles, parser.categories)


def render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    if re.search(r"\{\{[^}]+\}\}", template):
        raise ValueError("Unfilled web page placeholder")
    return template


def issue_link(issue: Issue, prefix: str = "") -> str:
    return prefix + issue.report_href


def article_link(issue: Issue, article: Article, prefix: str = "") -> str:
    return f"{prefix}news/{issue.slug}/{article.anchor}.html"


def render_article_card(issue: Issue, article: Article) -> str:
    image = (
        f'<img src="{escape(article.image_url)}" alt="{escape(article.image_alt)}" loading="lazy">'
        if article.image_url else '<span class="card-art-mark" aria-hidden="true">AI / DEV</span>'
    )
    summary = article.summary[:150] + ("…" if len(article.summary) > 150 else "")
    return f'''<article class="news-card" data-category="{escape(article.category_number)}" data-search="{escape(clean(article.title + ' ' + article.meta + ' ' + article.summary).lower())}">
      <a class="card-link" href="{escape(article_link(issue, article))}" aria-label="阅读：{escape(article.title)}">
        <div class="card-art">{image}</div>
        <div class="card-content"><div class="card-kicker"><span>{escape(article.category)}</span><span>{escape(issue.date_label)}</span></div>
        <h3>{escape(article.title)}</h3><p>{escape(summary)}</p><span class="card-more">阅读资讯 <span aria-hidden="true">↗</span></span></div>
      </a>
    </article>'''


def render_issue_row(issue: Issue) -> str:
    return f'''<a class="issue-row" href="{escape(issue_link(issue))}">
      <span class="issue-week">第 {issue.week_number:02d} 周</span>
      <span class="issue-copy"><strong>{escape(issue.date_label)}</strong><small>{escape(issue.summary)}</small></span>
      <span class="issue-count">{len(issue.articles)} 条资讯</span><span class="issue-arrow" aria-hidden="true">↗</span>
    </a>'''


def render_article_page(issue: Issue, article: Article, template: str) -> str:
    image = (
        f'<figure class="article-image"><img src="{escape(article.image_url)}" alt="{escape(article.image_alt)}" loading="eager"></figure>'
        if article.image_url else ""
    )
    sections = "\n".join(
        f'<section class="article-section"><h2>{escape(label)}</h2><p>{escape(body)}</p></section>'
        for label, body in article.sections
    )
    sources = "\n".join(
        f'<li><a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(label or url)} <span aria-hidden="true">↗</span></a></li>'
        for label, url in article.sources
    )
    return render(template, {
        "PAGE_TITLE": escape(article.title),
        "DESCRIPTION": escape(article.summary[:155]),
        "CATEGORY": escape(article.category),
        "ARTICLE_META": escape(article.meta),
        "ARTICLE_TITLE": escape(article.title),
        "ARTICLE_IMAGE": image,
        "ARTICLE_SECTIONS": sections,
        "SOURCE_LINKS": sources,
        "ISSUE_LABEL": escape(issue.date_label),
        "ISSUE_URL": escape("../../" + issue.report_href),
        "YEAR": str(issue.start.year),
    })


def render_report_page(issue: Issue) -> str:
    source = issue.source.read_text(encoding="utf-8")
    index = 0

    def add_anchor(match: re.Match[str]) -> str:
        nonlocal index
        index += 1
        return match.group(0).replace('class="story"', f'id="story-{index:02d}" class="story"', 1)

    source = re.sub(r'<td\s+class="story"', add_anchor, source)
    if index != len(issue.articles):
        raise ValueError(f"Anchor count mismatch in {issue.source}")
    back_link = ('<nav aria-label="站点导航" style="max-width:960px;margin:0 auto;padding:12px 12px 0;'
                 'font:600 13px -apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif;">'
                 '<a href="../../index.html" style="color:#155eef;text-decoration:none;">← 返回 AI 开发雷达</a></nav>')
    return re.sub(r"(<body\b[^>]*>)", lambda match: match.group(1) + back_link, source, count=1)


def build(output: Path) -> list[Issue]:
    paths = sorted(REPORTS.glob("*/*.html"), reverse=True)
    if not paths:
        raise ValueError("No weekly reports found in content/reports")
    issues = [parse_issue(path) for path in paths]
    slugs = [issue.slug for issue in issues]
    if len(slugs) != len(set(slugs)):
        raise ValueError("Duplicate report date range")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copytree(WEB / "assets", output / "assets")
    shutil.copytree(ROOT / "template", output / "template")
    (output / ".nojekyll").touch()

    article_template = (WEB / "article.html").read_text(encoding="utf-8")
    for issue in issues:
        report_output = output / issue.report_href
        report_output.parent.mkdir(parents=True, exist_ok=True)
        report_output.write_text(render_report_page(issue), encoding="utf-8")
        for article in issue.articles:
            article_output = output / article_link(issue, article)
            article_output.parent.mkdir(parents=True, exist_ok=True)
            article_output.write_text(render_article_page(issue, article, article_template), encoding="utf-8")

    latest = issues[0]
    recent = [(issue, article) for issue in issues for article in issue.articles][:36]
    cards = "\n".join(render_article_card(issue, article) for issue, article in recent)
    rows = "\n".join(render_issue_row(issue) for issue in issues)
    highlights = "\n".join(f"<li>{escape(item)}</li>" for item in latest.highlights[:3])
    counts = {str(n): sum(article.category_number == f"{n:02d}" for _, article in recent) for n in range(1, 6)}
    home = render((WEB / "index.html").read_text(encoding="utf-8"), {
        "LATEST_ISSUE_URL": escape(issue_link(latest)),
        "LATEST_ISSUE_DATE": escape(latest.date_label),
        "LATEST_ISSUE_WEEK": f"{latest.week_number:02d}",
        "LATEST_ISSUE_SUMMARY": escape(latest.summary),
        "LATEST_ISSUE_COUNT": str(len(latest.articles)),
        "LATEST_HIGHLIGHTS": highlights,
        "NEWS_CARDS": cards,
        "ISSUE_ROWS": rows,
        "NEWS_COUNT": str(len(recent)),
        "ISSUE_COUNT": str(len(issues)),
        **{f"CATEGORY_{n}_COUNT": str(counts[str(n)]) for n in range(1, 6)},
        "YEAR": str(date.today().year),
    })
    (output / "index.html").write_text(home, encoding="utf-8")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DIST)
    args = parser.parse_args()
    issues = build(args.output.resolve())
    print(f"Built {len(issues)} issues and {sum(len(issue.articles) for issue in issues)} article pages at {args.output.resolve()}")


if __name__ == "__main__":
    main()
