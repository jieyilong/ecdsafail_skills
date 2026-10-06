#!/usr/bin/env python3
"""Fetch public GitHub parents in batches and missing rendered commit diffs.

No token/config access: gh handles its existing authentication. Repository data
is read-only. Existing artifacts and metadata are retained on retries.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import gzip
import http.client
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

REPO = "Layr-Labs/ecdsafail-challenge"


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def parents(rows, cache):
    destination = cache / "parents.json"
    result = json.loads(destination.read_text()) if destination.exists() else {}
    pending = sorted({row["submissionCommitSha"] for row in rows
                      if row.get("submissionCommitSha") and row["submissionCommitSha"] not in result})
    for start in range(0, len(pending), 40):
        group = pending[start:start + 40]
        selections = " ".join(
            f'c{i}: object(oid:"{sha}") {{ ... on Commit {{ oid parents(first:1) {{ nodes {{ oid }} }} }} }}'
            for i, sha in enumerate(group))
        query = 'query { repository(owner:"Layr-Labs",name:"ecdsafail-challenge") { ' + selections + ' } }'
        request = cache / "parent-query.json"
        save(request, {"query": query})
        proc = subprocess.run(["gh", "api", "graphql", "--input", str(request)],
                              capture_output=True, text=True)
        if proc.returncode:
            print("Parent query failed:", proc.stderr[-1000:], flush=True)
            break
        payload = json.loads(proc.stdout)
        if payload.get("errors"):
            print("GraphQL errors:", json.dumps(payload["errors"]), flush=True)
        objects = (payload.get("data") or {}).get("repository") or {}
        for i, sha in enumerate(group):
            obj = objects.get(f"c{i}")
            if obj:
                result[sha] = {"sha": obj["oid"], "parents": [n["oid"] for n in obj["parents"]["nodes"]],
                               "source": f"https://github.com/{REPO}/commit/{sha}"}
        save(destination, result)
        print(f"verified parent metadata: {len(result)}", flush=True)
    return result


def download(row, output):
    sid, sha = row["id"], row["submissionCommitSha"]
    destination = output / (sid + ".diff")
    url = f"https://github.com/{REPO}/commit/{sha}.diff"
    if destination.exists():
        body = destination.read_bytes()
        return sid, {"status": "cached", "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "url": url}
    error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "ECDSAFail-skills-evidence-audit", "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=600) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            if body and not body.startswith(b"diff --git "):
                raise ValueError("response was not a Git diff")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
            return sid, {"status": "downloaded", "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "url": url}
        except (OSError, ValueError, http.client.HTTPException) as exc:
            error = str(exc)
            if isinstance(exc, urllib.error.HTTPError) and exc.code in {404, 406}:
                break
            if attempt < 2:
                time.sleep(2 ** attempt)
    return sid, {"status": "error", "error": error, "url": url}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--parents", action="store_true")
    parser.add_argument("--indices", type=int, nargs="*")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    rows = json.loads(args.ledger.read_text())
    args.cache.mkdir(parents=True, exist_ok=True)
    if args.parents:
        parents(rows, args.cache)
    if args.indices is not None:
        selected = [rows[i] for i in args.indices if rows[i].get("submissionCommitSha")]
        destination = args.cache / "direct-diffs"
        receipts_path = args.cache / "diff-downloads.json"
        receipts = json.loads(receipts_path.read_text()) if receipts_path.exists() else {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(download, row, destination): row["id"] for row in selected}
            for future in as_completed(futures):
                try:
                    sid, receipt = future.result()
                except Exception as exc:
                    sid = futures[future]
                    receipt = {"status": "error", "error": str(exc)}
                receipts[sid] = receipt
                save(receipts_path, receipts)
                print(sid[:7], receipt["status"], receipt.get("bytes", receipt.get("error")), flush=True)


if __name__ == "__main__":
    main()
