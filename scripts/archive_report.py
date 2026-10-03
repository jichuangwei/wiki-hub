#!/usr/bin/env python3
"""Validate and append a weekly email without replacing previous issues."""
from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path
import re
import tempfile

try:
    from .report_paths import report_paths
    from .build_site import REPORTS, DEEP_CATEGORY, parse_issue
except ImportError:
    from report_paths import report_paths
    from build_site import REPORTS, DEEP_CATEGORY, parse_issue


def archive_report(source: Path, start: str, end: str, topic: str = "ai-agent-frontend",
                   root: Path = REPORTS, expected_sha256: str | None = None) -> tuple[Path, bool]:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic):
        raise ValueError("Invalid report topic")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first.weekday() != 0 or last.weekday() != 6 or (last - first).days != 6:
        raise ValueError("Report range must be a full Monday–Sunday week")
    canonical, legacy = report_paths(start, end, topic)
    content = source.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        candidate = Path(directory) / canonical
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(content)
        issue = parse_issue(candidate)
        if topic == "ai-agent-frontend" and issue.categories != [DEEP_CATEGORY]:
            counts = Counter(article.category for article in issue.articles)
            if any(not 2 <= count <= 4 for count in counts.values()):
                raise ValueError("Each AI category must have 2–4 articles")
        for heading in ("一句话趋势总结", "本周动手验证", "团队行动建议"):
            if heading not in content.decode("utf-8"):
                raise ValueError(f"Missing report section: {heading}")
    target = root / canonical
    if not target.exists() and (root / legacy).exists():
        target = root / legacy
    if expected_sha256 is not None:
        if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
            raise ValueError("Invalid expected archive digest")
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError("Archive changed or is missing; reviewed update refused")
        target.write_bytes(content)
        return target, True
    if target.exists():
        if target.read_bytes() == content:
            return target, False
        raise FileExistsError(f"Existing issue differs; explicit correction required: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output:
        output.write(content)
    return target, True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--topic", default="ai-agent-frontend")
    args = parser.parse_args()
    path, created = archive_report(args.input, args.start, args.end, args.topic)
    print(f"{'Archived' if created else 'Already archived'}: {path}")


if __name__ == "__main__":
    main()
