#!/usr/bin/env python3
"""Verify complete evidence coverage and raw artifact identity for the audit."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def evidence_objects(value):
    """Support both structured and legacy list-format authored receipts."""
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from evidence_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from evidence_objects(item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--require-reviewed", action="store_true")
    args = parser.parse_args()
    inventory = json.loads((args.cache / "submissions.raw.json").read_text())["submissions"]
    summary = json.loads((args.audit / "summary.json").read_text())
    expected = {row["id"] for row in inventory if row["createdAt"] > summary["cutoff"]}
    ledger = json.loads((args.audit / "ledger.json").read_text())
    if len(ledger) != len(expected) or {row["id"] for row in ledger} != expected:
        raise ValueError("ledger does not match the complete post-cutoff inventory")
    parents = json.loads((args.cache / "parents.json").read_text())
    verified, errors = [], []
    folders = ["diffs", "direct-diffs", "middle-diffs", "late-diffs"]
    for row in ledger:
        sid = row["id"]
        note = args.audit / row["note_path"]
        if not note.is_file() or digest(note) != row["note_sha256"]:
            errors.append(f"note identity: {sid}")
        commit = row["submissionCommitSha"]
        hashes = set()
        if commit:
            found = [args.cache / folder / (sid + suffix)
                     for folder in folders for suffix in (".patch", ".diff")
                     if (args.cache / folder / (sid + suffix)).is_file()]
            hashes = {digest(path) for path in found}
            if row.get("diff_status") != "collected" or row.get("diff_sha256") not in hashes:
                errors.append(f"diff identity: {sid}")
            if commit not in parents or row.get("parent_commit") not in parents[commit]["parents"]:
                errors.append(f"parent identity: {sid}")
        elif row["diff_status"] != "no_public_commit":
            errors.append(f"unrecorded public source absence: {sid}")
        if args.require_reviewed and row["review_status"] != "reviewed":
            errors.append(f"technical review incomplete: {sid}")
        review = row.get("review", {})
        if row["review_status"] == "reviewed":
            for field in ("mechanism", "evidence", "lesson", "metric_basis", "transfer"):
                if not review.get(field):
                    errors.append(f"technical review missing {field}: {sid}")
            for receipt in evidence_objects(review.get("evidence")):
                for key in ("diff_sha256", "patch_sha256"):
                    # Git binary patches and GitHub rendered patches can both
                    # represent the same candidate/parent with different bytes.
                    if receipt.get(key) and receipt[key] not in hashes:
                        errors.append(f"authored review diff identity: {sid}")
                if receipt.get("note_sha256") and receipt["note_sha256"] != row["note_sha256"]:
                    errors.append(f"authored review note identity: {sid}")
                for key in ("commit", "submission_commit"):
                    if receipt.get(key) and receipt[key] != commit:
                        errors.append(f"authored review candidate identity: {sid}")
                if receipt.get("parent") and receipt["parent"] != row.get("parent_commit"):
                    errors.append(f"authored review parent identity: {sid}")
        verified.append(sid)
    report = {"submissions_checked": len(verified), "diffs": dict(Counter(r["diff_status"] for r in ledger)),
              "reviews": dict(Counter(r["review_status"] for r in ledger)), "errors": errors}
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
