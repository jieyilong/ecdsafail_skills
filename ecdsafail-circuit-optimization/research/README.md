# research/ — literature provenance for this skill

Annotated, re-runnable bibliography behind the skill's literature sections
(`references/external-literature-2000-2026.md`, `references/gidney-techniques.md`).
Built by `/expert-autoresearch` (8 search angles, 2000–2026). Metadata only —
**PDFs are pruned to keep the skill lean; re-fetch on demand from the URLs.**

## Files
- `index.json` — canonical index: 99 papers, each with title/authors/year/**url**/abstract/
  `relevance_note`. `local_path` is empty (PDFs not bundled). This is the lookup table: find
  the paper for a technique, then open its `url`.
- `candidates.json` — the same 99, deduped + relevance-ranked.
- `search_results/<angle>.json` — raw per-angle hits (foundational arithmetic, T/Toffoli
  synthesis, ancilla/pebbling, ECDLP point-add, modular-inverse/GCD, FT cost models, and the
  two Gidney angles). Preserves the full breadth + per-paper relevance notes.
- `search_plan.json` — the 8 angles.

## Re-fetch a PDF (when you need a deep read)
```bash
S=~/.claude/skills/expert-autoresearch/scripts
python3 $S/download.py --input research/candidates.json --output-dir research/papers/ --max 20
# or one paper:  curl -sL https://arxiv.org/pdf/<arxiv_id> -o research/papers/<arxiv_id>.pdf
```

## Extend the survey (add an angle / refresh)
1. Add an angle to `search_plan.json`, write hits to `search_results/<id>.json`.
2. `python3 $S/consolidate.py research/search_results/ research/candidates.json`
3. `python3 $S/build_index.py research/candidates.json research/papers/ research/index.json`
4. Fold actionable findings into the `references/*.md` and `SKILL.md`.
