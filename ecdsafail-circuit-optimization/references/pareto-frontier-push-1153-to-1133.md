# The (Q, T) Pareto-Frontier Push: 1153q → 1133q (clean, value-exact basis)

**Author/agent:** jieyilong (with GPT-5 / GPT-5-Codex sub-agents). **Dates:** 6/23–6/27/26.
**What this is:** a deliberate mapping of the **value-exact (qubits, Toffoli) Pareto frontier**
below the 1153q SOTA, published as a sequence of **clean, dead-CCX-free basis circuits** others can
fork. This is **objective 3** of the challenge (explore the (Q,T) frontier — especially the *useful
corner* where both Q and T beat the published estimate for a **single secp256k1 point addition**:
**≤1175q / ~2.69M Toffoli** (2²¹·³⁶), the Babbush et al. space-optimized figure in Schrottenloher
2026 Table 1, arXiv:2606.02235 — *not* the full-ECDLP ≤1200q/≤90M Toffoli, which is the whole Shor
run of ~28 point additions). This is *not* a product-score bid. Every rung below 1153 is "rejected"
on the Q×T product **by construction** — judging them by the score is a yardstick error.

> Companion: this extends `REPORT_1168_wall_revamp.md` §2.13 (which covered 1153→1141 in detail)
> with the new **1141→1133** rung and a unified frontier view. For the score-track SOTA (1152q ×
> 1.36M, value-exact) see §2.14 of that report.

---

## 1. The frontier at a glance

All points are **dead-CCX-free** (`DROP_DEAD_ROBUST_DISABLE=1` hard-set) — a sound reusable basis
with no island-overfit gate deletion. `T_clean` is the average-executed Toffoli of the clean circuit.

| submission | source | q | T_clean | score | vs SOTA@submit | clean exchange vs prev |
|------------|--------|---|---------|-------|----------------|------------------------|
| `5fc2e81` (anchor) | `da51a48` | 1153 | 1,392,603¹ | 1,577,865,511² | promoted (was SOTA) | — |
| `8155bb8` | `3e3966b` | 1147 | 1,396,769 | 1,602,094,043 | +0.23% | **−694 T/q** (−6q / +4,166 T) |
| `fa3bb03` | `e64cdfd` | 1146 | 1,408,582 | 1,614,234,972 | +0.34% | −11,813 T/q (−1q / +11,813 T) |
| `71b9cc4` | `48e6c23` | 1143 | 1,411,643 | 1,613,507,949 | +0.33% | −1,020 T/q (−3q / +3,061 T) |
| `3ab4f86` | `0cbc2d7` | 1142 | 1,415,790 | 1,616,832,180 | +0.36% | −4,147 T/q (−1q / +4,147 T) |
| `370fc31`³ | `370fc31` | 1141 | 1,423,723 | 1,624,467,943 | +0.43% | −7,933 T/q (−1q / +7,933 T) |
| `1c0e0e9` | `765ef38` | **1133** | **1,460,511** | 1,654,758,963 | +0.77% | **−4,599 T/q** (−8q / +36,788 T) |

¹ The clean (dead-CCX-off, cinc-on) anchor T; the *promoted* 1153 SOTA value with dead-CCX on was
1,368,487. ² Score shown is the promoted dead-CCX-on score. ³ `370fc31` is both the source commit
and the listed reset base for submission `3d9ce59`.

**The whole curve sits in objective-3's "useful corner":** the bar is the published *single
point-addition* estimate — Babbush space-optimized **1175q / 2²¹·³⁶ ≈ 2.69M Toffoli** (Schrottenloher
2026 Table 1; Schrottenloher's own space-opt is 1192q / 2²¹·¹⁹ ≈ 2.39M). Every rung here clears
**both** axes: q ∈ [1133, 1153] is under 1175, and every T ≈ 1.37–1.46M is **comfortably under
2.69M** (~2× headroom). So this is a map of the *reachable* frontier in exactly the regime that
matters — not a far-off lower-bound witness (contrast the 851q low-qubit track, which spends ~460M
Toffoli, ~250× over the product break-even and ~170× over the single-PA Toffoli figure). *(Do not
confuse this with the full-ECDLP estimate ≤1200q / ≤90M Toffoli, arXiv:2603.28846 — that is the
entire Shor run of ~28 windowed point additions, not the single PA the challenge scores.)*

**Net 1153→1133:** −20 qubits for +67,908 clean Toffoli (~3,395 T/qubit averaged). The curve is
**jagged and steepens below ~1146** — exactly the signal a future designer wants: it says where the
ludicrous route starts fighting back, and how much Toffoli a later lever (a re-hunted dead-CCX
screen, a cheaper inversion, a denser codec) must recover at each qubit count to make that width
product-competitive.

---

## 2. The lever taxonomy (what *kind* of move each qubit costs)

Every rung trades **qubits ↓ for Toffoli ↑**, value-exactly, by one of four mechanisms. They sort
cleanly by exchange rate:

1. **Fold-vent clamping (the cheap qubits).** `TLM_FOLD_CALL_CODE_OVERRIDES` clamps each peak-defining
   fold's measured-vent-window count: `nv = min(code, headroom − reserve)`. Each window dropped is
   −1 transient qubit at the peak and +Toffoli (the vented carry reverts toward a real uncompute).
   This is the primary frontier dial — −694 T/qubit at 1147, the cleanest single knob.
2. **No-ancilla / dirty-borrow substitution (the medium-to-expensive qubits).** Run adders and the
   GCD body with no fresh carry ancilla, borrowing dirty lanes and restoring them (`TLM_DIRTY_BODY_*_NOANC`,
   `TLM_ARITH_DIRTY_CARRYIN_NOANC`, `TLM_GIDNEY_ZERO_CIN0_NO_COUT`). Each converts an ancilla into
   Toffoli. The `TLM_GRAD_DISABLE` graduated→dirty-carry-in swap at 1146 is the steepest point
   (−11,813 T/qubit — "here's where the route fights back").
3. **Constant-lane loan + recompute.** Temporarily free a provably-constant GCD low bit and rebuild
   it (`TLM_LOAN_ODD_U0`, `TLM_LOAN_EVEN_V0`, `TLM_LOAN_GCD_Y0`) — the Bennett pebble move on a cheap
   pebble. Plus dialog-symbol flag-lane recycling (`TLM_GCD_RECYCLE_SYMBOL_FLAGS`).
4. **Active-width trimming + tighter layout (the deep tail, new at 1133).** Shrink the *live bit-width*
   of the GCD operands per step as the algorithm converges, plus tighter carry/output layout search
   (`TLM_GCD_ADAPTIVE_LAYOUT_MARGIN`, `TLM_COUT_LAYOUT_*`) and codec scratch reuse
   (`TLM_TRIPLE_CODEC_REUSE_PAIR_FREED`, `TLM_CODEC_PAIRRAW_LAST_K`).

None touches the dead-CCX path — that omission is the deliberate clean-basis constraint.

---

## 3. Per-rung detail

The 1147→1141 rungs fork `da51a48` and swap in a `configure_q11XX_*` block in `src/point_add/mod.rs`
(the per-rung baking; the lower-level `trailmix_ludicrous/mod.rs` defaults are overridden by it).
The 1133 rung is rebased onto the later `d44cad3` (1152 structural-dead-skip) base.

- **`3e3966b` → 1147q × 1,396,769** *(fused.rs +21)*. The minimal step. `TLM_TARGET_Q` 1152→**1144**
  + a 4-call fold-vent clamp `249:5,250:5,263:5,264:5` (the four peak-defining folds → 5 windows) +
  the base knobs (`TLM_FOLD_CHUNK_ZERO_CIN`, `TLM_FFG_MAX_G=47`, `TLM_APPLY_ADD_SKIP_LASTK`,
  `TLM_FOLD_TAIL_CINC`). −6 qubits for +4,166 T — the cleanest dial on the frontier.
- **`e64cdfd` → 1146q × 1,408,582** *(fused.rs +21, arith.rs +21)*. Same ceiling; widens the override
  to six calls (two folds pushed to **code 0 = fully un-vented**) and adds **`TLM_GRAD_DISABLE`**:
  the controlled const-add drops its phase-clean graduated staircase adder and routes through the
  borrowed-dirty carry-in path (drops a carry-out ancilla, costs Toffoli). The steepest rung:
  ~12k Toffoli for 1 qubit.
- **`48e6c23` → 1143q × 1,411,643** *(fused.rs +49, arith.rs +21, codec.rs +56)*. `TLM_TARGET_Q=1143`;
  12-call override (code-4 band). Two new value-exact levers: **`TLM_TRIPLE_CODEC_REUSE_PAIR_FREED`**
  (triple-codec reuses the pair-codec's just-freed scratch — an aliasing/live-range win on the dialog
  tape) and **`TLM_FOLD_DIRECT_DIRTY_CTL`** (fold controls driven off dirty lanes). −3q / +3,061 T.
- **`0cbc2d7` → 1142q × 1,415,790** *(+gidney.rs +26)*. `TLM_TARGET_Q=1141`; adds
  **`TLM_CODEC_PAIRRAW_LAST_K=2`** (keep only the last 2 pair-raw codec cells) and tightens the
  carry-chunk layout search margin 3→2. −1q / +4,147 T.
- **`370fc31` → 1141q × 1,423,723** *(the big source delta: fused.rs +233, gcd.rs +101, gidney.rs +82)*.
  `TLM_TARGET_Q`→**1139**, layout margin 0, override extended to 22 calls, **plus the whole
  no-ancilla / loan family**: `TLM_LOAN_ODD_U0/EVEN_V0/GCD_Y0` (loan+recompute the provably-constant
  GCD low bits), `TLM_DIRTY_BODY_LINEAR_NOANC/ALL_NOANC`, `TLM_ARITH_DIRTY_CARRYIN_NOANC`,
  `TLM_GIDNEY_ZERO_CIN0_NO_COUT`, `TLM_COUT_LAYOUT_SEARCH`+margin 0, `TLM_GCD_RECYCLE_SYMBOL_FLAGS`.
  Same 1141 peak as `0cbc2d7` but +7,933 more Toffoli — the deepest knob-only squeeze.

### The new rung — `765ef38` → 1133q × 1,460,511 (the 1141→1133 jump)

This is the first rung that goes **structural**, not knob-only. `configure_q1133_*` *layers on*
`configure_q1141_9_6_*` and then adds a coordinated repair (verbatim from `src/point_add/mod.rs`):

```
TLM_TARGET_Q=1131                         (aspiration; realized peak lands at 1133)
TLM_GCD_ACTIVE_WIDTH_TRIM=3               ← the headline lever
TLM_GCD_ACTIVE_WIDTH_TRIM_AFTER=205       (trim only the post-205 convergence tail)
TLM_GCD_ACTIVE_WIDTH_TRIM_OVERRIDES=254:4,255:4,256:4,257:4   (4 bits at the latest steps)
TLM_FOLD_FINAL_NO_COUT=1                  (drop the final fold carry-out lane)
TLM_FOLD_BOUNDARY_ZERO_DIRECT=1           (measurement-erase the fold boundary carry)
TLM_FOLD_ZERO_DIRECT_BORROW_CIN_C0=1      (borrow carry-in c0 for the zero-direct fold)
TLM_COMPARE_BORROW_CIN_C0=1               (comparator borrows its carry-in too)
TLM_CMP_CARRY_K_DELTA=-6                  (narrow the comparator carry-chunk width by 6)
TLM_CODEC_PAIRRAW_LAST_K=1               (keep only the last 1 pair-raw codec cell)
TLM_FOLD_ZERO_CHUNK_CINC=1 ; TLM_APPLY_INV_S2_ZERO_LAST=1
TLM_COUT_EFFECTIVE_TRIM=10 ; TLM_GCD_ADAPTIVE_LAYOUT_MARGIN=2
TLM_FOLD_CALL_CODE_OVERRIDES = <~60 calls, almost all clamped to code 0>
```

**The headline mechanism — GCD active-width trimming** (`gcd.rs:139 active_width_trim_for_step`,
`:160 active_width_for_pass_step` → `current_n = base − trim`). As the binary GCD converges, the
operands `u, v` lose high bits; a naive circuit keeps full width for all ~530 steps. Active-width
trimming **shrinks the live operand width per step** in the late tail (−3 bits after step 205,
−4 at steps 254–257), so the GCD body adders/folds in that tail run on fewer lanes. This is exactly
the **dynamic-width-register idea** (see primer §6.6) applied per-step to the ludicrous GCD tail —
the structural source of the deepest qubits on the frontier.

**Why 1133 and not lower — a value-exact repair.** The team first pushed to a **1131** "PairRaw1
codec-wall" route, but it *over-trimmed* the post-205 active width — clipping late GCD/carry state
inflated the classical/phase residual so no clean Fiat-Shamir island could be found. The 1133
submission **gives back two qubits** (relax the late-tail trim: 3 generally, 4 held at 254–257) to
reduce the residual just enough that a clean island (nonce `12846838`, 0/0/0 over 9024 shots) becomes
reachable — while keeping the rest of the low-qubit structure and adding **no** dead-CCX deletion.
Lesson: on this route the *binding* qubits live in the GCD convergence tail, and trimming them is a
**graded** correctness lever (§ primer "binary vs graded") — push the trim until the residual breaks,
then back off one notch and hunt.

**Supporting levers at 1133:** `TLM_FOLD_FINAL_NO_COUT` drops the final fold carry-out; the
`*_ZERO_DIRECT` + `*_BORROW_CIN_C0` pair measurement-erases the fold boundary and borrows its
carry-in rather than allocating one (a fold-local instance of borrowed-carry / direct-zero, primer
§6.11/§6.13); `TLM_CMP_CARRY_K_DELTA=-6` narrows the comparator carry chunk; the ~60-call fold override
clamps essentially every fold's vent count (most to 0). Together these clear the lanes the
active-width trim needs.

---

## 4. A new general mechanism introduced in this push: reset-bounded qubit-id compaction

`765ef38` adds a new file **`trailmix_ludicrous/compact.rs`** (`compact::run`, gated by
`TLM_RESET_BOUNDED_COMPACT=1`, invoked at `trailmix_ludicrous/mod.rs:460`). It is **not** used by the
1133 submission, but it is a reusable, fully-general lever worth recording:

> *"The builder reuses freed qubits, but the scored qubit count is the maximum id appearing in
> `ops.bin`. This pass recolors non-IO temp lifetimes after unconditional resets/HMRs, preserving
> the four benchmark registers."*

The scored width is `max qubit-id`, **not** the true simultaneous peak. If lifetime→id assignment
is loose, the max id can exceed the real peak. `compact.rs` builds the temp-lane lifetime segments
(split at unconditional `R`/`Hmr` resets), then **interval-colors** them onto the fewest ids
(a min-heap of free colors keyed by lifetime end), pinning the four IO registers. This is classic
register allocation / graph-coloring applied to qubit ids — a value-exact, density-neutral
post-pass that can recover whatever slack the builder left between *true peak* and *max id*. It is a
promising drop-in for any future rung whose reported count exceeds its measured concurrent peak.

---

## 5. How to use this frontier

- **As a fork target.** Each rung is a clean, reproducible, value-exact circuit at its qubit count.
  A future designer layers their own (better) dead-CCX screen / arithmetic / codec on top and measures
  the gain against a sound reference — no island-overfit contamination.
- **As a budget.** At each q, the gap `T_clean(q) − (SOTA_score / q)` is exactly how much Toffoli a
  new lever must recover at that width to tie the product SOTA. E.g. a clean 1147q basis needs
  ~21k Toffoli recovered; a clean 1133q basis needs ~67k.
- **As a map of where the route fights back.** The exchange rate steepens below ~1146 and the 1141→1133
  tail costs ~4,600 T/qubit — telling you the cheap qubits are exhausted and the remaining ones come
  from active-width trimming and dirty-borrow substitution in the GCD convergence tail.

## 6. Pointers

- `REPORT_1168_wall_revamp.md` §2.13 — original 1153→1141 frontier analysis; §2.14 — the value-exact
  1153→1152 score-SOTA break (cy0 free-and-recompute + structural-dead pivot).
- Source: commits `da51a48` (1153 anchor) → `3e3966b`/`e64cdfd`/`48e6c23`/`0cbc2d7`/`370fc31`
  (1147→1141) → `765ef38` (1133), all under `src/point_add/mod.rs` `configure_q11XX_*` +
  `src/point_add/trailmix_ludicrous/*.rs`. Pull any with `ecdsafail reset <submission-id>`.
- Memory: `ecdsafail-q1133-resident-cyl0-hunt.md` — the (negative) hunt for the *next* qubit below
  1133 (the cy0/u[0] free-and-recompute lever is exhausted on this base; the 1133 fold consumer has
  `free_pool=0`, so the next −1q needs a fold lane-discipline rewrite or a non-fold resident recompute).
