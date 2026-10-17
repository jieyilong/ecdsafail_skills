# Anthropic divstep decoding: guarded transfer to Q850 work

## Evidence boundary

This reference extracts reusable mechanisms from Gu, Kemeny, Yelin, and Lukin,
*Discovering state-of-the-art quantum circuits with large language models*
(arXiv:2610.22367v1) and its released `andigu/uncompute` implementation.

It is a route-selection and experiment guide, not a completed ECDSA.Fail
optimization. Do not treat the paper's recurrence, thresholds, resource model,
or test result as source-compatible with another circuit without deriving the
mapping and rerunning that circuit's validator.

Primary sources:

- Paper: <https://arxiv.org/html/2610.22367v1>, especially SI II.1 and
  Appendix A, Theorem A.6.
- Repository: <https://github.com/andigu/uncompute>.
- Point-add task: <https://github.com/andigu/uncompute/tree/main/tasks/modinv-point-add>.
- Exact resource rows: <https://github.com/andigu/uncompute/blob/main/tasks/modinv-point-add/results.jsonl>.
- Grader: <https://github.com/andigu/uncompute/blob/main/tasks/modinv-point-add/grader.py>.
- Divsteps: <https://github.com/andigu/uncompute/tree/main/tasks/modinv-point-add/circuits/divsteps>.
- Lean proofs: <https://github.com/andigu/uncompute/tree/main/lean/divsteps>.

The release contains circuit sources, compressed streams, an evaluator and
reproduction instructions. Do not describe the work as lacking an implementation.
The checked receipts do not provide ECDSA.Fail's separate `cls/pha/anc` report.

## The exact branch-recovery theorem

Use the paper's notation only in this section. Let `f',g'` be updated integer
remainders, `f_v',g_v'` updated coefficients, and `z` the signed counter. For an
active ambiguous negative-counter nonswap, define

```text
j = v2(f_v')
q = f_v' / 2^j
b = bit_(j-1)(g_v' * q^-1 mod 2^j)
  = bit_(j-1)(p * (f' * q)^-1 mod 2^j).
```

Theorem A.6 establishes this identity on that recurrence's supported state.
Its proof uses the signed-counter branch, parity, determinant and finite-window
invariants. It does not establish the same formula for arbitrary GCD states,
pre/post-swap frames, coefficient scalings or truncated implementations.

Their implementation combines decoded decisions with stored decisions above a
depth threshold. Forward branch measurements are phase-corrected when reverse
execution recovers the branch. The useful general principle is narrower:

> Derive the Boolean result a consumer needs directly from preserved arithmetic
> state instead of materializing a larger intermediate solely to read that bit.

## Released complete-circuit context

Selected point-add rows from the released receipts:

| Circuit | Q | T |
|---|---:|---:|
| `divsteps/circuit.py` |935|4,006,673|
| `divsteps/j8.py` |897|5,331,729|
| `divsteps/j9.py` |893|7,866,779|
| `euclidean/circuit.py` |843|20,521,949|

These rows do not supply Q<=850 and T<5.6M. In particular, the 897→893 width
change spends roughly 2.5M additional Toffolis, so do not extrapolate a cheap
last 43-qubit reduction.

The paper reports four failed full-circuit tests out of 100,000 for each of two
highlighted point adders. The grader accepts at most 20 failed shots out of
100,000 and combines wrong output, wrong phase and dirty workspace into one
verdict. That evidence differs from an ECDSA.Fail 9,024-shot `0/0/0` packet,
a population error estimate and an all-input proof.

## Audit the receiving walk before transferring anything

For Lilypad-G, inspect the current implementations and active callers around:

- branch measurement and reverse regeneration;
- rho/frame derivation;
- selected low-page source-bit queries and full page codecs;
- eraser/stream-page consumers, cap logic and marker cleanup;
- endpoint receipts, fixed-tail completion and inverse restoration.

Typical names in the October 2026 research line include `walk_forward_g`,
`rec_regen_g`, `walk_inverse_g`, `rho_stable`, `page3_source_anf`,
`page3_general_anf`, `page3_sources_xor_direct_rho`,
`page3_source_bit_controlled_xor_direct_rho`, `page_codec_u_to_v`,
`page_codec_xor_v`, `eraser`, `eraser_with_views`, `stream_page`, `GTail` and
`fixed_tail_prefix`. Read the actual checked-out source; names are navigation
hints, not guarantees that a path is active.

A local low-page relation may look like

```text
V = (G*U + (-1)^rho*p) * F^-1 mod 2^r.
```

Do not identify its stored U/V, signs or coefficient scaling with the paper's
variables without deriving the coordinate transformation, including any
half-cofactor representation and whether the consumer sees pre- or post-swap
state.

Some existing consumers already decode only one or two selected bits. Adding
another generic selected-bit helper is not progress unless it replaces a more
expensive active producer-consumer-cleanup sequence.

## Ranked experiments

### 1. Consumer-specific predicate fusion

Start here.

1. Select one active eraser or marker consumer that currently recovers page
   bits and then computes a predicate.
2. Express the final predicate directly in preserved low bits, rho/frame and
   existing controls.
3. Synthesize that predicate as a small Boolean circuit.
4. Compare the entire old and new producer-consumer-cleanup sequences.

The old cost includes every page conversion, materialized bit, control, phase
repair and cleanup eliminated by the fused predicate. The new cost includes
predicate compute/use/erase, changed lifetimes and any extra control fanout.

### 2. Share nonlinear low-bit work

Look for common monomials or products across page recovery, branch/marker
decisions and inverse erasure. A retained witness needs a named producer,
exact value and frame, supported domain, all consumers, measurement outcome if
any, last use and phase-correct restoration. A local gate saving can lose if it
extends the witness through the peak.

Do not loan page/code lanes because a toy round trip restored them. They may
hold a rotated marker, be live to another consumer or be classically tied to a
measurement receipt.

### 3. Hybrid decode versus store

Anthropic's depth threshold motivates a receiving-walk experiment, not a
portable constant. Derive the cost and information boundary for that walk:

```text
decode cost(depth) versus retained-record width/lifetime(depth).
```

Counter clamping or compressed logs may discard information absent from the
proposed preserved state. Prove recoverability before deleting a record. Price
the transcript and decoder together at the actual peak and through reverse
cleanup.

### 4. Spend savings on completion repair

If a Q850 route has unfinished inputs at a static absorption cutoff, a local
decoder saving can buy the scratch or Toffoli budget needed for dynamic
completion. It does not itself provide the completion algorithm. Completed and
active paths need an exact reversible union with distinct mode, endpoint and
phase lifecycles.

## Mandatory proof and pricing obligations

- **Coordinate map:** derive the relation between recurrences, stored
  half-cofactors, signs, counter and branch predicates.
- **Invocation frame:** identify the exact pre/post-swap and pre/post-normalized
  physical view read by the new predicate.
- **Support:** state parity, active/completed mode, coefficient window and all
  finite-width promises.
- **Reversibility:** prove the target bit is determined by retained state and
  restore every borrowed lane bit-identically.
- **Phase:** track the branch measurement receipt and its actual correction.
  Correct basis values are insufficient.
- **Whole-sequence cost:** include compute, controlled uses, cleanup, view
  conversion, both directions and forward/inverse multiplicity.
- **Peak:** report simultaneous owners at the globally binding operation. A
  locally smaller decoder may leave Q unchanged.
- **Approximation:** do not remove rare cases by implication. State and measure
  any changed support or error envelope separately.

Applying a circuit's own adjoint proves neither the required forward function
nor clean scratch at the forward boundary. Independently specify forward values,
phase, outcomes and borrowed-state restoration.

## Known integration traps

- An exact isolated flag formula can fail when its physical source lane is
  aliased or rotated before the call.
- A mathematically correct determinant identity can read the wrong low window
  after a normalization/view conversion.
- A wider algebraic codec can cost far more than the physical-source inverse it
  replaces. Price the complete active sequence before promoting it.
- A branch-decoder improvement does not automatically remove endpoint lift,
  fixed-tail storage, cap-log dependencies or the terminal mode union.
- Operation-stream changes alter Fiat-Shamir-derived inputs. Compare variants
  on explicit matched inputs and logical measurement roles.

## Promotion gates

For each hypothesis preserve:

| Gate | Required evidence |
|---|---|
| Target | Exact active consumer sequence replaced |
| Contract | Inputs, frame, support, borrowed lanes and phase debt |
| Local | Independent value/scratch/phase checks over feasible outcomes |
| Cost | Complete old/new sequence T and simultaneous scratch |
| Integration | Reachable-state ticks, both directions, active/completed cases |
| Full circuit | Emitted Q/T, endpoint inverse and affine point addition |
| Population | Fresh matched `cls/pha/anc`, not only aggregate pass/fail |

Suggested order:

1. Exhaustive small-domain predicate differential with phase negatives.
2. Reachable states at the real producer/consumer boundary.
3. Forward values and scratch, then fresh inverse and measurement phase.
4. Full division endpoint and complete affine point addition.
5. Fresh population characterization.
6. Trusted source-bound 9,024-shot validation before any hunt or submission.

Stop when the complete cost exceeds the available budget without a quantified
matched removal, the change moves no co-binding peak, or its inputs cannot be
retained at the active call site. Preserve negative results rather than
repeatedly narrowing unproved support.

## First useful deliverable

Compare one existing streamed-page consumer against one fused-predicate
replacement. Return the formula and frame contract, independent value/scratch/
phase evidence, complete old/new T and peak support, and either a source-bound
integration result or a precise rejection. Do not report a Q850 breakthrough
from an isolated gadget count.
