#!/usr/bin/env python3
"""Merge disjoint technical review checkpoints without approving pending rows."""
import argparse
from collections import Counter
import json
from pathlib import Path


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    args = parser.parse_args()
    ledger_path = args.audit / "ledger.json"
    ledger = json.loads(ledger_path.read_text())
    allowed = {row["id"] for row in ledger}
    reviews_path = args.audit / "reviews.json"
    current = json.loads(reviews_path.read_text())
    baseline_path = args.audit / "baseline-reviews.json"
    if not baseline_path.exists():
        save(baseline_path, current)
    owner = {}
    for filename in ("reviews-early.json", "reviews-middle.json", "reviews-late.json"):
        rows = json.loads((args.audit / filename).read_text())
        for sid, review in rows.items():
            if sid not in allowed:
                raise ValueError(f"unexpected submission in {filename}: {sid}")
            if sid in owner:
                raise ValueError(f"overlapping tranche ownership: {sid}")
            owner[sid] = filename
            if review["status"] not in {"reviewed", "pending"}:
                raise ValueError(f"invalid review status: {sid}")
            if review["status"] == "reviewed":
                for field in ("mechanism", "evidence", "lesson", "metric_basis", "transfer"):
                    if not review.get(field):
                        raise ValueError(f"review missing {field}: {sid}")
                current[sid] = review
            elif sid not in current or current[sid]["status"] != "reviewed":
                current[sid] = review
    closing_path = args.audit / "reviews-closing.json"
    closing = json.loads(closing_path.read_text()) if closing_path.exists() else {}
    if set(owner) & set(closing):
        raise ValueError("closing review overlaps initial tranche ownership")
    if set(owner) | set(closing) != allowed:
        raise ValueError("tranche and closing membership do not cover the full inventory")
    for sid, review in closing.items():
        if review["status"] != "reviewed":
            raise ValueError(f"closing technical review incomplete: {sid}")
        for field in ("mechanism", "evidence", "lesson", "metric_basis", "transfer"):
            if not review.get(field):
                raise ValueError(f"closing review missing {field}: {sid}")
        current[sid] = review
    overrides = {
        "reviews-middle-primary.json": set(range(331, 335)),
        "reviews-middle-extra.json": set(range(335, 360)),
        "reviews-late-extra.json": {409} | (set(range(422, 469)) - {460}),
    }
    for filename, indices in overrides.items():
        path = args.audit / filename
        if not path.exists():
            continue
        delegated = {ledger[i]["id"] for i in indices}
        for sid, review in json.loads(path.read_text()).items():
            if sid not in delegated:
                raise ValueError(f"unexpected delegated row in {filename}: {sid}")
            if review["status"] == "reviewed":
                for field in ("mechanism", "evidence", "lesson", "metric_basis", "transfer"):
                    if not review.get(field):
                        raise ValueError(f"delegated review missing {field}: {sid}")
                current[sid] = review
    for row in ledger:
        row["review"] = current[row["id"]]
        row["review_status"] = current[row["id"]]["status"]
    summary_path = args.audit / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["review_counts"] = dict(Counter(row["review_status"] for row in ledger))
    summary["all_technical_reviews_complete"] = all(row["review_status"] == "reviewed" for row in ledger)
    save(reviews_path, current)
    save(ledger_path, ledger)
    save(summary_path, summary)
    print(json.dumps(summary["review_counts"]))


if __name__ == "__main__":
    main()
