---
name: ecdsafail-circuit-optimization
description: >-
  Design and assess reversible secp256k1 point-addition optimizations for ECDSA.Fail.
  Use for qubit, Toffoli, product-score, or Pareto improvements; source-bound gate rewrites;
  GCD architecture comparisons; carry/history/payload scheduling; and choosing a viable
  circuit before island hunting. Distinguish measured results, local proof obligations,
  approximations, and validation limits.
---

# ECDSA.Fail Circuit Optimization

Design candidate changes against the active source and requested objective, then establish
their resource cost and validation obligations before spending search compute.

## Current evidence and route selection

Read [the October refresh](references/frontier-refresh-2026-10-06.md) for the current
product point, structural mechanisms, proof boundaries, and complete submission audit.
The pinned current point is Skywalk Q=1171, rounded T=946021, S=1107790591.
Refresh the official inventory before a new campaign. A product rejection can still
be a clean qubit/Toffoli Pareto improvement.

The detailed June catalogue is preserved as
[historical reference](references/legacy-playbook-2026-06.md), including TrailMix/Dialog
and Shrunken-PZ recipes, literature comparisons, and failed experiments.
Its dated SOTA numbers, default knobs, and empirical impossibility claims are not
current constraints. Choose the source family before applying any legacy knob.

## Establish the actual circuit

1. Pin the SHA, actual parent, and architectural predecessor. Separate inherited source
   snapshots from the new lever by inspecting both parent and lineage comparisons.
2. Follow the active dispatcher, emitter, and effective recipe. Check default precedence,
   environment clearing, compiled tables, and disabled helpers. Names such as “inert,”
   “exact,” or “skip” do not establish the called implementation's behavior.
3. Record the point-add interface, integer walk, field payloads, transcript representation,
   forward/reverse legs, cleanup, and support promised to each optimized gadget.
4. Measure Q, emitted CCX/CCZ, raw and rounded mean executed T, and every phase/live-set
   that binds Q. Count-only or component measurements remain estimates until the
   official emitter/evaluator reproduce the entire submitted circuit.

## Gate the requested objective

The official score is `S = Q * round(mean executed Toffoli)`. Preserve the raw mean.
For incumbent integer score S0 and proposed width Q, strict improvement requires
rounded `T <= (S0 - 1) // Q`:

Run this from the skill directory, or use the resolved path to its script:

```bash
python scripts/score_gate.py --best-score 1107975918 --qubits 1172 --rounded-toffoli 945335
```

These numbers reproduce the preceding October Q1172 width win's gate and 43298 score margin.
Fetch current values for a new candidate. Compare the product and the nondominated
resource set. Track depth/reaction cost separately for fault-tolerant runtime claims.

## Structural levers and obligations

- **Change the walk or frame.** Compare convergence, routing, field-update cost, and
  history occupancy together. A shorter walk with more history per step can win.
  An isolated GCD count omits the point-add payload and cleanup interface.
- **Move every co-binding peak.** Relocate passengers, borrow restored dirty support,
  schedule widths locally, release terminal registers, or rebuild them when needed.
  A local width cut can expose another binder and leave global Q unchanged.
- **Share a nonlinear witness.** Reuse a carry/product already computed elsewhere.
  Bind its producer, promised value, support, consumers, and restoration. Retain a
  measurement outcome until its inverse predicate is available for phase repair.
  The October pair codec has a checked local nine-state algebra; that does not
  prove its full-emitter support, lifetime, or point-add correctness.
- **Replace proven local operations.** Apply from-zero adders, affine/linear rewrites,
  algebraic fusion, conditional replay, or commutation/cancellation with explicit
  preconditions. Distinguish unrestricted proofs, promised-support proofs, bounded
  symbolic checks, and empirical validation.
- **Bind certificates to source.** Ordinal and tuple-occurrence tables depend on the
  full recipe, round count, schedule, relevant state, and operation identity.
  Retire or reprove them when dependencies change. Matching the gate tuple alone
  does not establish the semantic precondition.
- **Account for approximation.** Endpoint truncation, narrow carry/compare windows,
  and fewer rounds can change error probability. A no-fire census, equal coarse
  failure counts, and one clean packet do not prove zero added error.

## Diagnose, repair, then search

Freeze the route and reproduce the failure. Trace convergence/width/compare
disagreements, first-broken sections, scratch lifetime, and phase debt. Repair the
smallest mechanism, remeasure Q/T, and use matched-input diagnostics before a short
search pilot. Stop repeating knobs when the peak is allocation-bound.

Use distinct hypotheses when the mechanism is uncertain. Record failed repairs,
their source/gates, diagnostic results, and cumulative cost. A finite sample with
no clean candidate is a reason to inspect the tail or invariant, not a proof of
an impossible island.

## Validation and handoff

Use `reversible-circuit-validation` for independent value, relative-phase, and
forward-scratch checks; use `ecdsafail-island-hunting` for architecture-specific
screens and official packets. Applying a circuit's own exact adjoint does not
establish its forward specification.

Changing the operation stream changes Fiat–Shamir inputs even at the same tail
nonce. Use explicit matched inputs for differential claims. Bind GPU prescreens
to the active architecture and control them against the trusted native evaluator.
Partial phase debt can cancel later; only a proven prefix obstruction supports
a sound early rejection.

Handoff: exact source/recipe/table identity, Q/T/score basis, peak owner, proof or
empirical evidence, fresh-packet error statistics, prescreen agreement, official
clean packet result, and the reproducible next experiment. An optimization request
does not authorize unrelated fleet, platform, or account changes.
