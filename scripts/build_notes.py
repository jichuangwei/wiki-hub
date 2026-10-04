"""Parse Markdown notes and render their document bodies."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Note:
    source: Path
    slug: str
    title: str
    published: date
    summary: str
    body: str


def parse_note(path: Path) -> Note:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", path.stem):
        raise ValueError(f"Invalid note filename: {path.name}")
    source = path.read_text(encoding="utf-8")
    match = re.fullmatch(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", source, flags=re.S)
    if not match:
        raise ValueError(f"Missing Markdown front matter: {path}")
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if not separator or key not in {"title", "date", "summary"} or key in metadata:
            raise ValueError(f"Invalid note metadata: {path}")
        metadata[key] = value.strip()
    if set(metadata) != {"title", "date", "summary"} or not all(metadata.values()):
        raise ValueError(f"Incomplete note metadata: {path}")
    body = match.group(2).strip()
    if not body:
        raise ValueError(f"Empty note body: {path}")
    try:
        published = date.fromisoformat(metadata["date"])
    except ValueError as exc:
        raise ValueError(f"Invalid note date: {path}") from exc
    return Note(path, path.stem, metadata["title"], published, metadata["summary"], body)


def render_note_body(note: Note) -> str:
    try:
        import markdown
    except ImportError as exc:
        raise RuntimeError("Install requirements-site.txt to render Markdown notes") from exc
    rendered = markdown.markdown(note.body, extensions=["fenced_code", "tables"])
    sanitizer = NoteHtmlSanitizer(note.source)
    sanitizer.feed(rendered)
    sanitizer.close()
    return "".join(sanitizer.parts)


class NoteHtmlSanitizer(HTMLParser):
    ALLOWED_TAGS = {
        "p", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "strong", "em",
        "code", "pre", "blockquote", "table", "thead", "tbody", "tr", "th", "td",
        "hr", "br", "img",
    }
    VOID_TAGS = {"hr", "br", "img"}
    BLOCKED_TAGS = {"script", "style", "iframe", "object", "embed", "form", "svg"}

    def __init__(self, source: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.parts: list[str] = []
        self.blocked_tag: str | None = None
        self.blocked_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.blocked_tag:
            if tag == self.blocked_tag:
                self.blocked_depth += 1
            return
        if tag in self.BLOCKED_TAGS:
            self.blocked_tag = tag
            self.blocked_depth = 1
            return
        if tag not in self.ALLOWED_TAGS:
            return
        allowed_attrs = {"href", "title"} if tag == "a" else {"src", "alt", "title"} if tag == "img" else {"class"} if tag == "code" else set()
        safe_attrs = []
        for key, value in attrs:
            if key not in allowed_attrs or value is None:
                continue
            if key in {"href", "src"}:
                normalized = re.sub(r"[\x00-\x20]", "", value)
                scheme = urlparse(normalized).scheme.lower()
                if scheme not in ({"", "http", "https", "mailto"} if key == "href" else {"", "http", "https"}):
                    raise ValueError(f"Unsafe Markdown link in {self.source}")
            if key == "class" and not re.fullmatch(r"language-[a-zA-Z0-9_-]+", value):
                continue
            safe_attrs.append(f' {key}="{html.escape(value, quote=True)}"')
        if tag == "a" and any(key == "href" and value is not None for key, value in attrs):
            safe_attrs.append(' target="_blank" rel="noopener noreferrer"')
        self.parts.append(f"<{tag}{''.join(safe_attrs)}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self.blocked_tag:
            if tag == self.blocked_tag:
                self.blocked_depth -= 1
                if self.blocked_depth == 0:
                    self.blocked_tag = None
            return
        if tag in self.ALLOWED_TAGS and tag not in self.VOID_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.blocked_tag:
            self.parts.append(html.escape(data))

def article_layout(body: str) -> tuple[str, str]:
    """Assign unique anchors after sanitization; show a directory on long articles."""
    headings = []
    def anchor(match: re.Match[str]) -> str:
        level, content = match.groups()
        identifier = f"section-{len(headings) + 1}"
        title = html.unescape(re.sub(r"<[^>]+>", "", content))
        headings.append((level, identifier, title))
        return f'<h{level} id="{identifier}">{content}</h{level}>'
    body = re.sub(r"<h([23])>(.*?)</h\1>", anchor, body, flags=re.S)
    if sum(level == "2" for level, _, _ in headings) < 6:
        return body, ""
    links = "".join(f'<li class="toc-level-{level}"><a href="#{identifier}">{html.escape(title)}</a></li>'
                    for level, identifier, title in headings)
    toc = ('<aside class="article-toc" aria-label="文章目录">'
           '<p class="toc-title">文章目录</p>'
           f'<nav aria-label="章节导航"><ol>{links}</ol></nav></aside>')
    return body, toc
