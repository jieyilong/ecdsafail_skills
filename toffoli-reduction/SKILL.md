---
name: toffoli-reduction
description: >-
  Reduce non-Clifford gate cost in reversible or quantum circuits. Use for Toffoli/T-count
  bottlenecks, carry or predicate uncompute, algebraic fusion, witness sharing, source-bound
  rewrites, or the gate factor of a qubits-times-Toffoli objective. Measure the actual charged
  metric, preserve value/phase/scratch interfaces, and distinguish proof from sampled support.
---

# Toffoli Reduction

Find the charged hot spot, identify its mathematical role, and reduce that cost under
the circuit's actual input/support and cleanup interface.

## Current examples and historical catalogue

For ECDSA.Fail read [the October evidence](references/frontier-refresh-2026-10-06.md)
and the relevant tranche reference. It covers the newer GCD/payload families, Q834
predicate/shared-product work, Q792 metadata/permutation work, and source-proof limits.
The [detailed June catalogue](references/legacy-playbook-2026-06.md) preserves older
recipes and examples. Its dated “current” records, quantum-fire pricing, and generalized
zero-cost predicate claims are historical material, not canonical instructions.

## Measure the actual cost

Distinguish emitted CCX/CCZ, charged executed Toffoli, physical width, operation count,
and non-Clifford depth. A benchmark product does not by itself predict hardware runtime.
Use the target hardware/evaluator cost model for Clifford, measurement and reaction costs.

In ECDSA.Fail, executed cost uses the active **classical condition mask**, not whether
the quantum controls happen to be one in a sampled basis state. A quantum no-fire gate
can still be charged. Removing it requires an operator/support argument or an explicitly
empirical approximation, then source-bound validation. Source changes also change the
Fiat–Shamir input corpus, so a nonce-only lower average is not a gate-construction win.

Trace phase/operation contributions and follow the active emitter. Verify that a helper,
recipe override, or compiled table is actually used. Count-only and component outputs
are estimates until the complete official operation stream/evaluator confirms them.

## Choose a matching mechanism

- **Exact AND/carry uncompute:** if a target holds the known product a*b and the factors
  remain available, X-basis measurement/reset plus outcome-conditioned CZ(a,b) clears
  it with the correct phase. This specific phase function is quadratic and needs no
  charged Toffoli in the benchmark. Prove the target/value and alias/lifetime premises.
- **Whole predicate uncompute:** a target holding f(inputs) can be measured and repaired
  by a conditional phase oracle for f. That oracle may require non-Clifford gates.
  A wide comparator is not a free CZ. Price the complete carry compute/uncompute and
  classical branches. Q834's phase comparator replaces only its output CCX by CZ.
- **Carry/sum witness sharing:** compute a nonlinear product once for multiple outputs,
  retain it across a justified interval, and repair measurement phase against that
  actual product. Dirty entry, factor mutation, physical aliasing, and outgoing
  classical-bit state are separate obligations.
- **Fusion/cancellation:** telescope modular add/negate chains, share boundary work,
  or cancel inverse pairs only when the intervening operations commute on the complete
  quantum and classical-condition interface. Guard classical BitStore/BitInvert effects.
- **From-zero/constant-support specialization:** use a proved zero operand, clean lane,
  odd low bit, terminal endpoint or selected control, not merely a finite census.
  An ordinary Cuccaro MAJ already costs one CCX; a three-to-two majority identity
  applies to a different three-AND formula, not any helper named “majority.”
- **Predicate phase factorization:** express a supported phase polynomial in simpler
  gates when the algebra permits it. Clifford corrections are free only in the stated
  metric. Higher-degree terms or predicate reconstruction can require charged gates.
- **Source-bound gate replacement:** attach a complete recipe, schedule, round count,
  support premise, operation identity and proof scope to ordinal/tuple/span tables.
  Matching the tuple does not prove the semantic relation after a layout change.
- **Small-map synthesis:** optimize exact chart/permutation completion, combine compatible
  transpositions, or use an exhaustively checked local cube schedule. Pay physical
  mux/adapter/lender costs and preserve the complete off-domain bijection.
- **Avoid materialization:** stream contributions, preserve a needed ratio/witness instead
  of building a disposable output, or schedule narrower work per iteration. Price cleanup
  and every co-binding peak, not an isolated arithmetic block.

## Price width and depth honestly

At Q,T, adding dQ peak qubits must save more than `T*dQ/(Q+dQ)` gates for a strict
product win. The small-change estimate is T/Q saved gates per added qubit. Off-peak
headroom has no Q charge only while the measured global maximum remains unchanged.
For a final ECDSA.Fail decision, use official rounded T and a strict integer score gate.

Depth/reaction penalties can make a count win unattractive on a real machine.
Measurement-assisted transformations change feed-forward and classical storage too.
State those costs rather than calling every measured rewrite depth-neutral or free.

## Verify before transferring or searching

Prove the local relation and its active-emitter support/lifetime, or state empirical
limits explicitly. A no-fire census, equal coarse failure counts, or one clean packet
does not establish zero added error. Check phase as well as output values and scratch
at the forward boundary; a circuit followed by its own exact adjoint is insufficient.

Use explicit matched inputs for differential claims. Couple surviving measurement
events by logical role, or compare the induced channels when their structure changes.
A removed measurement can change an outgoing classical bit even if qubits and phase
match; include overwrite-before-read closure if that bit is allowed to differ.

For a benchmark packet, rebuild the exact submitted source and full stream, then run
the complete trusted evaluator. Preserve local tests, source counts, expected cost,
official rounded metrics, source-bound certificates, and approximation/error estimates
as separate evidence. Reprice the same mechanism on a new architecture or peak owner.
