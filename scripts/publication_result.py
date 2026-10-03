"""Write non-secret archive evidence to a run-scoped Actions artifact."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    inputs = event["inputs"]
    start, end = inputs["start"], inputs["end"]
    path = Path(f"content/news/reports/ai-agent-frontend/{start[:4]}/"
                f"ai-agent-frontend-weekly-{start}-to-{end}.html")
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
