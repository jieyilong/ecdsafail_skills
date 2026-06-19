# Breaking the 1168q Wall: the `trailmix_ludicrous` Revamp and the 1167→1164q Cascade

**Date:** 2026-06-19
**Scope:** commits `bdb1d22` (tob-joe) through `b310de9` (BitWonka) on `ecdsafail/ecdsafail-challenge` `main`.
**Objective recap:** `score = peak_qubits × avg_executed_Toffoli`, lower is better. The frontier sat at the dialog-GCD 1168q design (~1.43M Toffoli) for a long time. On 6/18 9:18 PM tob-joe submitted a *complete circuit revamp* that jumped to **1167q × 1,422,591 Toffoli = 1,660,163,697** (−8.9M score), and over the next ~15 hours a swarm of contributors drove it to **1163q × 1,412,402 = 1,642,623,526** (submission `175749f`, BitWonka, 6/19 11:42 AM, source commit `b310de9`).

---

## 0. The headline: this is a different circuit family

Everything before this was the **dialog-GCD** route (1168q). tob-joe's `bdb1d22` introduces a brand-new module `src/point_add/trailmix_ludicrous/` (+5001 lines, 11 files) and rewires `build()` to call `trailmix_ludicrous::build_trailmix_ludicrous_ops()` instead of the dialog builder. It is a port of Trail of Bits' **"ludicrous" product-min operating point** (a ~99.87%-per-add success-rate config) onto the challenge's `B` builder.

The structural thesis is simple and powerful:

> **Hold the second EC point `Q` entirely classically; never give it a resident quantum register. Compute the whole affine point-add as two GCD passes that share one modular-inversion primitive, with the inversion's dialog tape compressed live.**

That single decision (`Q` classical) is the **−512 qubit** product-min lever that gets the peak under 1168 to begin with. Everything after tob-joe is incremental Toffoli shaving plus **four** hard-won −1-qubit peak drops (1167→1166→1165→1164 *free* via constant-lane parking, then 1164→1163 *paid* by surrendering apply-phase vents — see §2.1 and §2.5).

---

## 1. The new circuit, end to end (`bdb1d22`, tob-joe)

### 1.1 Register layout (`mod.rs`)
Four 256-bit IO registers, allocation order pins the fuzzer IO ids:
- `x2` (reg0) — **quantum** `P.x` → `R.x`
- `y2` (reg1) — **quantum** `P.y` → `R.y`
- `ox` (reg2) — **classical `BitId`** `Q.x` (one value per shot; the verifier's runtime control)
- `oy` (reg3) — **classical `BitId`** `Q.y`

`Q` is two *classical* bit-registers, materialized into a transient 256-bit quantum temp **only** at the off-peak coordinate steps, then freed. A naive design that kept `ox` and `oy` as resident quantum registers would add 512 qubits live across the GCD peak. This is the decisive lever.

### 1.2 EC point-add dataflow (`ec_add.rs::ec_add`, the a-independent affine law)
Computes `(x2,y2) → P+Q` in place (generic add, `P≠±Q`):

```
3:  x2 -= ox                 dx = P.x − Q.x          (coord const-sub, transient temp)
4:  y2 -= oy                 dy = P.y − Q.y
6:  y2 *= x2^-1 mod q        GCD pass #1 (Inverse) → y2 = λ = dy·dx^-1 ; x2 restored to dx
7:  x2 += 3·ox               x2 = P.x + 2·Q.x        (coord_add3x: one fewer mod-add)
10: x2 -= λ^2 mod q          fused square-subtract
11: y2 *= x2 mod q           GCD pass #2 (Forward) → y2 = λ·x2
14: y2 -= oy                 (P+Q).y
15: x2 := ox − x2 mod q      zero-Toffoli negate: ox − x2 = −(x2 − ox)
```

Two things make this cheap:
- **Two GCD passes share one inversion primitive.** Both step 6 and step 11 call the *same* `mod_mul_inverse_in_place` engine, differing only by `Direction::Inverse` vs `Direction::Forward`. The slope `λ` is produced by the inversion itself — there is no separate field-inverse-then-multiply.
- **The negate (step 15) costs zero Toffoli.** `coord_rsub` uses `ox − x2 = −(x2 − ox)`: load classical coord (0-Toffoli `x_if_bit`), subtract, free, then `mod_neg` (a const-add of `f−1`). All X / const-add gates.

### 1.3 The modular-inversion engine: Schrottenloher jump-GCD (`gcd.rs`)
`mod_mul_inverse_in_place` realizes `y → y·x^±1 mod q` as **two passes sharing one tape**:
- **Forward** (`forward_gcd_jump`): a `JUMP=2`, `ITERS=258` binary-GCD divstep loop on `(u=q, v=x)`. Each step records a **3-bit dialog symbol `(subtracted, swap, s_2)`** plus a single global first-shift bit `t1`, and **compresses each window inline** the instant its symbols exist.
- **Reverse** (`reverse_gcd_jump`): the exact gate-inverse. It **decompresses one window at a time** from the tape end, applies the fused multiply, then inverts the divstep ops, restoring `x`.

Per-step divstep mechanics:
- **Shift-first** (jump=2): shift out low zero bits; `t1` records the step-0 even/odd choice; `s_2` flags the second (jump) shift.
- `subtracted = v[0]` post-shift → if odd, swap+subtract.
- **Swap decision** via a *narrow top-window* comparator (`comparator::controlled_swap_decision_lt_truncated`) — only scans `GAP_J2[i]` MSBs.
- **cswap + active-width subtract** `v −= subtracted·u` via `controlled_add_active`.
- **Kaliski odd-u bit-0 shortcut**: `u[0]==1` always, so the bit-0 carry-out is provably 0 — emit `cx(ctrl, y[0])` directly and run the capped adder on bits 1.. with carry-in 0 (~1000+ Toffoli saved across both passes).

**Shrink/regrow width schedule = the qubit floor.** `SCHED_J2[i]` (len 258) is the per-step active width: it holds at 256 for ~11 steps, then ramps to 13 by step 257. Each step frees the `u`/`v` qubits above the schedule width (`zero_and_free`); the reverse pass re-allocates them. The whole body (comparator, cswap, subtract) runs on `current_n = SCHED_J2[i]` bits, so **the adders run in the freed headroom**. This is the primary *lossy* lever — a `dx` whose bitlength exceeds the schedule width is rejected (it would make `zero_and_free` panic), which is exactly why the design needs a Fiat-Shamir nonce tail that lands all 9024 verifier draws in the schedule-supported set.

### 1.4 The all-triple base-5 codec (`codec.rs`) — resident tape 603q vs 772 raw
Only **5 of 8** `(subtracted, swap, s_2)` patterns are reachable, so a window of 3 symbols carries `log2(5^3) ≈ 6.97` bits and packs into a **7-bit code** (tighter than a K5 15→12 codec). Tiling: 1 `Step0` symbol (2 bits) + 85 `Triple`s (7 bits each) + 1 `Pair` tail (5 bits) + 1 `t1` bit = **603 resident qubits** vs `1 + 3×257 = 772` raw.

- **SAT-synthesized in-place pairs core** (`compress_2sym_fast`): a straight-line reversible `x/cx/ccx` circuit mapping the 25 valid 2-symbol inputs to 25 distinct 5-bit codes, freeing a wire; the terminal AND-uncompute is **vented** (HMR + conditional-Z, 0 Toffoli). The Triple codec is `pair → affine normalizer → fold-in s_2`.
- **Inline interleave + streamed decompression**: windows are compressed as produced (forward) and decompressed one-at-a-time (reverse), so the tape is never expanded all at once. The multiply *apply* is fused **into** the GCD passes, not run as a separate phase.

### 1.5 The vented-adder zoo + baked schedule tables (`gidney.rs`, `fused.rs`, `schedule.rs`)
Every adder vents its carry-uncompute via **Gidney-2025 measurement-based AND-uncompute (MBU)**: `hmr(carry,bit); cz_if_bit(a,b,bit)` — an X-basis measurement replacing the reverse-CCX with a conditional-Z, **0 Toffoli**. Each vent = −1 Toffoli, +1 transient qubit, held only between the forward/reverse carry chains.

The adder *family*, dispatched per-call by baked tables:
- plain Gidney AND-carry; variable-chunk (`varchunk`); headroom-adaptive (√n-chunk) → chunked-then-Cuccaro tail; cofactor-add cout core.
- A **fused double+cdouble** `y := 2(1+s_2)·y mod q` with one combined `(e+2d)·f` reduction instead of two separate `+f` adds.

`schedule.rs` bakes *every* per-call cost decision so the op-stream is deterministic and the peak is pinned: `GCD_SUB_K`, `GCD_BRANCH`, `APPLY_COUT_K`, `FOLD_SCHED`, `CMP_K`, `FFG_G`, `HYB_V`, `SQ_ROW_K`. Each adder's vent budget is set to exactly `CEILING − active_qubits` where `CEILING = 1167` — i.e. the schedule spends every spare qubit under the peak on vents (free Toffoli) and never exceeds it.

### 1.6 Deliberate exact-modular truncations (`arith.rs`)
`f = 2^32 + 977`, `PAD = 21`.
- **Low-54-bit `+f` fold** (`LSBS = PAD + F_BITLEN = 54`): every reduction fold touches only the low 54 bits; carry beyond bit 53 is dropped — wrong only with prob ~`2^-21` per fire on a uniform operand.
- **Narrow-top-window comparators** (`MSBS = PAD = 21`): overflow/swap predicates recompute on the top 21 bits only, cleaned by measurement-vent; a mis-decide happens only when the highest differing bit sits below the window (~`2^-21` / `2^-GAP` per call).

These are safe under the 9024-shot verifier because each is an independent ~`2^-21`-per-fire divergence; the common path is exact and the expected failing-shot count stays under tolerance. `PAD` is the master knob trading those rare misses for dropped-carry / narrow-comparator Toffoli savings.

### 1.7 Where 1167q and 1.42M Toffoli come from
- **Peak (1167)** is owned by the **forward-multiply GCD apply (step 11) cofactor-add hot path**: ~512 (two coord regs) + 603 (resident compressed tape) + early-width `u/v` + transient carry/vent ancilla. The −512q classical-`Q` lever and the 603-vs-772 tape compression are exactly what hold it at 1167.
- **Toffoli (1.42M)**, dominant consumers: (1) the symmetric schoolbook square (`n(n−1)/2` crosses, build+unbuild), (2) the two GCD passes' subtract adders ×258×2×(fwd+rev), (3) apply cofactor add/sub + fused double-cdouble, (4) codec compress/decompress (~18 Tof/Triple), (5) narrow comparators. **All AND-uncomputes are vented → 0 Toffoli**; Toffoli is spent only on forward carry chains, square ANDs, and gated register adds.

---

## 2. The 1167→1163q cascade (everything after tob-joe)

> **Measurement caveat:** almost every commit rewrites whole `.rs` files with LF↔CRLF churn, producing cosmetic symmetric `+N/-N` diffs. Below, only genuine content changes are listed (normalized away the CRLF noise).

### 2.1 The three *free* −1-qubit peak drops (1167→1164, constant-lane parking)
Each removes one qubit from the GCD-divstep peak by eliminating or **loaning back** a provably-constant low-bit lane (via the external `B::loan_zero_qubit`/`reclaim_zero_qubit` primitives), at roughly Toffoli-neutral cost. (The fourth drop, 1164→1163, is *paid* — see §2.5.)

- **`ab1b2d6` (PhantasticUniverse) 1167→1166, also −1.39M Toffoli.** Eliminates the dedicated `swap_flag` ancilla at the step-0 divstep: it becomes `Option<QubitId>`, allocated lazily only for steps ≥1; at step 0 the swap control *is* the `subtracted` qubit. A new codec `compress_step0_with_t1` folds the `t1` first-shift prefix bit into the step-0 symbol with one `ccx(t1,s2,sub)`, freeing both the `sub` and `swap` slots and dropping `tape_len` by 1. The freed `t1` prefix qubit is the −1; the cheaper step-0 path is the Toffoli win.
- **`cea9f5f` (BitWonka) 1166→1165.** "Park odd u0": `u[0]` is provably 1 (u odd invariant), so `park_known_one` does `X→|0>` then `loan_zero_qubit` to return the lane to the pool during the high-bit adder; `restore_known_one` reverses it. Knobs `TLM_PARK_ODD_U0=1`, `TLM_LOAN_ODD_U0=1`.
- **`f8d23a9` (BitWonka) 1165→1164** (Toffoli ticks *up* +329, accepted trade). "Park even v0" + "loan gcd y0": `v[0]` is provably 0 (v even) and the controlled-add's `y[0]` is a known constant; loan both lanes during the high-bit adder. A new `GcdBit0Mode::{ForwardKnownOneAfterCx, ReverseKnownZeroBeforeCx}` **delays the bit-0 CNOT** until after the high-bit adder so `y[0]` can be borrowed. Knobs `TLM_PARK_EVEN_V0`, `TLM_LOAN_EVEN_V0`, `TLM_LOAN_GCD_Y0`.

The common pattern: **provably-constant lanes in the GCD divstep (odd-u0=1, even-v0=0, known y0) are not held live — they are parked/loaned back to the free pool across the adder that needs the headroom.**

### 2.2 The big Toffoli wins
- **`bc2334a` (BitWonka) −5.9M — largest single win.** An **exhaustive-search adaptive chunked carry layout** (`searched_cout_layout`, `searched_gcd_adaptive_layout`, `adaptive_chunk_size` in `gidney.rs`): for each controlled clean-add of width n, search all `(chunk_size, plain_len)` splits minimizing carry-ancilla cost `2n + chunked_len + nchunks ± 1` under a `k`-qubit budget. Gated by `TLM_COUT_LAYOUT_SEARCH`, `TLM_GCD_ADAPTIVE_LAYOUT_SEARCH`. (Also reverts b1dec1e's identity and deletes the dead `single_ccx_fanout` staging.)
- **`497cc20` (gopikannappan) −1.38M.** Adds `constprop.rs`: a sound classical constant-propagation post-pass over `{Zero,One,Unknown}` seeding all qubits |0> except input regs. CCX with provably-0 control → **drop** (removes a Toffoli); provably-1 control → **fold to CX** (demotes to uncounted Clifford). Includes a `CONSTPROP_VERIFY` simulator cross-check. *This is a generic post-pass that any of these circuits benefits from — it just deletes Toffoli the structure made constant.*
- **`b1dec1e` (nasqret) −1.25M.** `toggle_dnot_e_from_intersection`: the identity `d & !e = d ^ (e & d)` computes `d AND NOT e` with **2 CX instead of 1 CCX**, reusing the already-live `cc = e AND d` — one Toffoli saved per call across ~6 fused-primitive sites.
- **`a47dc6e` (PhantasticUniverse) −1.19M — looks like a knob flip, is a structural one-liner.** Two divstep loops change `for j in 0..current_n` → `1..current_n`, **skipping j=0**. Because cea9f5f/f8d23a9 made `u[0]`/`v[0]` provably constant, the j=0 cswap is a provable no-op — one cswap (Toffoli) saved per GCD iteration over ~258 iters. Pure structural edit *enabled by* the parking commits.
- **`b02b354` / `9798bc9` / `fa7126d` (gopikannappan) −0.46M / −0.36M / −0.43M.** Extend `constprop.rs` (25KB→70KB) with **affine/XOR-relation tracking** + **inverse-pair detection** — drop/fold CCX when a control is provably XOR-equal to a known wire, beyond plain constants. (Re-added several times because the qubit-drop commits keep reverting it to the base version.)
- **`12c7337` (PhantasticUniverse) −0.10M.** Turns the `single_ccx_fanout` peephole from a single pass into a **fixpoint loop** (apply until no rewrite).
- **`b310de9` (BitWonka) — this is the 1164→1163 *qubit* drop, not just a knob tweak. Analyzed in detail in §2.5 below.**

### 2.3 Knob/schedule/infra-only commits
`a9ac507` (jieyilong, fold-vent schedule knobs `LUD_EXTRA_FOLD_*`), `c9c03de` (jackylee, adds the `TRAILMIX_*_DELTA` overlay infra), `75851e6` (bket7, comparator-width margin), `ed2715f` (gnuchev, layout-search margin tuning), `916c0e3`, `01560c7` — all small knob/table tweaks on top of the above structures.

### 2.4 Pure nonce grinds (cosmetic for circuit structure)
`615ce9a`, `5407215`, `fd89e69`, `550595a`, `f265bb1`, `fdb103e`, `6a9db88`, and `70bf11a` — these changed only `DIALOG_TAIL_NONCE` (a Fiat-Shamir island grind that re-seeds which clean island the verifier hits; score-neutral in gate count, but a different nonce can shave a few Toffoli by landing a cleaner schedule). `70bf11a` staged a `single_ccx_fanout.rs` but left it un-wired (dead code at that commit).

### 2.5 The *paid* −1q drop: 1164→1163 (`b310de9`, BitWonka — current SOTA `175749f`, 1163q × 1,412,402 = 1,642,623,526)

This is categorically different from the three free parking drops in §2.1. It does **not** find a new constant lane to park — it **buys** the 1163rd-qubit reduction by surrendering vents at the binding apply phase (and tightening the truncation windows), paying **+419 Toffoli** for **−1 peak**. The +419 is dwarfed by the −1-qubit factor (each peak qubit at this scale is worth ~1.41M of score), so the net is **−924,686** even though Toffoli went *up*. Verified: `constprop.rs`'s giant diff is pure CRLF churn — the real content is four small edits:

1. **Apply-schedule vent/cap reductions via the overlay deltas** (`mod.rs`, the new `sub_delta`/`env_delta` machinery): `TLM_HYB_V_DELTA=2` (−2 hybrid-adder vents), `TLM_COUT_K_DELTA=1` (−1 apply cofactor-add carry-cap), `TLM_FFG_DELTA=2` (−2 `+f`-fold clean-vents), `TLM_FOLD_DELTA=1`. **Removing vents at the binding apply phase frees the transient vent qubits that own the peak** — this is the mechanism that drops 1164→1163. Each removed vent is +1 Toffoli (the carry-uncompute reverts from a 0-Toffoli MBU back to a real CCX), which is most of the +419.
2. **`PAD` 21→19** (`arith.rs`) and **21→20** (`schedule.rs`): tightens the truncation windows (`LSBS = PAD + F_BITLEN`, `MSBS = PAD`). Narrower `+f` folds and comparators mean fewer live bits *and* fewer Toffoli, at the cost of a higher per-fire miss rate (`2^-19` instead of `2^-21`). This partially *offsets* the vent-cost Toffoli increase and shrinks the truncation-region live width.
3. **`maybe_adjust_late_gcd_k`** (`gcd.rs`): a window-gated GCD-subtract carry-cap trim — for divstep iters `[172,196)`, `k -= 1` (`TLM_GCD_K_ADJUST=-1`, `_AFTER=172`, `_BEFORE=196`). Fewer held carries in that late-GCD window.
4. A fresh `DIALOG_TAIL_NONCE` (`100000688994`) grinding a clean island under the now-tighter (`PAD=19/20`) miss budget across all 9024 shots, and replacing the old `LUD_EXTRA_FOLD_*` fold-vent values with `0` (the apply-delta relaxations subsume them).

**The lesson:** §2.1's three drops were *free* (park a constant lane, Toffoli ≈ neutral). This fourth drop is the **qubit↔Toffoli exchange rate run in reverse** — the skill's vent primitive normally says "vent OFF-peak for free Toffoli; venting the binding phase costs score." Here, *un-venting* the binding phase **buys** a peak qubit, and at 1163q each peak qubit (~1.41M) is worth far more than the +419 Toffoli surrendered. Tightening `PAD` against the verifier tolerance is the companion lever that keeps the net Toffoli cost small. This is the first drop in the cascade that spends Toffoli to buy a qubit, and it confirms the exchange-rate model is *the* live lever at the ludicrous floor.

---

## 3. Key insights / takeaways

1. **The wall broke on a family change, not a knob.** The dialog-GCD route was at a local floor (1168q). tob-joe's port of the **product-min "ludicrous"** point — *classical Q + two-shared-GCD-passes + live-compressed dialog tape* — reset the floor to 1167 and opened a fresh ladder.

2. **Classical `Q` (−512q) is the single most important structural decision.** Holding the second point classically and materializing it only in a transient temp at off-peak steps is what makes a 256-bit-arithmetic point-add fit under 1168 qubits at all.

3. **The qubit floor is the GCD shrink/regrow width schedule, and there are TWO ways to lower it.** Peak qubits are set by what's co-resident at the forward-multiply apply: two coord regs + the 603q compressed tape + early-width GCD state + transient vent ancilla. (a) **Free** drops (1167→1164): **don't hold provably-constant low bits live — park/loan them back across the adder that needs the headroom** (odd-u0=1, even-v0=0, known-y0, redundant step-0 swap_flag); Toffoli ≈ neutral. (b) **Paid** drop (1164→1163, `b310de9`): **surrender vents at the binding apply phase** — un-venting frees the transient vent qubits that own the peak, costing +Toffoli (each removed vent = +1 CCX) but buying a peak qubit worth far more.

4. **Toffoli is shaved two ways, and both are reusable elsewhere.** (a) A *generic sound post-pass* (`constprop` + affine/XOR/inverse-pair) that deletes/demotes Toffoli the structure made constant — model-agnostic, would help our routes too. (b) *Structure-aware* tricks: exhaustive carry-chunk layout search, the `d&!e` 2-CX identity, skip-j0 cswap elision, MBU venting everywhere.

5. **Aggressive truncation is a deliberate, budgeted error — and the companion to the paid qubit drop.** `PAD=21` (now 19–20 after `b310de9`) means each `+f` fold and comparator accepts a ~`2^-19`-per-fire miss; the 9024-shot verifier tolerates it, and `DIALOG_TAIL_NONCE` grinds the inputs so all draws land in the schedule-supported set. Tightening `PAD` shrinks both the live truncation width *and* the Toffoli, which is what kept the net cost of the 1164→1163 vent surrender to only +419 Toffoli. `PAD` is a live lever in **both** directions (qubits and Toffoli).

6. **The qubit↔Toffoli exchange rate is THE live lever at the ludicrous floor.** The first three drops were free; the SOTA-leading fourth (`b310de9`) is the exchange rate run in reverse — spend a few hundred Toffoli to buy one peak qubit, because at ~1163q a peak qubit is worth ~1.41M of score and the surrendered vents cost only ~hundreds. Expect the next drops (1163→1162…) to be increasingly *paid* as the free constant lanes run out.

7. **The shrunken-PZ floor is still not score-competitive.** teddyjfpender's 1019q submission (`55892ec`) scored 32.1B (+283%) and was *rejected* — confirming the 1050/1019q Proos-Zalka class is a qubit-lower-bound witness, not a product-min contender. The action is all at the 1163–1167q ludicrous operating point.

---

## 4. What this means for our own pushes
- The `trailmix_ludicrous` module is now the **base to fork from**, not the dialog-GCD 1168 route. Our prior dialog-GCD levers (vented-body BAND_TRIM/ODD_LOWBIT) are superseded as a *base* but the *techniques* (MBU venting, odd-lowbit shortcut) are already native here.
- The open qubit lever is now **two-pronged**: (1) **more provably-constant-lane parking** in the divstep (free, but the easy lanes are taken); (2) **paid vent surrender at the apply peak + `PAD` tightening** (`b310de9`'s recipe), which is the live SOTA lever — spend Toffoli to buy a peak qubit while grinding a clean nonce under the tighter miss budget.
- The open Toffoli lever is **extending the constprop/affine post-pass** and the **carry-layout search** — both are generic and still actively yielding (gopikannappan's affine extension, BitWonka's layout search).
- The `DIALOG_TAIL_NONCE` grind is a cheap, score-positive search any of us can run (it's offline island tooling, not part of the scored gate count).
