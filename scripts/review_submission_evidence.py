#!/usr/bin/env python3
"""Print one bounded review batch, without mistaking extraction for analysis."""
import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("diff_cache", type=Path)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=15)
    parser.add_argument("--full-notes", action="store_true")
    args = parser.parse_args()
    rows = json.loads((args.audit / "ledger.json").read_text())
    for index, row in enumerate(rows[args.start:args.start + args.count], args.start):
        print(f"\n[{index}] {row['id']} {row['createdAt']} {row['status']}")
        print("Metrics:", row["officialMetrics"], "current Pareto:", row["current_pareto"],
              "historical Pareto:", row["historically_nondominated"])
        print("Commit:", row["submissionCommitSha"], "parent:", row.get("parent_commit"))
        print("Reason:", row["rejectionReason"])
        note = (args.audit / row["note_path"]).read_text()
        if args.full_notes:
            print("NOTE:\n" + note)
        else:
            print("NOTE EXCERPTS (not a full review):\n" + note[:2400])
        patch_path = args.diff_cache / (row["id"] + ".patch")
        if patch_path.exists():
            patch = patch_path.read_text()
            print("Diff sha256:", row.get("diff_sha256"))
            print("Paths:\n" + "\n".join(row.get("changed_paths", [])))
            signatures = [line for line in patch.splitlines()
                          if re.match(r"^[+-](?:pub(?:\([^)]*\))?\s+)?(?:fn |def |class |const |static |struct |enum )", line)]
            print("Changed declarations:\n" + "\n".join(signatures[:100]))
            print("Diff preview:\n" + patch[:4500])
        else:
            print("DIFF:", row["diff_status"])


if __name__ == "__main__":
    main()
