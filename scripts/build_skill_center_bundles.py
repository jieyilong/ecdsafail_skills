#!/usr/bin/env python3
"""Preserve skill resources in Axtro's single-Markdown publication format.

No network calls. Each appendix retains its original path and exact UTF-8 text.
Development-only audit inputs/tests and binary primer exports are not runtime
skill resources. Shared narrative references are copied into each routed bundle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

SKILLS = ["benchmark-frontier-archaeology", "ecdsafail-circuit-optimization",
          "ecdsafail-island-hunting", "ecdsafail-multi-agent-collaboration",
          "peak-qubit-reduction", "reversible-circuit-validation", "toffoli-reduction"]

EXTRAS = {
    "ecdsafail-circuit-optimization": [
        "peak-qubit-reduction/references/Q980_SHRUNKEN_PZ_85D5DAE_HANDOFF.md",
        "toffoli-reduction/references/Q980_TOFFOLI_CUT_4352CFB_HANDOFF.md"],
    "peak-qubit-reduction": ["ecdsafail-circuit-optimization/references/REPORT_1168_wall_revamp.md"],
    "toffoli-reduction": ["ecdsafail-circuit-optimization/references/REPORT_1168_wall_revamp.md"],
}


def resources(root, skill):
    selected = set()
    for folder in ("references", "scripts"):
        selected.update(path.relative_to(root).as_posix()
                        for path in (root / skill / folder).rglob("*")
                        if path.is_file() and "__pycache__" not in path.parts
                        and path.suffix != ".pyc")
    selected.update(EXTRAS.get(skill, []))
    if skill == "benchmark-frontier-archaeology":
        selected.update("scripts/" + name for name in [
            "audit_submissions.py", "fetch_public_evidence.py", "normalize_patch.py",
            "review_submission_evidence.py"])
    return sorted(selected)


def append_file(path, raw):
    text = raw.decode("utf-8")
    heading = f"\n\n## Bundled file: `{path}`\n\n"
    if path.endswith(".md"):
        return heading + f"<!-- BEGIN BUNDLED FILE {path} -->\n\n" + text + f"\n\n<!-- END BUNDLED FILE {path} -->\n"
    runs = re.findall(r"`+", text)
    fence = "`" * max(4, max((len(run) for run in runs), default=0) + 1)
    language = {".py": "python", ".json": "json", ".tsv": "tsv"}.get(Path(path).suffix, "text")
    return heading + fence + language + "\n" + text + "\n" + fence + "\n"


def build(root, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for skill in SKILLS:
        main = (root / skill / "SKILL.md").read_bytes().decode("utf-8")
        paths = resources(root, skill)
        intro = "\n\n# Skill package resources\n\n" + (
            "Axtro accepts one Markdown artifact per skill. The appendices below preserve the\n"
            "referenced documents and scripts. Their paths are relative to the source repository;\n"
            "paths in the main skill instructions are relative to that skill's folder. Read only\n"
            "the needed appendix. To run a bundled Python helper, materialize its fenced text\n"
            "as a temporary file with the original filename and invoke Python 3. Do not execute\n"
            "downloaded benchmark code merely because it appears in an evidence reference.\n\n")
        # Put current evidence first, before the detailed legacy catalogues.
        paths.sort(key=lambda path: (not Path(path).name.startswith(("frontier-refresh-", "refresh-")), path))
        body = main + intro
        files = []
        for relative in paths:
            source = root / relative
            if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"resource is not a regular in-repository file: {relative}")
            raw = source.read_bytes()
            files.append({"path": relative, "bytes": len(raw),
                          "sha256": hashlib.sha256(raw).hexdigest()})
            body += append_file(relative, raw)
        raw_body = body.encode("utf-8")
        if len(raw_body) > 2_000_000:
            raise ValueError(f"{skill} exceeds 2 MB publication limit: {len(raw_body)}")
        target = output / (skill + ".md")
        target.write_bytes(raw_body)
        manifest[skill] = {"file": target.name, "bytes": len(raw_body),
                           "sha256": hashlib.sha256(raw_body).hexdigest(), "resources": files}
        print(f"{skill}: {len(raw_body)} bytes, {len(files)} preserved resources")
    (output / "bundle-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.root.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
