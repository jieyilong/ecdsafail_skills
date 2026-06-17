# Handoff: 4352cfb q980 TrailMix Toffoli Cut

## Executive Summary

Submission `4352cfb` keeps the TrailMix shrunken-PZ qubit count at 980, but cuts average Toffoli
substantially versus `85d5dae`:

```text
submission          4352cfbc-1d26-4dda-98e5-460e97cb5fa0
author              welttowelt
source commit       32bd56898f9d5494a4922642711395e47c910f2d
reset base          1caf521514708003e5cfe5313fa0730a18291008
local trusted q     980
avg Toffoli         28,847,321
emitted ops         92,105,748
validation          9024 shots, 0/0/0
score               28,270,374,580
```

Compared with `85d5dae`:

```text
85d5dae: q=980, avgT=39,648,420, emitted_ops=110,865,075
4352cfb: q=980, avgT=28,847,321, emitted_ops= 92,105,748
delta:           -10,801,099 avgT,       -18,759,327 emitted ops
```

The core Toffoli reduction is an elliptic-curve dataflow rewrite named in the note as
`zero-dy/newdx`. It avoids constructing and then cleaning the old `new_y` path before lambda
cancellation. Instead it zeroes `dy`, reuses that register as scratch, and directly builds the
alternate-witness numerator:

```text
new_dy = lambda * new_dx
```

That lets the circuit cancel `lambda` without first materializing:

```text
new_y = dy + lambda * (tx_orig - new_x) - oy
```

## High-Level Quantum Intuition

The older q980 route computes the affine output `new_y` early, then converts it back into
`new_dy = new_y + oy` so the alternate inversion can cancel `lambda`. That is reversible and
low-qubit, but gate-expensive: it builds an intermediate `dx_diff`, multiplies by `lambda`,
subtracts/adds constants, then uncomputes `dx_diff`.

The 4352cfb route notices that the alternate cancellation does not actually need `new_y` yet. It
only needs the ratio:

```text
lambda = new_dy / new_dx
```

But by the curve equation,

```text
new_dy = lambda * new_dx
```

So it can:

1. preserve `lambda` and `dx`;
2. erase `dy` using the already-known identity `dy = lambda * dx`;
3. reuse the now-zero `dy` register as a 257-bit quantum scratch pad;
4. compute `new_x`;
5. compute `new_dx = ox - new_x`;
6. compute `new_dy = lambda * new_dx`;
7. cancel `lambda` using `new_dy/new_dx`;
8. only after cancellation, materialize the final output `new_y = new_dy - oy`.

In quantum-computing terms, this is a live-range and arithmetic-DAG rewrite. It does not lower the
peak because the inversion bitlength phases still bind at 980q, but it deletes a large reversible
detour in the non-peak EC arithmetic. The trick is powerful because a whole modular multiply/add
path disappears without adding a new long-lived register.

## Source-Level Changes

Canonical inspection repo:

```text
/private/tmp/ecdsafail-4352cfb-canonical-default
```

Only three point-add files differ materially from `85d5dae`:

```text
src/point_add/trailmix_port/mod.rs
src/point_add/trailmix_port/ec/point_add.rs
src/point_add/trailmix_port/inversion/shrunken_pz_schedule.rs
```

### Defaults

In `trailmix_port/mod.rs`, the q980 settings become:

```text
TRAILMIX_THIN_SCHEDULE=1
TRAILMIX_THIN_SEED=278
TRAILMIX_THIN_CLZ_WINDOW=78
TRAILMIX_THIN_MARGIN=0
TRAILMIX_THIN_VALIDATE=500000
TRAILMIX_COUNTER_W=8
TRAILMIX_Q_CAP=20
TRAILMIX_SROT_W=5
TRAILMIX_DEFER_Y_MATERIALIZE=1
TRAILMIX_ZERO_DY_NEWDX_ROUTE=1
TRAILMIX_TAIL_NONCE=25
```

Line anchor from pulled repo:

```text
/private/tmp/ecdsafail-4352cfb-canonical-default/src/point_add/trailmix_port/mod.rs:256
```

### Main EC dataflow rewrite

The key branch is in:

```text
/private/tmp/ecdsafail-4352cfb-canonical-default/src/point_add/trailmix_port/ec/point_add.rs:242
```

The new route:

```rust
// dy = lambda * dx. Zero it, then reuse ty as a qload scratch until
// new_dy = lambda * new_dx is needed for the alt-witness cleanup.
mod_mul_rfold_mbu_undo(circ, &ty[..], &lambda, &tx[..]);

mod_sub_from_creg_scratch_qload_w(circ, &tx[..], ox, &ty[..]); // tx := tx_orig
mod_neg_inplace_w(circ, &tx[..]);
mod_mac_inplace(circ, &tx[..], &lambda, &lambda);
mod_sub_creg_scratch_qload_w(circ, &tx[..], ox, &ty[..]);      // tx := new_x

mod_sub_from_creg_scratch_qload_w(circ, &tx[..], ox, &ty[..]); // tx := new_dx
mod_mac_inplace(circ, &ty[..], &lambda, &tx[..]);              // ty := new_dy
```

The old route, still present under the disabled branch, did:

```text
tx := tx_orig
tx := new_x
tx := dx_diff = tx_orig - new_x
ty := new_y = dy + lambda * dx_diff - oy
tx := new_x again
ty := new_dy = new_y + oy
tx := new_dx = ox - new_x
```

The new route skips the expensive `dx_diff` build/clean and the early `new_y` materialization.

### Reusing zeroed `dy` as qload scratch

The route adds scratch constant-load helpers around:

```text
/private/tmp/ecdsafail-4352cfb-canonical-default/src/point_add/trailmix_port/ec/point_add.rs:479
```

These load a classical constant into the zeroed `ty` register, use the ordinary q-q modular add/sub
machinery, and then unload the same constant:

```text
load_creg_into_scratch
mod_add_creg_scratch_qload_w
mod_sub_creg_scratch_qload_w
mod_sub_from_creg_scratch_qload_w
```

This is a gate-count win because it avoids the older direct classical-register constant path in
places where `ty` is already known zero and has enough headroom to serve as temporary qload storage.

### Schedule support tweak

`shrunken_pz_schedule.rs` folds `TRAILMIX_Q_CAP` into the thin-schedule repair check:

```text
/private/tmp/ecdsafail-4352cfb-canonical-default/src/point_add/trailmix_port/inversion/shrunken_pz_schedule.rs:676
```

Instead of separately reporting qcap overflows, it clamps the q-width row before repair sampling:

```rust
if let Some(cap) = trailmix_q_cap() {
    let cap = cap.min(u16::MAX as usize) as u16;
    for row in &mut tmp {
        row[4] = row[4].min(cap).max(1);
    }
}
```

This is mostly support-search plumbing for the qcap route, not the main Toffoli cut.

## Measured Ablations

All count-only measurements were run in:

```text
/private/tmp/ecdsafail-4352cfb-canonical-default
```

Final q980 route:

```text
POINT_ADD_COUNT_ONLY=1 TRACE_PEAK=1 cargo run --release --bin build_circuit

peak_qubits=980
peak_phase='ec3.inv_fwd/p.bitlen/p.add'
emitted ops=92,105,748
```

Ablation ladder:

```text
route                                                       peak q   emitted ops
4352cfb final                                               980       92,105,748
zero-dy disabled, defer-y still enabled                     980      105,573,887
zero-dy disabled, defer-y disabled                          980      110,227,695
85d5dae q980 reference                                      980      110,865,075
```

Approximate attribution:

```text
defer y materialization only       saves ~ 4,653,808 emitted ops
zero-dy/newdx on top               saves ~13,468,139 emitted ops
other schedule/default differences save ~   637,380 emitted ops vs 85d5dae
```

The peak phase does not move. Both submissions bind at:

```text
ec3.inv_fwd/p.bitlen/p.add
ec3.alt.cancel/p.bitlen/p.add
```

So this is a pure Toffoli/static-op reduction at fixed q980.

## Section-Level Evidence

In `85d5dae`, the EC post-inversion path has several huge sections:

```text
ec3.alt.new_dx             2,354,592 ops
ec3.dx_clean               2,354,592 ops
ec3.new_y.dx_diff_clean    2,354,592 ops
ec3.new_x                  2,348,972 ops
ec3.new_y.dx_diff          2,348,972 ops
ec3.alt.new_dy             2,329,714 ops
ec3.new_y.build            2,324,094 ops
```

In `4352cfb`, those old `new_y`/`dx_diff` sections mostly vanish. The new large non-inversion
sections are much smaller:

```text
ec3.alt.new_x_restore         33,150 ops
ec3.dx_build                  33,150 ops
ec3.dy_build                  33,150 ops
ec3.alt.new_dx                32,893 ops
ec3.dx_clean                  32,893 ops
ec3.new_x                     39,424 ops aggregate
ec3.alt.new_y_restore         14,803 ops
```

The new route adds `dy_zero` and a direct `alt.new_dy/mod_mac`, but these are cheaper than the
old detour because they replace several full modular add/multiply/uncompute phases.

## Why It Is Algebraically Correct

The ordinary point-add identities are:

```text
lambda = dy / dx
new_x  = lambda^2 - x1 - x2
new_y  = lambda * (x1 - new_x) - y1
```

For the alternate cancellation, the old route used:

```text
new_dy = new_y + oy
new_dx = ox - new_x
lambda = new_dy / new_dx
```

The key observation is:

```text
new_dy = lambda * new_dx
```

Therefore, to cancel `lambda`, we do not need to compute `new_y` first. We can construct exactly
the numerator/denominator pair that proves the same slope:

```text
(new_dx, new_dy) = (ox - new_x, lambda * (ox - new_x))
```

After lambda is cancelled, the circuit converts `new_dy` into the public output:

```text
new_y = new_dy - oy
```

The route also erases `dy` using:

```text
dy = lambda * dx
```

which is already guaranteed by the first inversion. That makes `ty` available as clean scratch.

## Correctness / Risk Notes

This route is locally trusted clean over all 9024 official shots according to the submission note.
The support precheck also reportedly passed with:

```text
zero missing factors
zero repair entries
```

Still, classify the pieces separately:

- `zero-dy/newdx` is an algebraic dataflow rewrite and looks reusable.
- `defer-y materialization` is part of the same algebraic idea: do not create `new_y` until output.
- `Q_CAP=20`, `SROT_W=5`, and `TAIL_NONCE=25` remain support/tail-gated q980 choices.
- The route still depends on the TrailMix shrunken-PZ thin schedule machinery and rfold-MBU
  arithmetic, so it is a clean challenge route, not a general theorem for all inputs.

## Practical Takeaways

1. For low-qubit TrailMix paths, avoid materializing affine outputs until they are actually needed
   as outputs. Cancellation often needs a witness ratio, not the final coordinate itself.

2. When an inversion gives `lambda = dy/dx`, use it both ways: it can build `lambda`, but it can
   also erase `dy` later because `dy = lambda*dx`.

3. A zeroed 257-bit passenger can be a valuable temporary qload scratch. This is a gate win when it
   replaces per-bit classical constant arithmetic without increasing peak.

4. The remaining q980 peak is still inside shrunken-PZ `p.bitlen`, so future qubit cuts must attack
   the inversion bitlength/compare/add microsteps. Future Toffoli cuts can keep mining EC dataflow
   identities around the inversion boundaries.

