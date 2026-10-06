#!/usr/bin/env python3
"""Bind explicitly authored primary conclusions to canonical public evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit/2026-10-06"
CACHE = ROOT.parent / "research/ecdsafail-skills-refresh-20261006/middle-diffs"


def main():
    ledger = json.loads((AUDIT / "ledger.json").read_text())
    cases = json.loads((AUDIT / "primary-review-cases.json").read_text())
    result = {}
    for index, authored in cases.items():
        row = ledger[int(index)]
        patch = CACHE / (row["id"] + ".patch")
        raw = patch.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != row["diff_sha256"]:
            raise ValueError(f"primary patch changed: {row['id']}")
        review = dict(authored)
        inspection = review.pop("inspection")
        review["evidence"] = {
            "index": int(index), "note_path": row["note_path"], "note_sha256": row["note_sha256"],
            "submission_commit": row["submissionCommitSha"], "parent": row["parent_commit"],
            "diff_sha256": digest, "inspection": inspection,
            "source_url": f"https://github.com/Layr-Labs/ecdsafail-challenge/commit/{row['submissionCommitSha']}",
        }
        result[row["id"]] = review
    (AUDIT / "reviews-middle-primary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"bound {len(result)} explicitly reviewed primary entries")


if __name__ == "__main__":
    main()
