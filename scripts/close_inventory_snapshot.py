#!/usr/bin/env python3
"""Pin a closing public API snapshot, retaining the original audit input."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

URL = "https://api.ecdsa.fail/api/benchmarks/1ffb695a-309b-46b6-a728-2f97d8c7be74/submissions"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()
    target = args.cache / "submissions.raw.json"
    old_raw = target.read_bytes()
    old = json.loads(old_raw)["submissions"]
    with urllib.request.urlopen(URL, timeout=60) as response:
        raw = response.read()
    new = json.loads(raw)["submissions"]
    old_ids = {r["id"] for r in old}
    if not old_ids <= {r["id"] for r in new}:
        raise ValueError("closing inventory unexpectedly removed existing submissions")
    original = args.cache / "submissions.initial.raw.json"
    if not original.exists():
        original.write_bytes(old_raw)
    old_by_id = {r["id"]: r for r in old}
    changed = [r["id"] for r in new if r["id"] in old_by_id and r != old_by_id[r["id"]]]
    target.write_bytes(raw)
    receipt = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "url": URL,
               "sha256": hashlib.sha256(raw).hexdigest(), "total": len(new),
               "added": [r["id"] for r in new if r["id"] not in old_ids], "changed": changed}
    (args.cache / "closing-inventory-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
