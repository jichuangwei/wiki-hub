#!/usr/bin/env python3
"""Build the static news site from archived weekly email reports."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

if __package__:
    from .build_notes import article_layout, parse_note, render_note_body
else:
    from build_notes import article_layout, parse_note, render_note_body


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "content" / "news" / "reports"
NEWS = ROOT / "content" / "news" / "items"
NOTES = ROOT / "content" / "notes"
PRACTICES = ROOT / "content" / "practices"
ARTICLE_REDIRECTS = {
    "notes/chatgpt-scheduled-weekly-report-publishing":
        "practices/chatgpt-automated-content-publishing",
}
SITE = ROOT / "site"
DIST = ROOT / "dist"
REPORT_NAME = re.compile(r"^([a-z0-9-]+)-weekly-(\d{4}-\d{2}-\d{2})-to-(\d{4}-\d{2}-\d{2})\.html$")
EXPECTED_CATEGORIES = (
    "AI/大模型",
    "Coding Agent/Agent 产品",
    "Agent 开发技术与工程",
    "前端开发与生态",
    "AI 产业与开发者生态",
)
DEEP_CATEGORY = "AI 编程助手 / Code Agent 深度资料"


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
    topic: str
    start: date
    end: date
    title: str
    summary: str
    highlights: list[str]
    articles: list[Article]
    categories: list[str]

    @property
    def slug(self) -> str:
        dates = f"{self.start.isoformat()}-to-{self.end.isoformat()}"
        return dates if self.topic == "ai-agent-frontend" else f"{self.topic}-{dates}"

    @property
    def report_href(self) -> str:
        return f"reports/{self.start.year}/{self.slug}.html"

    @property
    def date_label(self) -> str:
        return f"{self.start:%Y.%m.%d} — {self.end:%m.%d}"

    @property
    def week_number(self) -> int:
        return self.start.isocalendar().week


@dataclass
class StandaloneNews:
    source: Path
    published: date
    slug: str
    article: Article

    @property
    def href(self) -> str:
        return f"news/{self.published.year}/{self.slug}.html"


def parse_standalone_news(path: Path) -> StandaloneNews:
    data = json.loads(path.read_text(encoding="utf-8"))
    published = date.fromisoformat(data["date"])
    if path.parent.name != str(published.year) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", path.stem):
        raise ValueError(f"Invalid news path: {path}")
    article = Article(category=data["category"].strip(), category_number="")
    article.title = data["title"].strip()
    article.meta = data.get("source_name", "").strip() + " · " + published.isoformat()
    article.sections = [(section["title"].strip(), section["text"].strip()) for section in data["sections"]]
    article.sources = [(item["label"].strip(), item["url"]) for item in data["sources"]]
    image = data.get("image") or {}
    article.image_url = image.get("url", "")
    article.image_alt = image.get("alt", "")
    if not article.category or not article.title or not article.summary or not article.sources:
        raise ValueError(f"Incomplete news item: {path}")
    if any(not label or not body for label, body in article.sections):
        raise ValueError(f"Empty news section: {path}")
    if any(not label or not valid_https(url) for label, url in article.sources):
        raise ValueError(f"Invalid news source: {path}")
    if article.image_url and (not valid_https(article.image_url) or not article.image_alt):
        raise ValueError(f"Invalid news image: {path}")
    return StandaloneNews(path, published, path.stem, article)


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
        if tag == "div" and ("news-date" in (attr.get("class") or "").split() or (not self.story.meta and not self.story.title and "news-tags" not in (attr.get("class") or "").split())):
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
            match = re.match(r"^(\d{2})\s*·\s*(.+)$", section)
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
    week_match = re.fullmatch(r"week-([1-9][0-9]?)\.html", path.name)
    if week_match:
        topic = path.parent.parent.name
        start = date.fromisocalendar(int(path.parent.name), int(week_match[1]), 1)
        end = start + timedelta(days=6)
    else:
        match = REPORT_NAME.fullmatch(path.name)
        if not match:
            raise ValueError(f"Unexpected report filename: {path}")
        topic, start_text, end_text = match.groups()
        start, end = date.fromisoformat(start_text), date.fromisoformat(end_text)
        if path.parent.name != str(start.year) or path.parent.parent.name != topic:
            raise ValueError(f"Report is in the wrong topic/year directory: {path}")
    if start.weekday() != 0 or end.weekday() != 6 or (end - start).days != 6:
        raise ValueError(f"Report range must be a full Monday–Sunday week: {path}")
    source = path.read_text(encoding="utf-8")
    if re.search(r"\{\{[^}]+\}\}", source):
        raise ValueError(f"Unfilled template placeholder: {path}")
    parser = ReportParser()
    parser.feed(source)
    deep = parser.categories == [DEEP_CATEGORY]
    combined = parser.categories == [*EXPECTED_CATEGORIES, DEEP_CATEGORY]
    if topic == "ai-agent-frontend" and not deep and not combined and parser.categories != list(EXPECTED_CATEGORIES):
        raise ValueError(f"Missing or out-of-order AI categories in {path}: {parser.categories}")
    if deep or combined:
        deep_articles = [article for article in parser.articles if article.category == DEEP_CATEGORY]
        if not 3 <= len(deep_articles) <= 5:
            raise ValueError("Deep reports must contain 3–5 articles")
        for article in deep_articles:
            labels = {label for label, _ in article.sections}
            if not {"证据强弱", "前端实践"}.issubset(labels):
                raise ValueError(f"Missing deep analysis sections: {article.title}")
    if not parser.categories:
        raise ValueError(f"No categories found in {path}")
    if not parser.articles:
        raise ValueError(f"No news articles found in {path}")
    for article in parser.articles:
        if not article.title or not article.summary or not article.sources:
            raise ValueError(f"Incomplete article in {path}: {article.title!r}")
        if any(not valid_https(url) for _, url in article.sources):
            raise ValueError(f"Non-HTTPS source link in {path}: {article.title}")
    if not parser.preheader:
        raise ValueError(f"Missing report preheader in {path}")
    return Issue(path, topic, start, end, parser.title, parser.preheader, parser.highlights, parser.articles, parser.categories)


def render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    if re.search(r"\{\{[^}]+\}\}", template):
        raise ValueError("Unfilled web page placeholder")
    return template



def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_slug(week: date) -> str:
    iso = week.isocalendar()
    return f"{iso.year}-week-{iso.week}"


def image_gallery(images: list[str]) -> str:
    """Use the current email template's wrapping, two-slot image layout."""
    slots = []
    for index, image in enumerate(images):
        image = re.sub(r'\s(?:style|width|height)="[^"]*"', '', image, flags=re.I)
        image = image.rstrip('>').rstrip('/') + ' height="200" style="display:block;width:auto;max-width:420px;height:200px;object-fit:contain;object-position:left center;border:0;margin:0;">'
        slots.append(f'<div class="image-slot" style="display:inline-block;vertical-align:top;width:auto;min-width:180px;max-width:420px;margin-right:8px;"><div style="padding:0 0 8px;">{image}</div></div>')
    return '<div style="width:100%;font-size:0;line-height:0;text-align:left;margin:0 0 13px;">' + ''.join(slots) + '</div>'


def news_metadata(tags: list[str], date_text: str) -> str:
    labels = "".join(f'<span class="mail-tag" style="display:inline-block;margin:0 6px 4px 0;padding:2px 8px;background:#e8edf5;border-radius:4px;font-size:12px;line-height:20px;color:#607089;">{escape(tag)}</span>' for tag in tags)
    tags_html = f'<div class="news-tags" style="margin:14px 0 8px;">{labels}</div>' if labels else ""
    return tags_html + f'<div class="news-date mail-subtle" style="margin:0 0 4px;font-size:12px;line-height:20px;color:#8090a6;">{escape(date_text)}</div>'


def news_heading(title_html: str, date_text: str) -> str:
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;margin:4px 0 11px;"><tr>'
            f'<td valign="top" style="padding:0 12px 0 0;overflow-wrap:anywhere;word-break:break-word;">{title_html}</td>'
            '<td width="1" align="right" valign="top" nowrap style="width:1%;padding:3px 0 0;white-space:nowrap;">'
            f'<div class="news-date mail-subtle" style="font-size:12px;line-height:20px;color:#8090a6;">{escape(date_text)}</div>'
            '</td></tr></table>')


def render_mail_body(source: str, categories: list[str]) -> str:
    """Preserve the complete mail layout and annotate its rows for filtering."""
    body = re.search(r"<body\b[^>]*>(.*?)</body>", source, flags=re.S | re.I)
    if not body:
        raise ValueError("Report is missing an HTML body")
    content = re.sub(r"<!--.*?-->", "", body.group(1), flags=re.S)
    if re.search(r"<(?:script|iframe|object|embed|form|base)\b|\son\w+\s*=", content, flags=re.I):
        raise ValueError("Report body must contain passive email markup")
    # Migrate the old three-column galleries only in website output. The original
    # sent email remains unchanged; current image-slot galleries pass through.
    def migrate_gallery(match: re.Match[str]) -> str:
        images = re.findall(r'<img\b[^>]*>', match.group(0), flags=re.I)
        return image_gallery(images) if images else match.group(0)

    content = re.sub(r'<table\b[^>]*style="[^"]*table-layout:fixed[^\"]*"[^>]*>.*?</table>',
                     migrate_gallery, content, flags=re.S | re.I)
    content = content.replace('padding:0 4px 4px 0;', 'padding:0 4px 8px;').replace('padding:0 0 4px 4px;', 'padding:0 4px 8px;')
    content = content.replace('width:100%;font-size:0;line-height:0;margin:0 0 13px;', 'width:100%;font-size:0;line-height:0;text-align:left;margin:0 0 13px;')
    # Apply the current week-first heading order to archived report pages.
    def week_before_date(match: re.Match[str]) -> str:
        attrs, text = match.groups()
        plain = html.unescape(text).replace("\xa0", " ")
        heading = re.search(r"(?P<date>.+?)\s*/\s*第\s*(?P<week>\d+)\s*周", plain)
        if not heading:
            return match.group(0)
        ordered = f"第 {heading.group('week')} 周&nbsp;&nbsp;/&nbsp;&nbsp;{escape(heading.group('date').strip())}"
        return f'<div{attrs}>{ordered}</div>'

    content = re.sub(r'<div(\b[^>]*)>([^<]*第\s*\d+\s*周[^<]*)</div>', week_before_date, content)
    # Keep archived emails intact while displaying their heading above the week.
    def title_before_date(match: re.Match[str]) -> str:
        date_line, title = match.groups()
        date_line = date_line.replace('style="', 'style="margin-top:12px;', 1)
        title = title.replace("margin:12px 0 0", "margin:0", 1)
        return title + date_line

    content = re.sub(
        r'(<div\b[^>]*>[^<]*第\s*\d+\s*周[^<]*</div>)\s*(<h1\b[^>]*class="hero-title"[^>]*>.*?</h1>)',
        title_before_date, content, flags=re.S,
    )
    chunks = re.split(r'(?=<tr><td\s+class="pad")', content)
    category = ""
    result = []
    for chunk in chunks:
        label = re.search(r"<span\b[^>]*>(.*?)</span>", chunk, flags=re.S)
        kind = "news" if 'class="story"' in chunk else "section"
        if label:
            heading = clean(html.unescape(re.sub(r"<[^>]+>", "", label.group(1))))
            for candidate in categories:
                if heading.endswith(candidate):
                    category = candidate
                    break
        if re.search(r"<h2[^>]*>\s*(?:一句话总结|一句话趋势总结|本周动手验证|团队行动建议)", chunk):
            category = ""
        if category:
            chunk = chunk.replace("<tr>", f'<tr data-category="{escape(category)}" data-kind="{kind}">', 1)
        result.append(chunk)
    content = "".join(result)
    # Older issues retain their text and images while adopting the current palette.
    for old, new in {
        "#f2f5f8": "#f6f8fc", "#155eef": "#2456cd", "#101b32": "#17233b",
        "#19345f": "#17233b", "#4574c5": "#2456cd", "#34425b": "#607089",
        "#52627b": "#607089", "#71809a": "#8090a6", "#8490a3": "#8090a6",
        "#dbe5f4": "#dde5f0", "#e6ebf2": "#dde5f0", "#e5eaf1": "#e7edf5",
        "max-width:960px": "max-width:1180px", "padding:14px 16px": "padding:19px 20px",
        "border:1px solid #e7edf5;border-radius:10px": "border:1px solid #e7edf5;border-radius:16px",
        "font-size:20px;line-height:28px;color:#17233b": "font-size:18px;line-height:26px;color:#17233b",
    }.items():
        content = content.replace(old, new)
    # Historical emails keep their archive bytes, but use the current separator
    # layout on the website, just like newly generated issues.
    content = content.replace("border:1px solid #e7edf5;border-radius:16px;", "border-bottom:1px solid #dde5f0;")
    content = content.replace("border-bottom:2px solid #dde5f0;", "")
    content = content.replace('class="story" style="padding:19px 20px;', 'class="story" style="padding:8px 0 20px;')
    content = content.replace('class="story" style="padding:19px 0;', 'class="story" style="padding:8px 0 20px;')
    content = content.replace('class="pad" style="padding:10px 12px 0;', 'class="pad" style="padding:4px 12px 0;')
    content = content.replace('style="padding:0 0 10px;"', 'style="padding:0;"')
    # Reuse the template's focus panel for older archives while retaining each
    # issue's original highlight markup and count.
    template = (ROOT / "templates/news/ai-agent-frontend-weekly-email.html").read_text(encoding="utf-8")
    panel = re.search(r'<table\b[^>]*class="mail-focus focus-panel".*?</table>', template, flags=re.S).group(0)
    def update_focus(match: re.Match[str]) -> str:
        items = re.findall(r'<li\b[^>]*>(.*?)</li>', match.group(0), flags=re.S)
        if not items:
            return match.group(0)
        rows = []
        for item in items:
            item = item.replace(' class="mail-ink"', '')
            rows.append(f'<li style="padding:0 0 5px;">{item}</li>')
        return re.sub(r'(<ul\b[^>]*>).*?(</ul>)', lambda m: m.group(1) + ''.join(rows) + m.group(2), panel, flags=re.S)
    content = re.sub(r'<table\b[^>]*(?:background:#eef4ff|class="mail-focus focus-panel")[^>]*>.*?</table>', update_focus, content, flags=re.S)
    # Improve reading without modifying historical email archives.
    content = content.replace("max-width:1180px", "max-width:1000px")
    content = content.replace("font-size:14px;line-height:23px", "font-size:15px;line-height:26px")
    content = content.replace("margin:0 0 10px;font-size:15px", "margin:0 0 14px;font-size:15px")
    content = content.replace("object-fit:cover", "object-fit:contain;object-position:left center")
    content = content.replace("一句话趋势总结", "一句话总结")
    content = re.sub(r'<td class="pad"[^>]*>(\s*<table\b[^>]*class="mail-focus focus-panel")',
                     r'<td class="focus-wrap" style="padding:0 12px;">\1', content)
    content = content.replace('class="focus-wrap" style="padding:0;"', 'class="focus-wrap" style="padding:0 12px;"')
    # Display archive dates beside their titles and existing tags above sources.
    def move_metadata(match: re.Match[str]) -> str:
        story = match.group(0)
        meta = re.search(r'<div\b[^>]*>([^<]+)</div>\s*(?=<h2)', story)
        if not meta:
            return story
        parts = [part.strip() for part in html.unescape(meta.group(1)).split(" · ")]
        date_index = next((i for i, part in enumerate(parts) if re.search(r'\d{4}[-/.]\d|\d+\s*月\s*\d+(?:[、，,–—-]\d+)*\s*日', part)), None)
        if date_index is None:
            return story
        # Legacy metadata uses either tag · organization · date or organization · date.
        tags = parts[:1] if date_index >= 2 else []
        full_date_text = " · ".join(parts[date_index:])
        date_text = re.search(r'\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d+\s*月\s*\d+(?:[、，,–—-]\d+)*\s*日', full_date_text).group(0)
        metadata = news_metadata(tags, "")
        metadata = re.sub(r'<div class="news-date[^>]*>.*?</div>', '', metadata, flags=re.S)
        if full_date_text != date_text:
            metadata += f'<div class="mail-subtle" style="margin:0 0 6px;font-size:12px;line-height:20px;color:#8090a6;">时间与状态说明：{escape(full_date_text)}</div>'
        story = story[:meta.start()] + story[meta.end():]
        def move_date(heading: re.Match[str]) -> str:
            title = re.sub(r'margin:[^;"]+', 'margin:0', heading.group(0), count=1)
            return news_heading(title, date_text)
        story = re.sub(r'<h2\b[^>]*>.*?</h2>', move_date, story, count=1, flags=re.S)
        return re.sub(r'(?=<p\b[^>]*>\s*<strong[^>]*>来源[：:])', lambda _: metadata, story, count=1)

    content = re.sub(r'<td class="story"[^>]*>.*?</td></tr></table>', move_metadata, content, flags=re.S)
    content = content.replace("border-bottom:1px solid #dde5f0;", "border-bottom:1px solid #cbd5e1;")
    # Restyle the three closing sections, preserving every original paragraph.
    def update_summary(match: re.Match[str]) -> str:
        body = match.group(1)
        body = re.sub(r'(<h2\b[^>]*style=")[^"]*("[^>]*>)',
                      r'\1margin:0 0 12px;font-size:18px;line-height:26px;font-weight:800;color:#17233b;\2', body, count=1)
        body = body.replace('class="mail-muted"', 'class="mail-ink"')
        body = body.replace('color:#607089;', 'color:#394a64;')
        if re.search(r"(?:一句话总结|一句话趋势总结)</h2>", body):
            def trend_list(match: re.Match[str]) -> str:
                description = match.group(1)
                return ('<ul style="margin:0;padding:0;list-style-type:none;'
                        'font-size:14px;line-height:23px;color:#394a64;">'
                        f'<li style="padding:0;">{description}</li></ul>')
            body = re.sub(r'<p\b[^>]*>(.*?)</p>', trend_list, body, count=1, flags=re.S)
        return ('<tr><td class="pad" style="padding:16px 12px 0;">'
                '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="mail-summary" style="width:100%;border:1px solid #cbd5e1;border-radius:8px;border-collapse:separate;border-spacing:0;">'
                '<tr><td class="summary-content mail-summary" style="padding:18px 20px;border-radius:8px;">' + body + '</td></tr></table></td></tr>')
    content = re.sub(r'<tr><td class="pad"[^>]*>\s*(<h2\b[^>]*>(?:一句话总结|一句话趋势总结|本周动手验证|团队行动建议)</h2>.*?)</td></tr>',
                     update_summary, content, flags=re.S)
    # Ordinary image links work in both the web page and email clients.
    def link_image(match: re.Match[str]) -> str:
        if match.group(1):
            return match.group(0)
        image = match.group(2)
        src = re.search(r'\bsrc="([^"]+)"', image)
        if not src or not valid_https(html.unescape(src.group(1))):
            return image
        return f'<a href="{html.escape(html.unescape(src.group(1)), quote=True)}" target="_blank" rel="noopener" style="display:inline-block;text-decoration:none;">{image}</a>'

    content = re.sub(r'(<a\b[^>]*>\s*)?(<img\b[^>]*>)(\s*</a>)?', link_image, content, flags=re.I)
    content = re.sub(r'(<strong\b[^>]*>)(?:为什么值得关注[^<]*|对(?:前端|Agent)[^<]*影响|适用场景与理由)[：:]',
                     lambda m: m.group(1) + ("适用场景：" if "适用场景" in m.group(0) else "影响与分析："), content)
    content = content.replace("margin:4px 0 11px;", "margin:4px 0 12px;")
    content = content.replace("text-align:left;margin:0 0 13px;", "text-align:left;margin:0 0 8px;")
    content = content.replace("padding:22px 12px 0;", "padding:28px 12px 0;")
    content = content.replace("font-size:16px;line-height:24px;font-weight:800;letter-spacing:.3px;", "font-size:18px;line-height:26px;font-weight:800;letter-spacing:.3px;")
    # Put event tags directly below the heading without altering archive files.
    chunks = re.split(r'(?=<td class="story")', content)
    for index, chunk in enumerate(chunks):
        if not chunk.startswith('<td class="story"'):
            continue
        tags = re.search(r'<div class="news-tags"[^>]*>.*?</div>', chunk, flags=re.S)
        if not tags:
            continue
        tag_html = tags.group(0).replace("margin:14px 0 8px;", "margin:0 0 8px;")
        chunk = chunk[:tags.start()] + chunk[tags.end():]
        heading = re.search(r'<h2\b[^>]*>.*?</h2>', chunk, flags=re.S)
        if not heading:
            continue
        table_end = chunk.find("</tr></table>", heading.end())
        insert_at = table_end + len("</tr></table>") if table_end >= 0 else heading.end()
        chunks[index] = chunk[:insert_at] + tag_html + chunk[insert_at:]
    content = "".join(chunks)
    content = content.replace("padding:28px 12px 0;", "padding:32px 12px 0;")
    content = content.replace("font-size:18px;line-height:26px;font-weight:800;letter-spacing:.3px;", "font-size:19px;line-height:28px;font-weight:800;letter-spacing:.3px;")
    return content.replace("font-size:14px;line-height:23px", "font-size:15px;line-height:26px")


def email_styles() -> str:
    template = (ROOT / "templates/news/ai-agent-frontend-weekly-email.html").read_text(encoding="utf-8")
    css = re.search(r"<style>(.*?)</style>", template, flags=re.S).group(1)
    # Website theme is selected by its header toggle, independently of the
    # system preference used by email clients.
    css = re.sub(r'@media\s*\(prefers-color-scheme:dark\)\s*\{(?:[^{}]*\{[^{}]*\})*\s*\}', '', css)
    for selector in ("body", "table", "img", "a"):
        replacement = ".weekly-report" if selector == "body" else f".weekly-report {selector}"
        css = re.sub(rf"(?<![\w.-]){selector}\s*\{{", replacement + "{", css)
    return css


def standalone_mail(items: list[StandaloneNews]) -> str:
    rows = []
    for item in items:
        article = item.article
        image = (image_gallery([f'<img src="{escape(article.image_url)}" alt="{escape(article.image_alt)}">']) if article.image_url else "")
        sections = "".join(f'<p style="margin:0 0 10px;font-size:14px;line-height:23px;color:#607089;"><strong style="color:#17233b;">{escape(label)}：</strong>{escape(body)}</p>' for label, body in article.sections)
        links = " · ".join(f'<a href="{escape(url)}">{escape(label)}</a>' for label, url in article.sources)
        heading = news_heading(f'<h2 style="margin:0;font-size:18px;line-height:26px;">{escape(article.title)}</h2>', item.published.isoformat())
        rows.append(f'<tr data-category="{escape(article.category)}" data-kind="news"><td style="padding:4px 12px 0;"><table width="100%" style="border-bottom:1px solid #cbd5e1;"><tr><td style="padding:8px 0 20px;">{heading}{image}{sections}<p style="font-size:13px;color:#607089;"><strong>来源：</strong>{links}</p></td></tr></table></td></tr>')
    return '<table role="presentation" width="100%">' + "".join(rows) + '</table>'


def build(output: Path) -> list[Issue]:
    issues = [parse_issue(path) for path in REPORTS.glob("*/*/*.html")]
    issues.sort(key=lambda issue: (issue.start, issue.topic), reverse=True)
    standalone = [parse_standalone_news(path) for path in sorted(NEWS.glob("*/*.json"))]
    if not issues and not standalone:
        raise ValueError("No content found in content/news/items or content/news/reports")
    slugs = [issue.slug for issue in issues]
    if len(slugs) != len(set(slugs)):
        raise ValueError("Duplicate report date range")

    entries = [(issue.start, article, issue.date_label) for issue in issues for article in issue.articles]
    entries += [(week_start(item.published), item.article, item.published.isoformat()) for item in standalone]
    entries.sort(key=lambda entry: entry[0], reverse=True)
    weeks = sorted({week for week, _, _ in entries}, reverse=True)
    latest_week = weeks[0]
    categories = list(dict.fromkeys(article.category for _, article, _ in entries))
    tabs = ['<button class="category-tab is-active" type="button" data-filter="all" aria-pressed="true">全部 <span></span></button>']
    tabs += [f'<button class="category-tab" type="button" data-filter="{escape(category)}" aria-pressed="false">'
             f'{escape(category)} <span></span></button>' for category in categories]
    def week_label(week: date) -> str:
        return f'第 {week.isocalendar().week:02d} 周 · {week:%Y.%m.%d}—{week + timedelta(days=6):%m.%d}'

    week_documents = {}
    for week in weeks:
        documents = [render_mail_body(issue.source.read_text(encoding="utf-8"), issue.categories)
                     for issue in issues if issue.start == week]
        extra = [item for item in standalone if week_start(item.published) == week]
        if extra:
            documents.append(standalone_mail(extra))
        week_documents[week] = f'<section class="weekly-report" data-week="{week.isoformat()}" aria-label="{week_label(week)}">' + "".join(documents) + '</section>'

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copytree(SITE / "assets", output / "assets")
    (output / ".nojekyll").touch()
    asset_rev = hashlib.sha256(b''.join((SITE / "assets" / name).read_bytes()
        for name in ("wiki-hub.css", "news-filter.js", "theme.js", "header.js", "article.js"))).hexdigest()[:12]
    news_template = (SITE / "pages" / "news.html").read_text(encoding="utf-8")
    image_copies = json.loads((SITE / "assets/news/image-sources.json").read_text(encoding="utf-8"))
    for asset in image_copies.values():
        if not (SITE / "assets" / asset).is_file():
            raise ValueError(f"Missing news image copy: {asset}")
    def news_page(selected_week: date, site_root: str) -> str:
        options = []
        previous_year = None
        for week in weeks:
            year = week.isocalendar().year
            if year != previous_year:
                options.append(f'<div class="week-year" role="presentation">{year} 年</div>')
                previous_year = year
            latest = '<span class="week-latest">最新</span>' if week == latest_week else ''
            options.append(f'<a class="week-option" href="{site_root}news/{week_slug(week)}/" role="option" '
                f'data-week="{week.isoformat()}" data-week-path="{week_slug(week)}" '
                f'aria-selected="{str(week == selected_week).lower()}"><span>{week_label(week)}</span>{latest}</a>')
        report = week_documents[selected_week]
        for original, asset in image_copies.items():
            report = report.replace(f'src="{escape(original)}"', f'src="{site_root}assets/{escape(asset)}"')
        return render(news_template, {
            "SITE_ROOT": site_root,
            "ASSET_REV": asset_rev,
            "WEEK_OPTIONS": "\n".join(options),
            "CURRENT_WEEK": week_label(selected_week),
            "CATEGORY_TABS": "\n".join(tabs),
            "WEEKLY_REPORTS": report,
            "EMAIL_STYLES": email_styles(),
        })

    news_dir = output / "news"
    news_dir.mkdir()
    (news_dir / "index.html").write_text(news_page(latest_week, "../"), encoding="utf-8")
    for week in weeks:
        week_dir = news_dir / week_slug(week)
        week_dir.mkdir()
        (week_dir / "index.html").write_text(news_page(week, "../../"), encoding="utf-8")
    for section, source, detail_template, empty_description in (
        ("notes", NOTES, "note.html", "遇到的问题和解决过程会陆续整理在这里。"),
        ("practices", PRACTICES, "practice.html", "工具协作、流程设计与实践经验会陆续整理在这里。"),
    ):
        notes = sorted((parse_note(path) for path in source.glob("*.md")),
                       key=lambda note: (note.published, note.slug), reverse=True)
        (output / section).mkdir()
        if notes:
            cards = "\n".join(
                f'<li><a class="note-card" href="{escape(note.slug)}/">'
                f'<h2>{escape(note.title)}</h2><p>{escape(note.summary)}</p>'
                f'<time datetime="{note.published.isoformat()}">{note.published:%Y.%m.%d}</time>'
                '</a></li>' for note in notes
            )
            notes_content = f'<ol class="notes-list">{cards}</ol>'
        else:
            notes_content = f'''<div class="content-empty">
            <svg class="content-empty-icon" width="42" height="42" viewBox="0 0 42 42" fill="none" aria-hidden="true">
              <rect x="9" y="6" width="24" height="30" rx="4" stroke="currentColor" stroke-width="1.8"/>
              <path d="M15 16h12M15 22h12M15 28h7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            <p>暂无记录</p>
            <span>{empty_description}</span>
          </div>'''
        notes_page = render((SITE / "pages" / f"{section}.html").read_text(encoding="utf-8"), {
            "ASSET_REV": asset_rev,
            "NOTES_SECTION_CLASS": " has-notes" if notes else "",
        }).replace("<!--NOTES_CONTENT-->", notes_content)
        (output / section / "index.html").write_text(notes_page, encoding="utf-8")
        for note in notes:
            note_body, note_toc = article_layout(render_note_body(note))
            note_page = render((SITE / "pages" / detail_template).read_text(encoding="utf-8"), {
                "ASSET_REV": asset_rev,
                "NOTE_LAYOUT_CLASS": " has-toc" if note_toc else "",
                "NOTE_TITLE": escape(note.title),
                "NOTE_SUMMARY": escape(note.summary),
                "NOTE_DATE_ISO": note.published.isoformat(),
                "NOTE_DATE": f"{note.published:%Y.%m.%d}",
            }).replace("<!--NOTE_BODY-->", note_body).replace("<!--NOTE_TOC-->", note_toc)
            note_dir = output / section / note.slug
            note_dir.mkdir()
            (note_dir / "index.html").write_text(note_page, encoding="utf-8")
    for old_path, new_path in ARTICLE_REDIRECTS.items():
        if not (output / new_path / "index.html").exists():
            continue
        redirect_dir = output / old_path
        redirect_dir.mkdir(parents=True, exist_ok=True)
        target = "../../" + new_path + "/"
        redirect_page = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0;url={escape(target)}">
<title>文章已移至实践经验 · Wiki Hub</title>
<link rel="canonical" href="{escape(target)}"></head>
<body><p><a href="{escape(target)}">阅读实践经验文章</a></p></body></html>'''
        (redirect_dir / "index.html").write_text(redirect_page, encoding="utf-8")
    (output / "index.html").write_text((SITE / "pages" / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DIST)
    args = parser.parse_args()
    issues = build(args.output.resolve())
    print(f"Built news, notes and practices pages from {len(issues)} weekly reports at {args.output.resolve()}")


if __name__ == "__main__":
    main()
