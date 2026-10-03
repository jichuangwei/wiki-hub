"""Write non-secret archive evidence to a run-scoped Actions artifact."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

try:
    from .report_paths import repository_paths
except ImportError:
    from report_paths import repository_paths


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    inputs = event["inputs"]
    start, end = inputs["start"], inputs["end"]
    path = next((Path(value) for value in repository_paths(start, end) if Path(value).is_file()), None)
    if path is None:
        raise ValueError("Archived report is missing")
    result = {"request_id": inputs.get("request_id", ""), "start": start, "end": end,
              "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if inputs.get("expected_sha256"):
        result["previous_sha256"] = inputs["expected_sha256"]
        result["previous_revision"] = inputs["expected_revision"]
        result["review_reason"] = inputs["review_reason"]
    Path("publication.json").write_text(json.dumps(result), encoding="utf-8")


if __name__ == "__main__":
    main()
