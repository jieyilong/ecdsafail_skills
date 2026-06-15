---
name: toffoli-reduction
description: >-
  Reduce the Toffoli / T-gate / non-Clifford count of a reversible or quantum circuit — the
  expensive, magic-state-bound resource that dominates error-corrected runtime. Use this
  whenever someone wants to "cut the T-count", "lower the Toffoli count", "reduce non-Clifford
  gates", "need fewer magic states", "my carry uncomputation is half my gates", or improve the
  gate factor of a qubits×Toffoli score. Covers venting carry-uncompute into measurement+phase
  fixups, conditional/measured replay so gates only execute on the branch that needs them,
  fused adders/folds, cross-block algebraic fusion of modular add/negate chains, ancilla-free
  majority, skipping provably-redundant cleanup, and avoiding full materialization. Fires on
  informal phrasing ("too many Toffolis", "T-count is my
  bottleneck", "can I make this uncompute free") and distinguishes emitted vs average-executed
  gate counts. For lowering the QUBIT/width count instead, use peak-qubit-reduction; this skill
  owns the GATE axis.
---

# Toffoli Reduction

On error-corrected hardware almost all cost is the **non-Clifford gates** — Toffoli (CCX) and
the T gates they decompose into — because each one consumes a distilled magic state. Cliffords
and measurements are nearly free by comparison. So in a `qubits × Toffoli` objective, this
skill owns the second factor, and on a fault-tolerant runtime estimate the Toffoli/T-count *is*
the headline number. It is the dual of `peak-qubit-reduction` (which owns the width factor);
the two trade against each other, and the exchange-rate section below is how you arbitrate.

Two facts shape every move here:

- **Cliffords and measurements are free; only the non-Clifford gates cost.** So the winning
  rewrites *convert* Toffoli/T work into measurement + Clifford (phase) corrections, or make it
  *not execute*, rather than just shuffling it around.
- **The trap is Toffoli-DEPTH, not Toffoli-COUNT.** The reciprocal "trade qubits for gates"
  rule holds only if a rewrite is **depth-neutral**. Recompute/uncompute and fewer-ancilla
  tricks inflate the non-Clifford *depth*, and at the magic-state reaction floor that depth is
  **not refundable** — a count win that triples depth can be a real-hardware loss the score
  doesn't see. Prefer depth-neutral moves; treat a depth blowup as a real cost.

## Emitted vs average-executed — know which your metric counts

Before optimizing, find out whether your objective counts **emitted** Toffoli (every CCX in the
circuit) or **average-executed** Toffoli (CCX weighted by how often its control condition
actually fires, averaged over inputs). They reward different moves:

- **Emitted** → only *structural* cuts help: fewer CCX in the circuit (fusion, MAJ, vents,
  skipped cleanup, less materialization).
- **Average-executed** → *also* rewards **conditional replay**: wrapping a block under a
  measurable predicate so its gates only count on the fraction of inputs where the predicate
  fires. A block that's emitted once but executes on 5% of inputs costs ~0.05× its Toffoli.

This distinction decides which half of the move-set is even available. State it explicitly at
the start.

## The core loop

Mirrors the width loop, but the resource is gates, not wires.

1. **Measure** — get the Toffoli/T count and find the **hot-spot**: which phase/operation emits (or executes) the most non-Clifford gates. Note emitted-vs-executed.
2. **Classify** the hot-spot's Toffoli by *kind* (table below) — the kind dictates the move.
3. **Pick the move** that fits that kind.
4. **Cost it** — depth-neutral? qubit cost? correctness risk? worth it at the exchange rate?
5. **Re-measure** — the hot-spot moves; repeat until it's an irreducible floor.

## Step 2 — Classify the hot-spot's gates

| Kind of Toffoli at the hot-spot | The move that fits |
|---|---|
| **Carry-uncompute** (reverse carry chain returning scratch to \|0⟩) | **Vent** it — replace each with a measurement + Clifford phase fixup (T-count 0) |
| **Recomputed self-uncomputing scratch** (comparators built then cleanly reversed) | **Conditional replay** under a measurable predicate (executed-metric only) |
| **Data-controlled arithmetic** (cadd, fold-sub controlled on live data) | *Not* conditionable — attack via fusion / materialization instead |
| **Majority / MAJ gadgets** (3-CCX majority) | **Ancilla-free majority** (2-CCX) — peak-neutral count cut |
| **Redundant final cleanup** (a top-clean made unnecessary by the folded structure) | **Skip it** — but only if provably redundant |
| **Full intermediate products / wide rows** | **Avoid materialization** — short/streamed/segmented forms emit fewer gates |
| **Repeated algebraic stages** (back-to-back add/negate/subtract chains, or stages with separate carry chains) | **Fuse** into one equivalent modular operation or shared carry chain (value-identical) |

## Step 3 — The moves

### Venting: turn carry-uncompute into a measurement (the exact, depth-neutral primitive)

A hybrid controlled adder costs `Toffoli = 3n − 2 − vents`. Each **vent** replaces one
carry-*uncompute* Toffoli with an **X-basis measurement + a `CZ` phase fixup** (T-count 0). So
each vent is exactly **−1 Toffoli, +1 qubit** — and the extra qubit is held *only* between the
forward and reverse carry chains, a short window. It is the cleanest, sim-verified, essentially
depth-neutral Toffoli dial there is.

The dial has a rule: **vent OFF-peak phases for free.** Where ancilla headroom exists (the phase
is not the qubit binder), every vent is pure Toffoli savings at no score cost. On the
peak-binding phase, the +1 qubit raises width and costs you on the other factor — so don't vent
there unless the gate win beats the qubit loss at your exchange rate. This is the single most
reliable count reducer when you have off-peak headroom.

### Conditional / measured replay (average-executed metric only)

If the metric counts executed gates, wrap a block under `push_condition(measurable predicate)`
so its CCX only count on inputs where the predicate is set. The score charges
`popcount(condition)` per CCX, so a predicate that is 0 on most inputs makes the block nearly
free on average.

**The hard-won constraint:** replay only works on **recomputed, self-uncomputing scratch** — a
comparator you build, read under the condition, and cleanly reverse (e.g. compute-condition →
phase-conditioned recompute). It does **not** work on:
- **data-controlled ops** (a `cadd`/fold-sub whose control is live data, not a measurable
  scratch bit) — the metric counts the push_condition mask, not the data controls, so wrapping
  these changes nothing, and
- **live-qubit predicates** that get reused downstream (you can't measure-and-discard them).
Mis-applying replay here is the classic over-optimistic estimate — verify the predicate is a
measurable, recomputed scratch bit before counting the savings.

### Fused folds and fast-adds

Fusing adjacent stages removes redundant controls, duplicated cleanup, and repeated carry work.
Examples that paid off: fusing `mod_double + cmod_double` into a single shared carry chain
(value-identical); turning coherent small adders into measured-fast form. These are usually the
first thing to try when you have a little qubit slack — low risk, real count savings.

### Cross-block algebraic fusion: collapse add/negate chains

Look for adjacent modular-arithmetic stages that are separated in the program because they
belong to different semantic phases, but algebraically telescope when composed. If the
intermediate value is not externally observed and the next phase immediately transforms it
again, replace the whole chain with one equivalent modular operation.

ECDSA Fail example (`DIALOG_FUSE_C_FORM`, `DIALOG_FUSE_X_RESTORE`):
- Square tail + c-form originally does
  `tx += 2*Qx; tx = -tx; tx -= Qx; tx = -tx`.
  The two negations cancel and the constants combine, so this is exactly `tx += 3*Qx`.
- x-restore originally does `tx = -tx; tx += Qx`.
  This is exactly `tx = Qx - tx`.

This reduces Toffoli because each removed modular negate/add/subtract avoids a carry chain,
reduction fold, and cleanup. It is not a truncation or approximation; it is an exact identity
over the modulus.

Checklist before trusting a fusion:
1. Prove the algebra in modular form, including underflow/overflow reduction behavior.
2. Confirm the intermediate value is not used as a control, measured, or needed by a later
   uncompute before the fused replacement.
3. Implement the fused primitive behind a default-off knob and verify knob-off is byte-identical.
4. Add or run component selftests for value, phase, and ancilla cleanliness.
5. Re-measure both q and average-executed Toffoli. A fusion should usually be peak-neutral,
   but the new primitive can briefly allocate different scratch.
6. If the op stream changes, assume the old Fiat-Shamir nonce is stale. Re-hunt or revalidate
   clean islands; algebraic exactness does not preserve the old transcript seed.

Treat fusion as a high-quality first move on the Toffoli axis: depth-neutral, peak-neutral
when scratch fits, and stackable with width/slope/truncation routes. Do not combine it with
risky truncation and then blame Fusion for density collapse; isolate Fusion-only density first.

### Ancilla-free majority

Replace a 3-CCX majority with a 2-CCX ancilla-free majority (and its per-position variants).
Peak-neutral, value-identical, pure count reduction wherever majorities appear in carry logic.

### Skip provably-redundant cleanup

A folded structure sometimes makes a final top-clean pass unnecessary. Dropping it removes its
Toffoli — but **only if it is genuinely redundant.** If it isn't, you get silent phase/classical
dirt. Pair this with strong correctness validation; it's the highest-risk move here.

### Avoid full materialization

Don't build a full-width intermediate when a window, the top bits, or a streamed/folded
contribution suffices. Short product paths, segmented rows, and truncated/streamed forms emit
fewer gates *and* fewer cleanup gates — a shared win with `peak-qubit-reduction`.

### Off-peak loosening (the dual move)

Once a phase falls off the qubit peak, you can *loosen* its width to buy Toffoli back for free
(a real SOTA did exactly this: it widened a segment knob once that phase was no longer the
binder, recovering gates at zero qubit cost). The general rule: **shrinking an off-peak phase
is a pure-Toffoli play**, and **widening an off-peak phase is a free Toffoli refund** — judge
both on gates alone.

### Per-step scheduling

When a block runs in a loop, a single constant width/precision must be set for the worst
iteration, emitting cleanup/carry gates the easy iterations don't need. A per-step schedule
`width(step)` trims the gate work to each step's tolerance. (Same lever as in
`peak-qubit-reduction`, here aimed at gates.)

## Step 4 — Cost the move

- **Depth first.** Is the rewrite non-Clifford-depth-neutral? Vents and fusion roughly are;
  recompute-heavy replay and aggressive uncompute may not be. A count win that inflates the
  reaction-floor depth can lose on real hardware even though the score improves — call that out.
- **Exchange rate.** Vents and some replays spend qubits to save gates. Compute break-even =
  (qubits added) ÷ (gates saved) against your qubit budget; off-peak the qubit is free, on-peak
  it isn't. If your score is `qubits × Toffoli`, a rough break-even is `qubits_total /
  Toffoli_total` gates-per-qubit.
- **Correctness.** Every move must be value-identical and phase-clean. The dangerous ones are
  measured uncompute / vents (phase fixup must be exact), skipped cleanup (must be truly
  redundant), and mis-scoped conditional replay. Validate with a `cls / pha / anc`
  (classical / phase / ancilla) error decomposition, not just an output-value check —
  measurement-based moves fail in *phase*, which value checks miss.

## Step 5 — Re-measure and repeat

Re-count after each change; the Toffoli hot-spot migrates just like the qubit binder does.
Stop when the hot-spot is irreducible (the genuine arithmetic the result depends on) or the
next move costs more qubits/depth than the exchange rate allows. **Re-measure BOTH factors** —
a gate win that quietly raised the peak (a vent on the wrong phase) may be a net score loss.

## Relationship to peak-qubit-reduction

These two skills are duals over the same `qubits × Toffoli` objective and constantly trade:
venting and conditional replay spend qubits to save gates; the width skill's uncompute holes
spend gates to save qubits. Use the exchange rate to decide direction, and after *any* change
re-measure **both** the peak qubits and the Toffoli count — the score is the product, and it's
easy to win one factor while quietly losing more on the other.

## Worked example (this lineage, for grounding)

A reversible point-add scored `peak_qubits × avg_executed_Toffoli`:
- `DIALOG_GCD_FOLD_MAJ1/MAJ2` (ancilla-free majority) and a fused double-y shared carry chain —
  structural count cuts, peak-neutral.
- `ROUND84_FOLD_FAST_ADD=0` flipped small Solinas-fold adders from coherent to measured-fast:
  **−1,434 executed Toffoli, peak-neutral** (a textbook measured-uncompute win).
- `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS` 21→19 once the square was off the qubit peak: **−442
  avg-Toffoli at 0 qubits** — a pure-Toffoli play on a now-off-peak phase.
- Conversely the 1192→1185 step *spent* +6,604 avg-Toffoli to buy −7 qubits — the dual
  direction, justified only because it cleared the exchange rate.

Note how each move is matched to the *kind* of gate at the hot-spot, and how the off-peak/
on-peak status of a phase decides whether a gate cut is free or costs width.

## Domain specifics

This is the domain-agnostic method. For the concrete knob names, the executed-Toffoli metric
mechanics, and the validated exchange-rate numbers of the ECDSA-fail / quantum-ECC
point-addition circuit, use the companion **ecdsafail-circuit-optimization** skill.
