#!/usr/bin/env python3
"""Consume workflow_dispatch JSON as data and reuse the existing archiver."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import tempfile

try:
    from .archive_report import archive_report
except ImportError:
    from archive_report import archive_report


def read_inputs(event: dict) -> tuple[str, str, str]:
    values = event.get("inputs", {})
    result = tuple(values.get(key) for key in ("start", "end", "html"))
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError("start, end and html must be non-empty strings")
    request_id = values.get("request_id", "")
    if not isinstance(request_id, str) or (request_id and not re.fullmatch(r"[a-f0-9]{32}", request_id)):
        raise ValueError("Invalid publication request ID")
    if sum(len(value) for value in result) + len(request_id) > 65535:
        raise ValueError("Combined workflow inputs exceed 65535 characters")
    # Dates are validated by archive_report before use in paths or git messages.
    return result


def main() -> None:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    start, end, content = read_inputs(event)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "report.html"
        source.write_bytes(content.encode("utf-8"))
        path, created = archive_report(source, start, end)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as output:
        output.write(f"REPORT_START={start}\nREPORT_END={end}\n")
    print(f"{'Archived' if created else 'Already archived'}: {path}")


if __name__ == "__main__":
    main()
