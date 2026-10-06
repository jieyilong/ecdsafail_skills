# Completed submission audit, October 6, 2026

Scope: all submissions created after skills commit
`08a60e4f8fafb26363b43a9d206d815e3f7d618a`, committed June 28 at
19:15:59 UTC, through the closing public API snapshot retrieved October 6 at
04:32:17 UTC. The initial snapshot had 585 later submissions; the closing
snapshot adds one, with no changes to the existing entries.

All 586 received technical review of the full available note and active
implementation delta: 557 public candidate commits with exact Git parents,
and 29 explicit no-public-commit limitations. One entry has no substantive
note. Large generated tables/shards were inspected through their consumers,
contracts, structure and artifact identities; this does not claim a proof of
each numeric record. No contestant circuit, evaluator or GPU job was executed.

## Published evidence

- [ledger.json](ledger.json): chronological per-submission source, note and raw
  diff hashes; official metrics/outcomes; current and historical frontier status;
  technical conclusions and source availability.
- [reviews.json](reviews.json): complete UUID-keyed mechanism, inspection,
  transfer lesson, metric basis and limitations.
- [summary.json](summary.json): closing inventory hash, totals and completion.
- [skill-quality-review.md](skill-quality-review.md): independent forward-use
  review and correction history, not a whole-circuit correctness certificate.

The public note source is the [official inventory](https://api.ecdsa.fail/api/benchmarks/1ffb695a-309b-46b6-a728-2f97d8c7be74/submissions).
Match each row by its full UUID. `note_path` and evidence-cache paths describe
the reproducible local cache, not files shipped here. Raw repeated notes,
multi-gigabyte source patches, orchestration checkpoints and upload credentials
are kept outside the published package; public commit/diff URLs and hashes remain.
The initial and closing snapshots are retained locally. The closing hash is in
`summary.json`; the API is mutable, so a later download may differ.

To reproduce, pin the API JSON and exact parents, use
`scripts/audit_submissions.py` and `scripts/fetch_public_evidence.py` to rebuild
the notes/patch cache, then run `scripts/verify_audit_sources.py` with
`--require-reviewed`. Extracting or hashing a patch is not technical review.
Read the [architectural synthesis](../../references/frontier-refresh-2026-10-06.md)
for route selection and reusable methods. Rejected scalar scores may be valid
Pareto points; failed/local-only claims are not official clean points.
