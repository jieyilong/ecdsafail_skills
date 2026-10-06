---
name: benchmark-frontier-archaeology
description: >-
  Analyze an optimization benchmark's public submissions and code history. Use to explain a new
  SOTA, identify the mechanism behind a score change, or reconstruct a Pareto frontier including
  rejected submissions. Inspect submission notes and parent-relative diffs, walk adjacent winners,
  verify the active implementation, distinguish measured results from projections, and identify
  reusable mechanisms and the next bottleneck. For implementing circuit changes, use
  peak-qubit-reduction or toffoli-reduction.
---

# Benchmark Frontier Archaeology

For the post-June ECDSA.Fail corpus, read
[the October evidence](references/frontier-refresh-2026-10-06.md) and the relevant
tranche review in this skill's references directory. The audit covers promoted,
rejected, failed, and cancelled entries. Use its explicit per-row coverage rather
than treating source acquisition or repeated headline metrics as completed review.

When you compete on a benchmark whose accepted submissions are visible — a git history of
accepted entries, public leaderboard solutions, released configs — every time the frontier
advances you get a free lesson, *if* you can extract what actually changed. This skill is the
forensic procedure for turning "they beat me by 0.1%" into "they pulled lever X, it transfers
(or doesn't), and the next target is Y."

The output you want from each advance is three things:
1. **The mechanism package** — the active changes that drove the improvement, and any
   interactions or unisolated contributions (not formatting or inherited noise).
2. **Whether it transfers** — a reusable knob/structural idea, or a one-off search artifact.
3. **The next target** — where the binding constraint moved, so you know where to push.

## The core loop

1. **Detect & sync** the new frontier; verify it is really better by re-measuring, not by trusting the headline.
2. **Diff consecutive winners** — every adjacent accepted pair, scoped to the editable/submitted paths.
3. **Isolate the lever(s)** in each step; filter formatting/noise.
4. **Re-measure the metrics yourself** — confirm you built the circuit/artifact you think you did.
5. **Decompose** the score delta across factors and across levers.
6. **Track the moving bottleneck** — where the binding constraint went → name the next target.
7. **Classify** each lever: transferable (knob/structural) vs non-transferable (search artifact).
8. **Record the mechanism and propagate** it into your own notes/skills so the knowledge compounds.

## Step 1 — Detect, sync, and re-verify

For a repository refresh, pin the repository commit and its UTC timestamp as the cutoff.
Enumerate every subsequent submission before selecting examples. Preserve one coverage row per
submission, including failures, cancellations, missing notes, and submissions without a public
commit. Record note and diff hashes, the candidate SHA, its actual parent, official metrics,
promotion status, and review completion. Extraction is not analysis: leave a row pending until
its available note and relevant code changes have been inspected.

Keep the score winner and the Pareto frontier separate. A candidate rejected because its product
score did not improve may still be nondominated in qubits and Toffolis. Compute dominance from
official positive metrics for evaluated accepted/rejected submissions; exclude failed or merely
claimed results. Keep equal-coordinate ties. Record both the frontier at submission time and the
frontier at the pinned inventory snapshot. Retain historically useful mechanisms even after a
later candidate dominates their resource point.

Pull the new accepted submission onto a clean tree (stash your local diagnostics/instrumentation
first so they don't contaminate the diff). Then **re-measure the headline number yourself.** A
submission's claimed metric is a starting point, not ground truth — you need your own measurement
to decompose it. Watch for stale build caches: if the toolchain keys a build artifact on source
hash, an env-only change can silently measure the *old* artifact. Confirm a real rebuild happened
(look for the build to actually run) before trusting any number.

## Step 2 — Diff consecutive winners, and WALK THE INTERMEDIATES

This is the step everyone gets wrong, and it's the most important rule here:

> **Diff *adjacent* accepted submissions, never two non-adjacent endpoints.**

Competitions often advance in small steps, but one accepted submission can combine interacting
levers. If you diff submission N against submission N−5, you can bundle several mechanisms into
one blob and invent a false causal story — attributing the qubit win to the knob that only cut gates,
etc. Enumerate **every** accepted submission between your last-understood point and the new
frontier, and diff each adjacent pair (`diff <S_k> <S_{k+1}>`), scoped to the **editable/submitted
paths** for candidate attribution, and separately verify harness/interface changes that alter
metric meaning. Compiled envelopes, rewrite tables, HIR shards and other generated runtime
artifacts are part of the implementation, not disposable noise. Inspect their consumers and
provenance; exclude only irrelevant build output. If there are eight intermediate
submissions, you do eight diffs. The extra work is exactly what stops you from misreading the
frontier.

(Hard-won example: diffing a 1192-qubit winner directly against the 1193-qubit one bundled *two*
separate submissions and produced a wrong "this one knob did both" story. Walking the single
intermediate submission showed the qubit drop and the gate trim were two different levers in two
different entries.)

## Step 3 — Isolate the lever in each step

Also inspect each candidate against its own Git parent. A parent-relative patch can contain an
entire older route, so it does not by itself identify the new optimization. Establish the
candidate's architectural lineage from its dispatcher, active defaults, and source, then compare
against the relevant prior implementation as an additional diff. Do not substitute that lineage
comparison for the submission's own patch.

Follow the active build path into the emitter. A named module can delegate to the incumbent, a
selftest can be a stub returning success, and a later configuration block can be ineffective
because an earlier default already set the variable. Do not credit a projected algorithm as
implemented merely because its wrapper appears in the patch. June 29 submission `68f90fe`
labels a deferred-Lehmer route but calls the unchanged TrailMix emitter; its official metrics
tie the incumbent. July 2 submission `78f8c2b` documents the same route and adds no executable
circuit change.

Treat claimed global optima, entropy floors, and impossibility statements in notes as claims to
check. An unsuccessful local sweep establishes a limitation of that experiment, not a theorem
that later architectures cannot improve. A score tie with an empty patch is a reproduction or
platform experiment, not another optimization technique.

Within each adjacent diff, separate signal from noise:
- **Config/knob changes** — the changed parameter values (the usual lever).
- **Structural code changes** — a new function, a replaced primitive, a changed schedule.
- **Potential noise** — formatting or comments after confirming no semantic effect.
  Changed defaults and regenerated runtime artifacts require consumer inspection before
  classifying them as unchanged behavior.

Small recipe-ladder steps may reduce to one real lever. Architectural replacements, coupled
width/gate packages, and large snapshot reinstalls may change several mechanisms at once.
Record that coupling instead of forcing a single-lever causal story. Keep inherited source,
formatting noise, approximation changes, local identities, and nonce selection separate.
When attributing an error-neutral or cost delta, use explicit matched inputs and aligned
simulator randomness; the same nonce on different hashed streams does not hold the corpus fixed.

## Step 4 — Re-measure the metrics yourself

For each step, build/run the artifact and record the metrics *independently*: the headline score
plus its sub-components. Two tricks recur:
- **Recover sub-metrics by exact arithmetic.** If the score is a product (e.g. `factor_A ×
  factor_B`) and you can measure one factor, the other often falls out as an exact integer
  division — a clean way to get a sub-metric the submission didn't report. If the division is
  *not* exact, your assumption about the formula or your measurement is wrong; stop and reconcile.
- **Retain the score's rounding rule.** ECDSA.Fail publishes `Q × round(mean executed Toffoli)`.
  Dividing the official score by Q recovers the rounded gate metric, not the unrounded mean.
  Record both when available and use the rounded integer for strict product-score gates.
- **Instrument the binding constraint directly** if the toolchain supports it (a peak/hot-spot
  trace), so you can see not just *that* the metric changed but *which part of the artifact* now
  dominates it.

## Step 5 — Decompose the score delta

A single lever can move several sub-metrics at once, especially in a multi-factor objective.
Attribute the change **per factor**:
- e.g. a knob that drops one unit of factor A while *raising* factor B — separate those, and
  compute the **effective exchange rate** (units of B spent per unit of A gained) to judge whether
  it was a real win or a near-wash that only looked good because the product moved.
- A follow-up submission may be **factor-neutral on one axis** — it shaves factor B at zero cost
  to factor A (e.g. shrinking a component that no longer binds the constraint). Recognize these as
  *pure* single-factor plays; they tell you that component had gone slack.

Watch for **reversed/loosened knobs.** A new winner sometimes *undoes* an earlier tightening —
loosening a component once it stops being the bottleneck, to buy back the other factor for free.
If you assume the frontier only ever tightens, you'll misread a loosening as a regression. The
direction of a knob change is only meaningful relative to whether that component currently binds.

## Step 6 — Track the moving bottleneck → the next target

In any constrained optimization the **binding constraint migrates** as it's attacked: shave the
component that dominates the metric and a different one becomes dominant. Build the **migration
chain** across the submissions — "at score S1 the binder was phase P1; lever L moved it to P2 at
S2; …". The current binder is **your next target**, and the chain often reveals the competitor's
strategy (they're walking the bottleneck, one lever per entry). This is the single most actionable
output: not "they changed knob X" but "the constraint is now at Y, so that's where the next lever
has to land."

## Step 7 — Classify the lever: transferable vs search artifact

Decide what you can actually reuse:
- **Reusable mechanism** — a knob, fused stage, encoding or schedule worth testing on your
  line after re-establishing its interface, support, lifetime, source binding and cost.
  A structural idea is not automatically portable across architectures or ABIs.
- **Non-transferable search artifact** — a value that is only valid *because they searched for it
  against their exact configuration*: a hunted random seed/nonce, an island, a fitted constant, a
  data-order that happens to dodge a failure on their setup. Re-using their artifact on your
  (different) configuration will not reproduce the win and may silently break correctness. When a
  competitor's entry is "structural knob change + a re-hunted artifact," evaluate the mechanism
  under its port contract and re-run/revalidate the artifact against the exact new configuration.

This split is what separates "I learned their technique" from "I copied a number that won't work
for me."

## Step 8 — Record the mechanism and propagate

Write down, per advance: the lever, the measured per-factor effect, the bottleneck it exposed, and
the transferable/artifact split — then fold it into your own optimization notes/skills. The point
of archaeology is compounding: each decoded advance should make your *next* attempt sharper and
stop you from re-deriving what a competitor already showed you. A decoded frontier that isn't
written down is a lesson you'll pay for twice.

## A note on scope and ethics

This is for benchmarks where the winning entries are **legitimately visible** — an open submission
history, public leaderboard solutions, released artifacts — and you're a participant learning from
the published state of the art. It's the quantitative-competition analog of reading a published
paper's method. It is *not* a method for obtaining private or access-controlled submissions.

## Worked example (this lineage, for grounding)

A reversible point-add benchmark scored `peak_qubits × avg_executed_Toffoli`, advancing
1211 → 1193 → 1192 → 1185 qubits across accepted submissions:
- **Sync + re-measure:** synced each winner, re-derived qubits via a peak trace and `avg_Toffoli`
  via exact division of the score by the qubit count (the division being exact confirmed the
  formula and the measurement).
- **Walk intermediates:** the 1193→1192 step looked like "one knob did everything" when diffed
  endpoint-to-endpoint; walking the single intermediate accepted entry split it into *two* levers
  — a segment notch that cost the qubit (and +34 Toffoli) and a separate clean-compare trim that
  cut 442 Toffoli at **zero** qubits.
- **Decompose + exchange rate:** the 1192→1185 step *spent* +6,604 Toffoli to buy −7 qubits — a
  decompose that showed it cleared the qubit↔gate exchange rate, i.e. a real win not a wash.
- **Migration chain → next target:** binder moved GCD-apply-block → round84-square →
  materialized-special-underflow-fold → GCD-apply-chunk-sub-ripple; that last phase was the named
  next target.
- **Transferable vs artifact:** each advance = a structural knob (K5 clean-block hole, per-step
  schedule, head-11 codec) **plus** a re-hunted island nonce. The knobs transfer; the nonce is a
  search artifact that must be re-hunted against your own config.
- **Loosened knob caught:** the 1185 winner *raised* a segment knob it had previously lowered,
  because that component had gone off the peak — a loosening, not a regression.

## Relationship to the other skills

Archaeology is the **intake** stage: it tells you which lever to pull and where the bottleneck is,
then you hand off to `peak-qubit-reduction` (width levers), `toffoli-reduction` (gate levers), and
`reversible-circuit-validation` (confirm any re-hunted artifact is actually clean on your config).
For the ECDSA-fail domain specifics — the sync workflow, the exact knob catalogue, and the GPU
island re-hunt — see `ecdsafail-circuit-optimization` and `ecdsafail-island-hunting`.
