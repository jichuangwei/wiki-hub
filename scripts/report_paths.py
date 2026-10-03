"""Canonical ISO-week archive paths and legacy lookup compatibility."""
from datetime import date
from pathlib import Path


def report_paths(start: str, end: str, topic: str = "ai-agent-frontend") -> tuple[Path, Path]:
    first = date.fromisoformat(start)
    iso = first.isocalendar()
    return (Path(topic) / str(iso.year) / f"week-{iso.week}.html",
            Path(topic) / str(first.year) / f"{topic}-weekly-{start}-to-{end}.html")


def repository_paths(start: str, end: str) -> tuple[str, str]:
    return tuple(str(Path("content/news/reports") / path) for path in report_paths(start, end))
