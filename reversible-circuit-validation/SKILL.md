---
name: reversible-circuit-validation
description: >-
  Validate and debug the CORRECTNESS of a reversible or quantum circuit — not its size. Use
  this whenever a circuit "gives wrong answers on some inputs", "ancilla aren't returning to
  zero / uncomputation is leaving garbage", there are "phase errors", "it passes my basis-state
  test but I'm not sure it's right in superposition", or someone needs to test a reversible
  adder/multiplier/modular-arithmetic block before trusting it inside Shor's. Covers the
  classical/phase/ancilla (cls/pha/anc) three-channel decomposition, differential testing
  against a trusted reference on RANDOM inputs, the forward-inverse identity check, telling a
  designed approximation failure apart from a real bug, and localizing the first broken op.
  Fires on informal phrasing ("my uncompute is dirty", "results get corrupted when I compose
  it", "is 0.3% failure expected?"). For making a correct circuit SMALLER use peak-qubit-reduction
  (qubits) or toffoli-reduction (gates); this skill owns CORRECTNESS.
---

# Reversible Circuit Validation

A reversible/quantum circuit is correct only if it is correct in **three independent channels
at once** — and the trap that bites everyone is that the easiest test (feed a basis state,
check the output bits) only exercises *one* of them. The other two fail silently in the
computational basis and only bite once the circuit runs in superposition, which is exactly
where you can no longer see them by inspection.

## The three channels: cls / pha / anc

| Channel | What's wrong | How it hides | Why it's fatal |
|---|---|---|---|
| **cls** (classical) | the output *value* is wrong on some inputs | — (a basis-state test catches it) | wrong answer |
| **pha** (phase) | output value is right, but a spurious **relative phase** was stamped on the state | invisible to any value/output check | destroys the interference Shor/QPE depend on |
| **anc** (ancilla) | scratch qubits don't return to **\|0⟩** — they stay **entangled** with the data | output register still reads correct | the leftover entanglement decoheres the computation and breaks reversibility/uncompute |

The headline rule: **a value check is necessary but not sufficient.** A circuit can pass
"basis state in → correct bits out" on every input you try and still be broken in `pha` or
`anc`. Validation means checking all three — and tracking them *separately*, because they have
different causes and different fixes.

## The core loop

1. **Decide which channels you need.** Standalone classical use → `cls` may be enough. Anything
   run in superposition (Shor, QPE, amplitude estimation, or any circuit *composed* into a
   larger one) → you need all three. State this first.
2. **Differential-test** the circuit against a trusted reference, on **random** inputs (not just
   the structured/graded set).
3. **Decompose** every failure into `cls` / `pha` / `anc`.
4. **Classify** each failure: a *designed* approximation failure, or a real *bug*?
5. **Localize** real bugs to the first broken operation.
6. **Fix the smallest responsible mechanism, re-validate** — and re-check all three channels,
   since a fix in one can disturb another.

## Step 2 — Differential testing, on random inputs

Run the circuit and compare its output to a **trusted classical reference** that computes the
same function (e.g. compute `P+Q` classically and check the circuit's output register equals
it). Two disciplines matter:

- **Use random inputs, seeded for reproducibility — not only the structured/graded set.** A
  fixed or Fiat-Shamir-derived test set can systematically *dodge* an input-dependent bug; a
  bug that triggers on 0.2% of inputs may never appear in 24 hand-picked cases. Generate many
  random inputs, batch them, and report per-channel counts. (In practice: a few hundred catches
  gross bugs; ~10k surfaces rare input-dependent ones.)
- **Report `cls / pha / anc` per batch**, not a single pass/fail. You want to see *which*
  channel is dirty and how often — that immediately narrows the cause.

## Step 3 — How to actually measure each channel

- **anc** — after the circuit runs, every ancilla must be provably back to **\|0⟩**. Assert it
  (measure them, or check the statevector). Non-zero, or *entangled-but-happens-to-read-zero*,
  both count as dirty: cleanliness means **disentangled and \|0⟩**, not "value unused." The
  sharpest single test: run the circuit **forward then its exact inverse** (`U† U`) and confirm
  you recover the input state *exactly* — any ancilla left entangled makes `U†U ≠ I`.
- **pha** — a value check can't see relative phase, so test it directly: (a) the same
  **forward-inverse identity** `U†U = I` catches a stray phase (you won't return to the exact
  input state, including global/relative phase); or (b) run on a **superposition** input and
  check the output interferes as the reference unitary predicts; or (c) compare against the
  reference unitary on basis states *with phase tracked*, not just bit-values.
- **cls** — compare the output register to the classical reference value on each input.

The **forward-inverse identity (`U†U = I`)** is the highest-leverage single check: it exercises
`pha` and `anc` together and needs no superposition machinery — if the composed circuit doesn't
return every input exactly to itself, something is dirty. Make it your first reflex.

## Step 4 — Designed approximation failure vs. real bug

Many space-optimized circuits **deliberately** truncate carries, narrow compare windows, or
approximate a reduction — so they are *supposed* to be wrong on a small fraction of inputs
(the inputs where the dropped information mattered). Before chasing a "bug," decide whether a
failure is **designed-hard** or **unexpected**:

- Build (or reuse) a **classical model of the approximation** — e.g. a model of the GCD's
  width/convergence envelope — and run each failing input through it. If the model predicts
  failure (it overflowed the width, didn't converge in the budget, lost a needed body bit),
  the input is **designed-hard**: expected, not a bug.
- If the model says the input *should* have been clean but the circuit failed → **unexpected**:
  a real bug (or an approximation your model doesn't capture). Investigate.
- **Know your model's coverage.** A classical filter usually models *some* of the
  approximations, not all — e.g. it may capture GCD-width failures but not an apply-phase carry
  truncation. So an "unexpected-clean" failure can still be a *designed* truncation your model
  is blind to. Don't over-trust the filter; widen it, or localize (Step 5) to be sure.

For a circuit graded on a **fixed input set**, the endgame of this is a **clean island**: since
the designed-hard inputs are a tiny fraction, you search for a seed/parameter under which the
graded inputs all dodge the hard set, giving `0/0/0` on exactly that set. Validation's job is to
*confirm* `0/0/0` across all graded shots — and to keep the random-input failure rate at the
designed level, no higher.

## Step 5 — Localize a real bug to the first broken op

When a failure is unexpected, treat the circuit as a program under debugging and find the
*first* operation where an invariant breaks — don't eyeball the whole thing:

- **Bisect the op stream.** Run to op `K`, check an invariant (an intermediate value, or
  "ancilla X should still be \|0⟩ here"), and binary-search the first `K` where it breaks.
- **Per-section invariants / counters.** Carry/borrow width histograms, compare-decision
  agreement counts, "this scratch should be clean at this boundary" receipts.
- **Channel tells you where to look:** an `anc` failure points at a missing/incorrect
  *uncompute* (a compute with no matching reverse, or an aliased qubit reused before it was
  cleaned); a `pha` failure points at a measurement/phase-fixup that's wrong or a
  relative-phase gadget whose mirror didn't cancel; a `cls` failure points at the arithmetic
  itself (a truncation that went too far, a wrong control).

## Step 6 — Fix the smallest mechanism, re-validate all three channels

Patch the one responsible op (restore the missing uncompute, fix the phase fixup, widen the one
truncation), then **re-run the full cls/pha/anc validation** — not just the channel you fixed.
Repairs interact: restoring an uncompute can change timing that exposes a phase bug; a phase fix
can leave an ancilla dirty. The circuit is correct only when all three channels are clean on
random inputs at the designed failure rate.

## Guardrails (the "why")

- **Never ship on a value check alone.** `cls`-clean with dirty `pha`/`anc` is the most common
  silent failure — it works in your basis-state test and corrupts the moment it's used coherently.
- **Random inputs expose what structured inputs hide.** If you only ever test the graded/derived
  set, a bug can hide in the gap; random differential testing is the cheapest way to find it.
- **Clean ≠ value-unused.** An ancilla can hold the "right" value and still be entangled — that's
  an `anc` failure. Demand provable \|0⟩ and disentanglement (the `U†U=I` test proves it).
- **Don't over-trust your approximation model.** "Unexpected-clean" failures may be designed
  truncations the model doesn't cover; confirm by localizing rather than assuming a bug.

## Worked example (this lineage, for grounding)

Validating a space-optimized reversible point-add (output `P+Q`): generate 10,000 **random,
non-graded** inputs (seeded), run each through the circuit, compare to the classical `P+Q`, and
report `cls/pha/anc` per batch. Result pattern: **`anc` always 0** (the circuit is structurally
clean — every scratch uncomputes), and the only `cls` failures were ~0.16% of inputs that hit
the **designed** carry/width truncation. Each failure was run through the classical GCD filter
and classified: `NonConvergence` / `WidthOverflow` / `BodyTrimMismatch` → **designed-hard**;
a residue the filter didn't model (an apply-phase truncation) showed up as **unexpected-clean**
— a reminder that the filter's coverage is partial. The graded 9024-shot set, on its hunted
island, validated `0/0/0`. The whole exercise is Steps 2-4 of this loop.

## Relationship to the other skills

This skill is the **correctness** counterpart to the two optimization skills: every qubit you
free with `peak-qubit-reduction` and every gate you cut with `toffoli-reduction` is exactly the
kind of change that risks a `pha`/`anc` regression (a freed-too-early ancilla, a measurement
whose phase fixup is wrong, a skipped cleanup that wasn't redundant). Run this validation loop
after any such change. For the domain-specific filter, the GPU island search that finds a clean
nonce, and the exact graded-shot harness of the ECDSA-fail circuit, see the companion
**ecdsafail-island-hunting** and **ecdsafail-circuit-optimization** skills.
