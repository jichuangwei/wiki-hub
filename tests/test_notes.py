import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_notes import parse_note, render_note_body
from scripts.build_site import build


class NotesTests(unittest.TestCase):
    def test_markdown_note_renders_as_detail_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notes = root / "notes"
            notes.mkdir()
            (notes / "example.md").write_text("""---
title: 示例问题
date: 2026-10-03
summary: 问题摘要
---

## 原因

使用 **相对路径**。

```html
<script>alert('not executable')</script>
```
""", encoding="utf-8")
            with patch("scripts.build_site.NOTES", notes):
                build(root / "dist")
            listing = (root / "dist/notes/index.html").read_text(encoding="utf-8")
            detail = (root / "dist/notes/example/index.html").read_text(encoding="utf-8")
            self.assertIn('href="example/"', listing)
            self.assertIn("<strong>相对路径</strong>", detail)
            self.assertIn("&lt;script&gt;", detail)
            self.assertNotIn("<script>alert", detail)

    def test_note_requires_complete_front_matter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "note.md"
            path.write_text("# Missing front matter", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_note(path)
            path.write_text("---\ntitle: Test\ndate: invalid\nsummary: Test\n---\n\nBody", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_note(path)

    def test_unsafe_markdown_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "note.md"
            path.write_text("---\ntitle: Test\ndate: 2026-10-03\nsummary: Test\n---\n\n[link](javascript:alert(1))", encoding="utf-8")
            with self.assertRaises(ValueError):
                render_note_body(parse_note(path))


if __name__ == "__main__":
    unittest.main()
