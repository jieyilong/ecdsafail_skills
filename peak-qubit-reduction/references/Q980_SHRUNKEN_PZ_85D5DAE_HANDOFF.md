# Handoff: 85d5dae TrailMix Shrunken-PZ 1050q -> 980q

## Executive Summary

Submission `85d5dae` is a rejected but locally clean low-qubit TrailMix/shrunken-PZ route:

```text
submission          85d5dae0-4d1b-4829-bc16-ade6d3bd2dc1
source commit       f46a8c47d39bb6446beec23614799784506a984b
reset base          1caf521514708003e5cfe5313fa0730a18291008
local trusted q     980
avg Toffoli         39,648,420
avg Clifford        41,529,025.965
emitted ops         110,865,075
validation          9024 shots, 0/0/0
score               38,855,451,600
```

It is far worse on score than current SOTA because the Toffoli count is enormous, but it is valuable
as a qubit-floor reference. The main idea is to replace the opaque 1050q TrailMix op stream with a
source-level shrunken-PZ state machine whose live registers are resized every Euclidean step, then
apply support-tuned width/counter/qcap tightening.

Canonical inspection repo:

```text
/private/tmp/ecdsafail-85d5dae-canonical-default
```

## High-Level Quantum Intuition

The circuit is not primarily saving qubits by changing elliptic-curve math. It is saving qubits by
asking a more quantum-native question:

```text
Which pieces of information are actually coherent and live at this instant?
```

In a reversible quantum circuit, qubits are expensive because any value that might later be needed
for uncomputation must stay coherent. A naive modular inverse carries several full-width registers
through the entire extended-gcd process: `A`, `B`, coefficient registers, quotient state, input
passengers, and arithmetic scratch. TrailMix's shrunken-PZ design observes that the Euclidean
state naturally shrinks as the algorithm proceeds. Large high bits become known zero, constants
become known constants, and some values can be reconstructed later instead of physically carried.

The q980 route combines four quantum-computing live-set tricks:

1. **Dynamic-width Euclidean registers.** If a register's high bits are provably zero at a step,
   those qubits are no longer quantum information. The source port frees them and only reallocates
   if later steps need width again.

2. **Passenger ghosting.** Values such as `dy` and `lambda` are temporarily removed by HMR/ghost
   logic when they can be reconstructed from other still-live data. Intuitively, the circuit keeps a
   reversible receipt instead of carrying the whole 257-bit passenger across the peak.

3. **Known-constant teardown.** At convergence, several PZ registers hold known terminal constants
   such as `A=0`, `B=1`, `ca=p`, `q=0`. Known constants do not need to remain as live quantum
   payloads. The route tears them down before the lambda multiply, then recreates them for reverse
   uncomputation.

4. **Support-gated narrowing.** The submitted q980 is not a universal all-input proof. It tunes
   schedules and quotient caps against the challenge's Fiat-Shamir support and then selects a tail
   nonce that validates. This is the main reason it can push below the safer exact-looking 1027q
   source-port baseline.

## Step-By-Step Technical Route

### 1. Replace the embedded KMX blob with a source TrailMix port

In `85d5dae`, `src/point_add/mod.rs` dispatches to:

```rust
trailmix_port::build_builder().ops
```

unless `POINT_ADD_DIALOG_ROUTE=1` is set. The implementation lives under:

```text
/private/tmp/ecdsafail-85d5dae-canonical-default/src/point_add/trailmix_port
```

This is already a large difference from the earlier `shrunken-pz-1050q` branch, which used an
embedded compressed op stream. The q980 branch makes the TrailMix route inspectable and tunable at
source level.

### 2. Use an in-place affine point-add layout

The entry point is:

```text
trailmix_port/ec/point_add.rs
ec_add_inplace_shrunken_pz
```

The point-add flow keeps only the working coordinates `tx`, `ty` plus classical input constants
`ox`, `oy`. The same quantum registers are reused for several meanings:

```text
ty: dy -> new_y
tx: dx -> new_x -> dx_diff -> new_x
```

The algorithm computes:

```text
dy     = oy - ty
dx     = ox - tx
lambda = dy / dx
new_x  = lambda^2 - tx_orig - ox
new_y  = lambda * (tx_orig - new_x) - ty_orig
```

Then it cancels `lambda` through an alternate witness:

```text
lambda = (new_y + oy) / (ox - new_x)
```

This avoids carrying separate full-size coordinate and quotient passengers at the inversion peak.

### 3. Run PZ inversion as a bit-by-bit state machine

The central file is:

```text
trailmix_port/inversion/shrunken_pz_state_machine.rs
```

It uses live PZ state:

```text
A, B, ca, cb, q, s_rot, off, parity, counter
```

Every step calls `reg_widths(i)` and resizes the state:

```rust
shrunken_pz_resize(...)
shrunken_pz_pass_step(...)
```

This replaces a coarse "allocate the worst-case width forever" inversion with a step-local width
schedule. The design comment says this state-machine path supersedes the older full-division
primitive because the old version needed a fat quotient pad and did not handle large termination
quotients cleanly.

### 4. Generate and validate a thin schedule

The schedule file is:

```text
trailmix_port/inversion/shrunken_pz_schedule.rs
```

The q980 default route sets:

```text
TRAILMIX_THIN_SCHEDULE=1
TRAILMIX_THIN_SEED=278
TRAILMIX_THIN_MARGIN=0
TRAILMIX_THIN_VALIDATE=500000
```

The universal schedule comment reports:

```text
peak A+B+ca+cb+q = 741 at step 348
```

The thin schedule samples factors, validates/repairs against a finite support set, and produces
tighter per-step widths. This is a big qubit win, but it is also the point where the method becomes
support-tuned rather than a clean universal mathematical bound.

### 5. Narrow quotient/counter/rotation metadata

The submitted defaults are set in `trailmix_port/mod.rs`:

```text
TRAILMIX_COUNTER_W=8
TRAILMIX_Q_CAP=20
TRAILMIX_SROT_W=5
TRAILMIX_TAIL_NONCE=602
```

These trims attack metadata rather than main 257-bit payloads:

- `COUNTER_W=8` shrinks the step counter.
- `SROT_W=5` shrinks small rotation/state metadata.
- `Q_CAP=20` caps quotient storage.
- `TAIL_NONCE=602` chooses a tail/support instance that validates under the cap.

The qcap and tail nonce are not density-neutral exact improvements. They are challenge-support
dependent and need trusted validation.

### 6. Tear down terminal constants before lambda multiply

`shrunken_pz_divide_forward` reaches a terminal PZ state where the inverse lives in `cb`, while
other PZ registers are known:

```text
A=0, B=1, ca=p, q=0
```

The route tears down that constant pack before multiplying by `dy` to produce `lambda`. This keeps
the lambda multiply from overlapping with dead-but-still-allocated PZ constant registers. Later,
the constants are recreated so the inverse path can run backward and restore `dx`.

Quantum interpretation: if the value is known classically and can be recreated reversibly, it does
not need to occupy coherent storage across an unrelated arithmetic peak.

### 7. Ghost `dy` and `lambda` around the inversion pair

The forward division path computes:

```text
lambda = dy * cb
```

Then it HMR-ghosts `dy` and frees it so the reverse inversion can run without carrying the original
`dy` passenger. At the end, it reconstructs:

```text
dy = lambda * dx
```

and resolves the ghost.

The cancellation path similarly ghosts `lambda`, computes a temporary alternate quotient from
`new_dy/new_dx`, resolves `lambda`, uncomputes the temporary, and reverse-inverts.

This is the part that feels most like "quantum memory compression": carry a reversible/phase-safe
obligation instead of carrying a full classical-looking register through the highest live set.

### 8. Use rfold-MBU arithmetic and classical-register arithmetic paths

The arithmetic helper is:

```text
trailmix_port/rfold_mbu.rs
```

It implements rfold pseudo-Mersenne-style modular operations with measured cleanup / phase repair:

```text
mod_double_rfold_mbu
mod_halve_rfold_mbu
mod_mul_rfold_mbu
controlled add/sub variants
```

The point-add code also leans on direct classical-register add/sub paths when adding known
constants. This reduces qload-like temporary pressure in the already crowded inversion phases.

## Measured Ablation Ladder

These were count-only measurements in the canonical reset repo. They are useful for understanding
what actually creates the q980 drop.

```text
route                                                       peak q   emitted ops
source-port universal schedule, old widths                 1027     111,805,380
thin schedule, qcap wide, old counter/srot                 990      112,614,751
thin schedule + qcap20, old counter/srot                   987      111,832,043
thin schedule + counter8/srot5, qcap wide                  983      111,631,109
final q980 defaults: thin + counter8 + srot5 + qcap20      980      110,865,075
```

Interpretation:

```text
source-level dynamic PZ route        gets into the 1027q region
thin support-tuned schedule          gives about -37q
counter/srot metadata trimming       gives about -7q combined in measured variants
qcap20 + tail reselection            gives about -3q
```

The original 1050q embedded op stream is not easy to line-by-line ablate because `85d5dae` replaces
it with a source implementation. The clean comparison is therefore: TrailMix embedded low-q design
to source-level dynamic shrunken-PZ, then the source-level knobs above.

## Peak Owner

Final count-only trace:

```text
TRAILMIX_SHRUNKEN_PZ peak_qubits=980 peak_phase='ec3.inv_fwd/p.bitlen/p.add' ops=110865075
```

Top active phases:

```text
ec3.alt.cancel/p.bitlen                          980
ec3.alt.cancel/p.bitlen/p.add                    980
ec3.inv_fwd/p.bitlen                             980
ec3.inv_fwd/p.bitlen/p.add                       980
ec3.alt.cancel/p.bitlen/p.sub                    976
ec3.inv_fwd/p.bitlen/p.sub                       976
ec3.alt.cancel/p.ornz                            971
ec3.inv_fwd/p.ornz                               971
```

So after q980, the binders are not elliptic-curve output registers. They are bitlength/compare/add
subphases inside the forward inversion and alternate cancellation inversion.

## Correctness and Risk Labels

### More exact-looking structural ideas

These are conceptually reusable for exact designs if their invariants are proven:

- source-level dynamic-width PZ state machine
- in-place point-add coordinate/dataflow reuse
- terminal constant-pack teardown/recreation
- HMR ghosting when reconstruction is algebraically exact
- direct classical-register arithmetic for known constants

### Support-gated or risky parts

These should not be treated as universal exact proof without additional work:

- `TRAILMIX_THIN_SCHEDULE=1` with margin 0
- finite sample/repair validation of thin widths
- `TRAILMIX_Q_CAP=20`
- `TRAILMIX_TAIL_NONCE=602`
- rfold-MBU approximate/measurement-cleaned arithmetic unless phase/correctness obligations are
  traced for the specific route

The submission note says the q980 route is locally trusted clean over 9024 shots. That is strong
challenge evidence, but not the same thing as a universal reversible arithmetic theorem.

## Reproduction Commands

From the canonical reset repo:

```bash
cd /private/tmp/ecdsafail-85d5dae-canonical-default
ecdsafail reset 85d5dae
```

Final count-only peak:

```bash
POINT_ADD_COUNT_ONLY=1 TRACE_PEAK=1 TRACE_PHASE_ACTIVE=1 TRACE_PHASE_ACTIVE_TOP=20 \
  cargo run --release --bin build_circuit
```

Useful ablations:

```bash
TRAILMIX_THIN_SCHEDULE=0 TRAILMIX_COUNTER_W=10 TRAILMIX_SROT_W=6 \
  TRACE_PEAK=1 POINT_ADD_COUNT_ONLY=1 cargo run --release --bin build_circuit

TRAILMIX_COUNTER_W=10 TRAILMIX_SROT_W=6 TRAILMIX_Q_CAP=128 \
  TRACE_PEAK=1 POINT_ADD_COUNT_ONLY=1 cargo run --release --bin build_circuit

TRAILMIX_COUNTER_W=8 TRAILMIX_SROT_W=5 TRAILMIX_Q_CAP=128 \
  TRACE_PEAK=1 POINT_ADD_COUNT_ONLY=1 cargo run --release --bin build_circuit
```

## How This Might Help Future Work

1. **Use the source TrailMix port as an analyzable qubit-floor scaffold.** It exposes peak owners,
   schedules, and algebraic structure that the embedded KMX route hides.

2. **Separate "low q" from "good score".** q980 proves the live-set can go very low, but 39.6M
   average Toffoli is too expensive. The next research question is whether exact low-Toffoli
   compaction/cancellation passes can be applied after this source route.

3. **Attack the remaining binders directly.** The final peak is inside `p.bitlen/p.add` and
   `p.bitlen/p.sub`; reducing or dirty-borrowing bitlength scratch may be more profitable than
   changing point-add algebra.

4. **Make thin schedules provable.** If the thin schedule can be replaced by a compact exact bound
   or reversible metadata proof, the low-q technique becomes much more reusable.

5. **Try hybridizing with exact 1046/1050 postpasses.** Existing reset-bounded compaction,
   dirty-borrow C3X, and MBU fanout ideas may reduce either qubits or Toffoli once the source route
   emits a stable op stream.

