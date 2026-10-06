#!/usr/bin/env python3
"""Index every note and complete cached diff for bounded, source-backed review.

Output is extraction, not proof or automatic review approval. Large data tables and
inherited snapshots remain hashed in the complete patch cache.
"""
from collections import Counter
import argparse
import hashlib
import json
import re
from pathlib import Path


def paragraphs(note):
    return [p.strip() for p in re.split(r"\n\s*\n", note) if p.strip()]


def patch_index(text):
    files = []
    current = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            path = line.split(" b/", 1)[-1]
            current = {"path": path, "added_lines": 0, "removed_lines": 0,
                       "declarations": [], "config_changes": [], "added_code": []}
            files.append(current)
        elif current is not None and line[:1] in {"+", "-"} and not line.startswith(("+++", "---")):
            current["added_lines" if line[0] == "+" else "removed_lines"] += 1
            code = line[1:].strip()
            if re.match(r"(?:pub(?:\([^)]*\))?\s+)?(?:fn |def |class |const |static |struct |enum )", code):
                current["declarations"].append(line)
            if ("set_default_env(" in code or "set_var(" in code
                    or re.match(r"[+-].*(?:const|static).*\b(?:ITERS|STEPS|QCAP|CAP|PAD|LSBS|MSBS)\b", line)):
                current["config_changes"].append(line)
            if (line.startswith("+") and current["path"].endswith((".rs", ".py", ".cpp", ".cu"))
                    and not code.startswith(("//", "#")) and code):
                current["added_code"].append(code)
    for item in files:
        item["added_code_sha256"] = hashlib.sha256("\n".join(item.pop("added_code")).encode()).hexdigest()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()
    ledger = json.loads((args.audit / "ledger.json").read_text())
    notes = {r["id"]: (args.audit / r["note_path"]).read_text() for r in ledger}
    freq = Counter(p for note in notes.values() for p in set(paragraphs(note)))
    rows = []
    for i, row in enumerate(ledger):
        note = notes[row["id"]]
        patch_file = args.cache / (row["id"] + ".patch")
        patch = patch_file.read_text() if patch_file.exists() else None
        selected = []
        for paragraph in paragraphs(note):
            if freq[paragraph] > 5:
                continue
            if re.match(r"^(?:Model:|Harness:|Credit:|AI Coding Models:|Join us on|This work was sponsored)", paragraph):
                continue
            selected.append(paragraph)
        files = patch_index(patch) if patch is not None else []
        rows.append({"index": i, "id": row["id"], "date": row["createdAt"],
                     "status": row["status"], "metrics": row["officialMetrics"],
                     "score": row["officialScore"], "current_pareto": row["current_pareto"],
                     "historical_pareto": row["historically_nondominated"],
                     "note_unique_paragraphs": selected,
                     "note_bytes": len(note.encode()), "note_sha256": row["note_sha256"],
                     "complete_patch_scanned": patch is not None,
                     "patch_bytes": len(patch.encode()) if patch is not None else None,
                     "patch_sha256": hashlib.sha256(patch.encode()).hexdigest() if patch is not None else None,
                     "files": files})
    destination = args.audit / "evidence-index.json"
    destination.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"rows": len(rows), "complete_diffs_scanned": sum(r["complete_patch_scanned"] for r in rows),
                      "index_bytes": destination.stat().st_size}))


if __name__ == "__main__":
    main()
