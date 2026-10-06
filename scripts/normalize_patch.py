#!/usr/bin/env python3
"""Present textual hunks after removing line-ending noise; not an equivalence proof.

Displayed line numbers are offsets in concatenated hunk fragments, not source
line references. Use the original patch or Git blobs for source citations.
"""
import argparse
import difflib
from pathlib import Path


def normalize(text):
    files = []
    path, before, after = None, [], []
    def finish():
        if path is None:
            return
        changed = list(difflib.unified_diff(before, after, fromfile="a/" + path,
                                            tofile="b/" + path, lineterm="", n=3))
        if changed:
            files.append("\n".join(changed))
    in_hunk = False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            finish()
            path = line.split(" b/", 1)[-1]
            before, after = [], []
            in_hunk = False
        elif line.startswith("@@ "):
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            after.append(line[1:])
        elif in_hunk and line.startswith("-"):
            before.append(line[1:])
        elif in_hunk and line.startswith(" "):
            before.append(line[1:])
            after.append(line[1:])
    finish()
    return "\n\n".join(files) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = normalize(args.patch.read_text())
    if args.output:
        args.output.write_text(result)
        print(f"normalized {args.patch.stat().st_size} to {len(result.encode())} bytes")
    else:
        print(result)


if __name__ == "__main__":
    main()
