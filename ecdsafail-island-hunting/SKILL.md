---
name: ecdsafail-island-hunting
description: >-
  Design and operate source-bound nonce searches for ECDSA.Fail point-addition circuits.
  Use for GPU prescreens, packet density/error triage, runtime estimates, candidate validation,
  or deciding whether a structural route is worth hunting. Require architecture-matched
  filters, exact source/table/corpus binding, and full trusted validation; distinguish
  empirical error estimates, partial phase debt, and verified clean packets.
---

# ECDSA.Fail Island Hunting

Turn an eligible structural route into a reproducible clean packet. Read
[the October evidence](references/frontier-refresh-2026-10-06.md) before selecting a
current route. The older parameter grids, family-specific triage recipes, and detailed
runtime examples remain in [the June catalogue](references/legacy-playbook-2026-06.md).
Use them only with the matching emitter. The current product architecture is Skywalk,
not the June TrailMix/Dialog emitter.

## Freeze a complete hunt identity

Record the exact source commit, effective build recipe, active dispatcher, compiled
tables/templates, op-stream prefix, tail encoding, generator/evaluator versions, and
Q/T/score basis. Clear or pin experiment overlays as the actual builder requires.
Count-only and estimated metrics cannot replace the official full-circuit measurement.

Identity-tail changes preserve the intended computational prefix when correctly encoded,
but change the full operation stream, its digest, and the SHAKE-derived input corpus.
Keep separate body/prefix and full-stream hashes. Source changes can invalidate both a
nonce and an ordinal/tuple-keyed rewrite certificate. Matching the tuple is insufficient
if the intermediate support or schedule changed.

## Gate the objective and route first

Refresh the current official product incumbent and clean Pareto set. The strict rounded
T gate at width Q is `(incumbent_score - 1) // Q`. A user pursuing width or Pareto
tradeoffs may intentionally target a product-rejected point; state that objective.

Run full fresh-packet samples on candidate routes before allocating broad nonce ranges.
Record final classical, phase, and ancilla failures separately, along with raw/rounded T.
Diagnose deterministic invariants and persistent scratch corruption. A sampled channel
that never reaches zero suggests a tail or defect to investigate; it does not establish
an unreachable island without a proved positive lower bound.

## Use an architecture-matched prescreen

A classical model of Dialog GCD is not an oracle for TrailMix, Pingpong, Skywalk, or an
executable fixed-schedule EEA merely because all routes compute inversion. Check the
actual walk, width schedule, endpoint repair, field payload, and supported approximations.

Run source-bound control shots against the trusted native evaluator. Report false
rejections and conservative over-admissions separately, with cohort size and source.
An empirical zero false-rejection count is evidence about that cohort, not a universal
soundness proof. Revalidate the filter after every relevant source or recipe change.

Partial phase is not a final failure: later uncompute/corrections may cancel it. A
partial-phase K score can rank candidates, but do not hard-reject K>0 unless the
remainder of the circuit is proved unable to repair that debt. Similarly, use early
classical/scratch rejection only for a proved obstruction at that boundary.

## Measure the two-stage hunt, not density alone

For a matching Stage-1 screen, estimate candidate density d and screen throughput R.
For its survivors, use full trusted evaluations to estimate q=P(final C/P/A=0/0/0
given a screen pass) and time per evaluation. The per-nonce clean probability is d*q.
Correlation, overdispersion, rare tails, and sampling uncertainty can invalidate a
simple Poisson estimate or a claimed channel floor. State model assumptions and
confidence limits instead of deriving certainty from a modest panel.

Use the bundled model for an explicitly stated estimate. Run it from the skill
directory, or use the resolved path to its script:

```bash
python scripts/island_runtime_model.py --density 1.5e-8 --q 0.7 --rate 5000 --t-eval 15 --concurrent
```

It is a planning model, not a proof of reachability or runtime. Distinguish nonce
packets, individual shots, and failure batches. Keep an empirical lambda proxy separate
from an all-input correctness claim and from the observed clean-packet rate.

## Repair and compare before scaling

For each candidate, freeze its source, score margin, peak owner, raw failure channels,
and the smallest diagnostic reproducing its bottleneck. Restore the specific width,
carry, comparison, cleanup, or alias-lifetime invariant, then remeasure both resources.
Do not keep tightening an approximation while calling the change exact.

For a claimed differential/error-neutral optimization, compare on explicit matched
inputs and aligned measurement/random streams. Equal coarse counts or the same nonce
on changed op streams does not establish equality of the tested inputs or output states.
Preserve holdout evidence separately from the data used to select a skip set.

## Operate the authorized search

Assign disjoint ranges, persist coverage and artifact identities, and track throughput,
candidate backlog, best final failure triples, and validator agreement. Validate every
survivor, not merely a trust-check sample. A small local/remote cross-check establishes
trust in the evaluator deployment, not validation of the other survivors.

If progress monitoring is requested, use the environment's durable monitor/wait mechanism
and report meaningful changes. A search request does not grant access to unspecified
hosts, fleet credentials, or unrelated platform changes.

## Close with a source-identical trusted packet

Pin the selected nonce in the production recipe and rebuild the exact submitted source
without inherited experiment overlays. Match the operation stream/body to the trusted
packet before an independent complete 9024-shot evaluation. Require zero final
classical, phase, and ancilla failures, official Q, rounded T, and the correct score.
Report fresh-packet error estimates and any disclosed approximation tradeoff separately.

A locally clean partial test or a failed server run does not add a verified frontier
point. Packaging, forbidden runtime file reads, op-count limits, memory pressure, and
workflow timeouts can fail an otherwise promising route; preserve the exact failure stage
rather than labeling all such outcomes arithmetic failures. Submit only within the
user's authorized objective and submission scope, with required provenance and notes.
