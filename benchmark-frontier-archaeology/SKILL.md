---
name: benchmark-frontier-archaeology
description: >-
  Reverse-engineer a competitive optimization benchmark's advancing frontier: when a competitor
  or new SOTA submission beats your score and the winning entries are visible (a git history of
  accepted submissions, public leaderboard solutions, released configs), extract exactly which
  lever drove the improvement and whether it transfers to you. Use whenever "a new SOTA was
  submitted, analyze it", "diff the new leaderboard winner", "what did they change / what lever
  did they use", "reverse-engineer their improvement", "figure out what drove the score jump",
  or you need to learn from a competitor's accepted entry on a benchmark you're optimizing.
  Covers diffing consecutive winners, walking every intermediate submission (not just
  endpoints), re-measuring the metrics yourself, decomposing a multi-factor score delta,
  separating a transferable lever from a non-transferable search artifact, and tracking the
  moving bottleneck so you know the next target. For DOING the optimization, use
  peak-qubit-reduction / toffoli-reduction; this skill is the forensic analysis that feeds them.
---

# Benchmark Frontier Archaeology

When you compete on a benchmark whose accepted submissions are visible — a git history of
accepted entries, public leaderboard solutions, released configs — every time the frontier
advances you get a free lesson, *if* you can extract what actually changed. This skill is the
forensic procedure for turning "they beat me by 0.1%" into "they pulled lever X, it transfers
(or doesn't), and the next target is Y."

The output you want from each advance is three things:
1. **The lever** — the single change that drove the improvement (not the noise around it).
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

Pull the new accepted submission onto a clean tree (stash your local diagnostics/instrumentation
first so they don't contaminate the diff). Then **re-measure the headline number yourself.** A
submission's claimed metric is a starting point, not ground truth — you need your own measurement
to decompose it. Watch for stale build caches: if the toolchain keys a build artifact on source
hash, an env-only change can silently measure the *old* artifact. Confirm a real rebuild happened
(look for the build to actually run) before trusting any number.

## Step 2 — Diff consecutive winners, and WALK THE INTERMEDIATES

This is the step everyone gets wrong, and it's the most important rule here:

> **Diff *adjacent* accepted submissions, never two non-adjacent endpoints.**

Competitions advance in small steps, and each accepted submission is usually *one* lever. If you
diff submission N against submission N−5, you bundle five independent levers into one blob and
invent a false causal story — attributing the qubit win to the knob that actually only cut gates,
etc. Enumerate **every** accepted submission between your last-understood point and the new
frontier, and diff each adjacent pair (`diff <S_k> <S_{k+1}>`), scoped to the **editable/submitted
paths** only (ignore graders, harness, and generated files). If there are eight intermediate
submissions, you do eight diffs. The extra work is exactly what stops you from misreading the
frontier.

(Hard-won example: diffing a 1192-qubit winner directly against the 1193-qubit one bundled *two*
separate submissions and produced a wrong "this one knob did both" story. Walking the single
intermediate submission showed the qubit drop and the gate trim were two different levers in two
different entries.)

## Step 3 — Isolate the lever in each step

Within each adjacent diff, separate signal from noise:
- **Config/knob changes** — the changed parameter values (the usual lever).
- **Structural code changes** — a new function, a replaced primitive, a changed schedule.
- **Noise** — formatting, comments, re-baked defaults, regenerated artifacts.

Most steps reduce to **one** real lever. If a single submission genuinely changed several coupled
things, note that explicitly — but your prior should be "one lever per accepted step," and a diff
that looks like five levers is usually one real change plus re-baked noise (or you skipped an
intermediate — go back to Step 2).

## Step 4 — Re-measure the metrics yourself

For each step, build/run the artifact and record the metrics *independently*: the headline score
plus its sub-components. Two tricks recur:
- **Recover sub-metrics by exact arithmetic.** If the score is a product (e.g. `factor_A ×
  factor_B`) and you can measure one factor, the other often falls out as an exact integer
  division — a clean way to get a sub-metric the submission didn't report. If the division is
  *not* exact, your assumption about the formula or your measurement is wrong; stop and reconcile.
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
- **Transferable** — a knob value or a structural change (a fused stage, a denser encoding, a
  per-step schedule). These port to your own line directly.
- **Non-transferable search artifact** — a value that is only valid *because they searched for it
  against their exact configuration*: a hunted random seed/nonce, an island, a fitted constant, a
  data-order that happens to dodge a failure on their setup. Re-using their artifact on your
  (different) configuration will not reproduce the win and may silently break correctness. When a
  competitor's entry is "structural knob change + a re-hunted artifact," **only the knob transfers**
  — you must re-run the search for the artifact against your own config.

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
