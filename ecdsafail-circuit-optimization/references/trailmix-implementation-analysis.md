# TrailMix Implementation Analysis

Use this reference when the task mentions Trail of Bits, TrailMix, jump-GCD,
base-3/base-5 dialog compression, Proos-Zalka divstep, whole-register ghosting,
venting, or sub-1175-qubit EC point-addition routes.

## Source Snapshot

- GitHub: `https://github.com/trailofbits/trailmix`
- Local analyzed checkout: `/Users/jieyilong/Personal/research/ShorOptimization/shor_optimization_workspace/repos/trailmix`
- Analyzed commit: `cd961ff088243f4a49097867fb053b80675e0ad5`
- Commit subject: `release: version 1.0.0`
- Crate version: `trailmix 1.0.0`
- Primary source files:
  - `README.md`
  - `kmx_circuit_summaries.md`
  - `gen_and_validate_kmx.sh`
  - `trailmix/src/arith/schrottenloher/gcd_pack.rs`
  - `trailmix/src/arith/schrottenloher/gcd_jump.rs`
  - `trailmix/src/arith/schrottenloher/gcd_compress_jump.rs`
  - `trailmix/src/arith/gidney_const_adder.rs`
  - `trailmix/src/inversion/shrunken_pz_state_machine/mod.rs`
  - `trailmix/src/inversion/shrunken_pz_schedule.rs`

Refresh this reference after pulling a newer TrailMix commit. Prefer source files and
checked-in validation scripts over secondary summaries when the numbers disagree.

## Headline Routes

All five TrailMix circuits compute the same in-place affine secp256k1 `P += Q`
with `P` in quantum registers and `Q` as classical per-shot input. They differ
only in the modular inversion engine and the chosen qubit/Toffoli operating point.

| route | emit binary | qubits | Toffoli | role |
|---|---|---:|---:|---|
| low-qubit | `emit_test_ec_add_schrottenloher` | 1173 | ~2.48M | Schrottenloher dialog, M=5 base-3 tape, no apply vents |
| low-tof | `emit_test_ec_add_schrottenloher_lowtof` | 1416 | ~2.03M | Same dialog, M=3 tape, apply-BV venting |
| jump-lowqubit | `emit_test_ec_add_schrottenloher_jump` | 1169 | ~2.09M | Jump-GCD dialog, jump=2, base-5 tape |
| jump-lowtof | `emit_test_ec_add_schrottenloher_jump_lowtof` | 1412 | ~1.90M | Jump-GCD plus apply-BV venting |
| shrunken-PZ | `emit_test_ec_add_shrunken_pz` | 1050 | ~32.3M | Reversible Proos-Zalka divstep; qubit-floor witness |

Validation script caps in `gen_and_validate_kmx.sh`:

- low-qubit: `1175 q / 2,700,000 Toffoli / 15M ops`
- low-tof: `1420 q / 2,100,000 Toffoli / 15M ops`
- jump-lowqubit: `1175 q / 2,100,000 Toffoli / 13M ops`
- jump-lowtof: `1420 q / 1,950,000 Toffoli / 14M ops`
- shrunken-PZ: `1060 q / 50,000,000 Toffoli / 140M ops`

Read the headline correctly:

- The best score-relevant low-qubit route is **jump-lowqubit: 1169q / ~2.09M**.
- The absolute lowest-qubit route is **shrunken-PZ: 1050q / ~32.3M**, but it is
  not score-competitive under a qubits * Toffoli objective.

## Low-Qubit Schrottenloher Route: 1173q

TrailMix starts from Schrottenloher's dialog in-place modular multiply:

1. Forward GCD construction consumes `x` into a dialog transcript.
2. `apply_bv` reconstructs Bezout/modular state from the transcript.
3. Reverse GCD construction restores `x` and erases the transcript.

The low-qubit route changes the transcript packing:

- `gcd_pack.rs` sets `DIALOG_M = 5` and `DIALOG_PACK = 8`.
- Five `(b0, b0&b1)` pairs have only `3^5 = 243` valid states, so they fit in
  8 bits.
- This gives `8/5 = 1.600` bits per dialog pair, versus Schrottenloher's
  `5/3 = 1.667`.
- For `n=256`, the iteration count is rounded to 405, so the tape is
  `405 / 5 * 8 = 648` bits.

Peak owner:

- The peak is `apply_bv` / Bezout reconstruction, not GCD construction.
- The 648-bit tape co-resides with `x2` and `y2`.
- GCD construction runs below peak, so its controlled subtracts can use full
  Gidney-style vented adders without increasing peak.

Practical lesson:

- If a route is transcript-bound, radix-aware transcript compression is a real
  qubit lever.
- If a route is not transcript-bound, compression may only add encoder/decoder
  Toffoli with little peak benefit.

## Jump-GCD Route: 1169q

TrailMix's best competitive low-qubit route replaces the one-bit-at-a-time
binary-GCD dialog with a Stein-style jump-GCD:

- Standard dialog removes exactly one factor of two from `v` per step.
- Jump-GCD removes up to `jump=2` trailing zeros per step.
- Fewer steps means fewer GCD subtract/swap operations and fewer `apply_bv`
  modular updates.
- The register layout and peak owner remain basically the same as the
  Schrottenloher dialog route.

The per-step symbol is wider, so TrailMix changes the alphabet and packing:

- The jump-before-swap form has exactly five valid symbols for `jump=2`.
- Three symbols pack into seven bits because `5^3 = 125 < 2^7`.
- Raw symbol width would be 3 bits/step; packed width is about
  `7/3 = 2.333` bits/step.
- The base-5 packer uses a radix-5 accumulator and a QROM/ghost-clear path to
  clear displaced symbol bits.

Why it wins:

- The extra symbol width is more than paid back by the step-count reduction.
- The route reaches `1169q / ~2.09M`, under both Google-style reference axes
  (`1175q / 2.7M` and `1425q / 2.1M`).

Practical lesson:

- For ECDSA Fail, jump-GCD is the most promising TrailMix idea to consider
  porting or approximating.
- A direct port is not just a knob change: it changes the dialog alphabet,
  packing, reverse reconstruction, and validation envelope.
- Before island hunting a jump-style route, measure q/Toffoli and run short
  triage, because a different transcript schedule will almost certainly require
  a fresh nonce.

## Low-Toffoli Variants: 1416q and 1412q

The low-Toffoli variants spend peak qubits on measurement-vented adders in
`apply_bv`.

In `gidney_const_adder.rs`, a controlled hybrid adder has:

```text
Toffoli = 3n - 2 - vents
peak increase = vents
```

Interpretation:

- `vents = 0`: TTK/Cuccaro-like `3n` controlled adder.
- `vents = n - 1`: Gidney-like `2n` controlled adder.
- Each vent replaces one carry-uncompute Toffoli with measurement plus a phase
  correction.

TrailMix low-tof route:

- Uses `dialog_m = 3`, because the M=3 SAT-style compressor is cheaper than the
  M=5 radix encoder.
- Uses a shared apply-BV vent budget, including pseudo-Mersenne `+f` reductions.
- Lands around `1416q / ~2.03M`.

Jump-lowtof:

- Adds the same venting policy to jump-GCD.
- Lands around `1412q / ~1.90M`.

Practical lesson:

- Venting is an explicit score trade. It is useful when Toffoli dominates and
  qubit headroom exists.
- On a qubit-frontier route, venting the peak-binding phase may worsen score
  even if it improves raw Toffoli.

## Shrunken-PZ Route: 1050q

The `shrunken-PZ` route is a different inversion family, based on a reversible
Proos-Zalka divstep state machine.

Key implementation ideas:

- `SHRUNKEN_PZ_NSTEPS = 530`.
- Per-step register widths are precomputed by Monte Carlo and stored in
  `shrunken_pz_schedule.rs`.
- The checked-in schedule records a state-register peak:

```text
A + B + ca + cb + q = 741 at step 348
```

The route then minimizes coordinate passengers:

- In forward divide, it computes `lambda = dy / dx`.
- It ghosts `dy` during the reverse inversion so `dy` and `lambda` do not
  co-reside.
- In cancel direction, it ghosts `lambda` so only `new_dy` rides through the
  inversion.
- The divide peak is approximately `EEA peak + one 256-bit passenger`, not
  `EEA peak + two 256-bit passengers`.

The cost:

- About `1050q / ~32.3M Toffoli / ~100M ops`.
- It is a qubit-floor witness, not a good score route.

Practical lesson:

- Whole-register ghosting and passenger minimization can lower qubits by
  hundreds, but may explode Toffoli/depth.
- Use shrunken-PZ as an idea source: ghost or reconstruct one coordinate
  passenger, tear down constants at convergence, and pipeline quotient state.
- Do not copy it wholesale unless the objective heavily favors qubits over
  Toffoli.

## Transferable Design Patterns

Use these patterns when proposing new ECDSA Fail routes:

1. **Radix-aware transcript compression**
   - Binary dialog pairs are ternary symbols.
   - Jump dialogs can be base-5 symbols.
   - Compress invalid states out of the transcript rather than storing raw bits.

2. **Peak-owner accounting**
   - Identify whether peak is transcript, `apply_bv`, square-row state, coordinate
     passengers, carry slices, or decoded windows.
   - Shrinking non-owners does not help until it moves the actual peak.

3. **Jump-GCD before local carry notches**
   - TrailMix's strongest competitive improvement is changing the GCD schedule,
     not shaving another local carry bit.
   - If implementation time allows, prioritize a small jump-GCD prototype over
     increasingly risky carry/compare truncations.

4. **Spend vents only where headroom exists**
   - GCD construction often has free ancilla headroom because `apply_bv` binds
     peak.
   - Applying vents in the peak-binding phase is a deliberate q/Toffoli trade.

5. **Passenger minimization**
   - Avoid separate long-lived slope registers.
   - Let the slope live in an existing coordinate when possible.
   - Consider ghost/reconstruct only with explicit phase obligations and strong
     validation.

6. **Validation discipline**
   - TrailMix validates emitted `.kmx` circuits through a native simulator over
     thousands of Fiat-Shamir shots.
   - For ECDSA Fail, any equivalent structural change still needs exact CFG
     baking, q/Toffoli measurement, short candidate triage, and full fast/full
     validation of candidates before large island search.

## Source Map

Use this map when verifying or extending the analysis:

- Route table and headline claims: `README.md`, `kmx_circuit_summaries.md`
- Validation caps: `gen_and_validate_kmx.sh`
- M=5 transcript geometry: `trailmix/src/arith/schrottenloher/gcd_pack.rs`
- M=5 compressor: `trailmix/src/arith/schrottenloher/gcd_compress5.rs`
- Jump-GCD algebra: `trailmix/src/arith/schrottenloher/gcd_jump.rs`
- Jump symbol compressor: `trailmix/src/arith/schrottenloher/gcd_compress_jump.rs`
- Apply-BV and EC point-add drivers: `trailmix/src/arith/schrottenloher/pointadd.rs`
- Vented adder: `trailmix/src/arith/gidney_const_adder.rs`
- Pseudo-Mersenne reductions: `trailmix/src/arith/schrottenloher/pm_prims.rs`
- Shrunken-PZ state machine: `trailmix/src/inversion/shrunken_pz_state_machine/mod.rs`
- Shrunken-PZ schedule: `trailmix/src/inversion/shrunken_pz_schedule.rs`
- Verification/tooling overview: `trailmix/notes/OVERVIEW.md`
- Qubit/Toffoli exchange-rate note: `trailmix/notes/quantum_resource_metrics.md`

## Decision Guidance

When asked "what should we try next?", rank TrailMix-inspired ideas as:

1. **Most promising:** jump-GCD / compact jump transcript, if implementation budget
   allows a real structural route.
2. **Near-term:** M=5 or other radix-aware transcript packing if the current route
   is transcript/apply sidecar peak-bound.
3. **Conditional:** apply-BV venting when a route has qubit slack and needs Toffoli.
4. **Research-only unless objective changes:** shrunken-PZ style whole-register
   ghosting, because it proves low qubits but pays too much Toffoli.

Always score-gate before island search. A beautiful lower-qubit route is not useful
if estimated `qubits * Toffoli` loses to the current promoted SOTA or if early
candidate validation shows a uniform dirty fingerprint.
