#!/usr/bin/env python3
"""Generate portable per-skill copies from one maintained evidence source."""
import argparse
import hashlib
from pathlib import Path

SKILLS = ["benchmark-frontier-archaeology", "ecdsafail-circuit-optimization",
          "ecdsafail-island-hunting", "ecdsafail-multi-agent-collaboration",
          "peak-qubit-reduction", "reversible-circuit-validation", "toffoli-reduction"]
NAMES = ["frontier-refresh-2026-10-06.md", "refresh-early.md",
         "refresh-middle.md", "refresh-middle-primary.md", "refresh-middle-extra.md",
         "refresh-late.md", "refresh-late-extra.md", "refresh-closing.md"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    copied = 0
    for name in NAMES:
        raw = (args.root / "references" / name).read_bytes()
        header = (f"<!-- Generated from repository references/{name}; "
                  f"source SHA256 {hashlib.sha256(raw).hexdigest()}. "
                  "Edit the maintained source, then run scripts/sync_shared_references.py. -->\n\n")
        for skill in SKILLS:
            target = args.root / skill / "references" / name
            if target.exists() and not target.read_text().startswith("<!-- Generated from repository references/"):
                raise ValueError(f"refusing to overwrite an independently maintained file: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(header.encode() + raw)
            copied += 1
    # This diagnostic is explicitly named by the portable reference. It uses
    # only stdlib and the independently written local equations, not contestant code.
    diagnostic = args.root / "scripts/test_shared_pair_codec.py"
    raw = diagnostic.read_bytes()
    header = ("# Generated from repository scripts/test_shared_pair_codec.py; "
              "edit the maintained source, then sync shared references.\n")
    for skill in SKILLS:
        target = args.root / skill / "scripts/test_shared_pair_codec.py"
        if target.exists() and not target.read_text().startswith("# Generated from repository scripts/"):
            raise ValueError(f"refusing to overwrite independent diagnostic: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(header.encode() + raw)
    print(f"synchronized {copied} portable reference files")


if __name__ == "__main__":
    main()
