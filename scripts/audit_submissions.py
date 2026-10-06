#!/usr/bin/env python3
"""Collect a reproducible, complete post-cutoff submission evidence ledger.

Reads public API JSON and an existing Git object store. It never resets a checkout,
runs submission code, or treats submitted prose as instructions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--git-dir", str(repo), *args],
                          capture_output=True, text=True)


def valid_metrics(row: dict) -> bool:
    metrics = row.get("officialMetrics") or {}
    return (row.get("status") in {"accepted", "rejected"}
            and isinstance(metrics.get("qubits"), (int, float))
            and isinstance(metrics.get("toffoli"), (int, float))
            and metrics["qubits"] > 0 and metrics["toffoli"] > 0)


def frontier(rows: list[dict]) -> list[str]:
    grouped: dict[tuple[float, float], list[str]] = {}
    for row in rows:
        if valid_metrics(row):
            metrics = row["officialMetrics"]
            grouped.setdefault((metrics["qubits"], metrics["toffoli"]), []).append(row["id"])
    result: list[str] = []
    best_t = float("inf")
    for (_, t), ids in sorted(grouped.items()):
        if t < best_t:
            result.extend(ids)
            best_t = t
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--git-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diff-cache", type=Path,
                        help="Keep large full patches outside the published skills repository")
    parser.add_argument("--parent-map", type=Path)
    parser.add_argument("--rendered-diff-dir", type=Path, action="append", default=[])
    parser.add_argument("--cutoff", default="2026-06-28T19:15:59Z")
    parser.add_argument("--cutoff-commit", default="08a60e4f8fafb26363b43a9d206d815e3f7d618a")
    args = parser.parse_args()
    payload = json.loads(args.inventory.read_text())
    all_rows = sorted(payload["submissions"], key=lambda x: (x["createdAt"], x["id"]))
    rows = [row for row in all_rows if row["createdAt"] > args.cutoff]
    current_frontier = set(frontier(all_rows))
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    reviews_path = out / "reviews.json"
    reviews = json.loads(reviews_path.read_text()) if reviews_path.exists() else {}
    public_parents = json.loads(args.parent_map.read_text()) if args.parent_map else {}
    ledger = []
    for row in rows:
        sid = row["id"]
        short = sid[:7]
        entry = {key: row.get(key) for key in (
            "id", "solverUsername", "status", "promotionStatus", "createdAt",
            "updatedAt", "claimedScore", "officialScore", "officialMetrics",
            "rejectionReason", "submissionCommitSha", "promotedSourceRef")}
        note = row.get("note") or ""
        note_path = out / "notes" / (sid + ".md")
        note_path.parent.mkdir(exist_ok=True)
        note_path.write_text(note)
        entry.update(note_present=bool(note.strip()),
                     note_path=f"notes/{sid}.md",
                     note_sha256=hashlib.sha256(note.encode()).hexdigest(),
                     current_pareto=sid in current_frontier,
                     historically_nondominated=sid in frontier([
                         other for other in all_rows if other["createdAt"] <= row["createdAt"]]),
                     review_status="pending")
        commit = row.get("submissionCommitSha")
        cached_patch = (args.diff_cache or out / "diffs") / (sid + ".patch")
        rendered = next((directory / (sid + suffix) for directory in args.rendered_diff_dir
                         for suffix in (".diff", ".patch")
                         if (directory / (sid + suffix)).exists()), None)
        # Rendered downloads are read only after complete HTTP responses. Their
        # directory must contain only complete artifacts, never curl partials.
        source = cached_patch if cached_patch.exists() else rendered
        if not commit:
            entry["diff_status"] = "no_public_commit"
            entry["diff_limitation"] = row.get("rejectionReason") or row.get("status")
        elif source is not None and commit in public_parents:
            parent_list = public_parents[commit]["parents"]
            parent = parent_list[0] if parent_list else None
            raw_patch = source.read_bytes()
            patch = raw_patch.decode("utf-8")
            paths = [line.split(" b/", 1)[-1] for line in patch.splitlines()
                     if line.startswith("diff --git ")]
            entry.update(parent_commit=parent, diff_status="collected",
                         diff_format="git_binary_patch" if source == cached_patch else "github_rendered_diff",
                         diff_cache_file=source.name,
                         diff_url=f"https://github.com/Layr-Labs/ecdsafail-challenge/commit/{commit}.diff",
                         diff_sha256=hashlib.sha256(raw_patch).hexdigest(),
                         diff_bytes=len(raw_patch), changed_paths=paths)
        elif args.parent_map is not None:
            # Acquisition is explicit in this mode: do not trigger Git's lazy
            # network fetch for an absent artifact in a partial clone.
            entry["diff_status"] = "awaiting_public_diff"
        elif git(args.git_dir, "cat-file", "-e", commit + "^{commit}").returncode:
            entry["diff_status"] = "commit_not_in_cache"
        else:
            parents = git(args.git_dir, "rev-list", "--parents", "-n", "1", commit).stdout.split()
            parent = parents[1] if len(parents) > 1 else None
            entry["parent_commit"] = parent
            diff_args = ["diff", "--no-ext-diff", "--no-renames", "--binary"]
            if parent:
                diff_args += [parent, commit, "--", "src/point_add"]
            else:
                diff_args = ["show", "--format=", "--binary", commit, "--", "src/point_add"]
            diff = git(args.git_dir, *diff_args)
            if diff.returncode:
                entry["diff_status"] = "diff_error"
                entry["diff_limitation"] = diff.stderr[-2000:]
            else:
                diff_path = (args.diff_cache or out / "diffs") / (sid + ".patch")
                diff_path.parent.mkdir(exist_ok=True)
                diff_path.write_text(diff.stdout)
                entry.update(diff_status="collected", diff_cache_file=sid + ".patch",
                             diff_format="git_binary_patch",
                             diff_url=f"https://github.com/Layr-Labs/ecdsafail-challenge/compare/{parent}...{commit}",
                             diff_sha256=hashlib.sha256(diff.stdout.encode()).hexdigest(),
                             diff_bytes=len(diff.stdout.encode()),
                             diff_stat=git(args.git_dir, "diff", "--stat", parent or commit,
                                           commit, "--", "src/point_add").stdout,
                             changed_paths=git(args.git_dir, "diff", "--name-only",
                                               parent or commit, commit,
                                               "--", "src/point_add").stdout.splitlines())
        if sid in reviews:
            entry["review"] = reviews[sid]
            entry["review_status"] = reviews[sid]["status"]
        ledger.append(entry)
        print(f"{short} {entry['diff_status']}", flush=True)
    dump(out / "ledger.json", ledger)
    dump(out / "summary.json", {
        "cutoff": args.cutoff, "cutoff_commit": args.cutoff_commit,
        "inventory_sha256": hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
        "inventory_total": len(all_rows), "post_cutoff": len(rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "diff_counts": dict(Counter(row["diff_status"] for row in ledger)),
        "review_counts": dict(Counter(row["review_status"] for row in ledger)),
        "all_current_pareto": sorted(current_frontier),
        "patches_published": args.diff_cache is None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })


if __name__ == "__main__":
    main()
