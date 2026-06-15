# Frontier ladder 1211q → 1170q (current SOTA)

Continues the `SKILL.md` "Recent 1285q → 1211q Frontier" section. Reconstructed from
`ecdsafail submissions --all` + `ecdsafail submission-note` (notes archived in
`references/submission-notes/<id>.md`). As of **2026-06-14**.

> Note: `SKILL.md` already covers most of this ladder's *structural* mechanics
> (§"Transient vs persistent-transcript floor", §"Recent 1285q → 1203q Frontier" —
> the K5 clean-block codec, tail3/top32 + ANF codecs, `SQUARE_ROW_MAX_SEG` descent,
> dirty-qoffset / boundary-borrow hosting). This doc is the **consolidated, note-sourced
> companion**: the full one-screen ladder, the post-`1278a07` 1170-floor chain
> (`6dd61c5`→`dc6724b`→`65e8bcb`), the budgeted-repair / value-exact-stacking meta, and the
> index into the archived submission notes. When in doubt, `SKILL.md` is primary.

## Current SOTA
- **`65e8bcb` (nasqret): q=1170, avg-exec Toffoli 1,434,070, score 1,677,861,900**, 0/0/0 over all 9024 shots.
- The 1170 peak is a **9-way co-bind**; value-exact comparator headroom at 1170 is reported
  **exhausted** — further gains need a *structural sub-1170 cut* (open research) or the
  avg-rounding lottery. (jieyilong's q1194 K5 route, score 1,727,106,672, is above this — a
  low-qubit artifact, not score-SOTA.)

## The ladder (submission · q · avg-tof · score · key change)
- 1226 `c20c89b` 1,435,354 1,759,744,004 — low-width stack + re-hunted tail (Teddy Pender 1169-lowqubit branch)
- 1218 `19815a4` 1,402,579 1,708,341,222 — 3 stacked q-descent levers (below)
- 1211 `cac150e` — `DIALOG_GCD_FOLD_PARK_LOW_CARRIES` + `SQUARE_ROW_MAX_SEG` 185→184
- **1203 `833642f`** 1,410,971 1,697,398,113 — **K5 clean-block transcript codec**
- **1193 `ad4cf86`** 1,412,391 1,684,982,463 — **K5 free-clean-block-during-shift**
- 1192 `a7ec174` 1,412,425 1,683,610,600 — `SQUARE_ROW_MAX_SEG` 165 + reroll
- **1185 `3182d2b`** 1,418,587 1,681,025,595 — exact 11-bit head codec + implicit-zero apply
- **1170 `1278a07`** 1,434,999 1,678,948,830 — exact 3-step tail codec + selective per-site repairs
- 1170 `6dd61c5`/`dc6724b`/`65e8bcb` — value-exact cleanup-comparator cuts + budgeted repairs (current best)

## New techniques (not in the pre-1211 skill)

### 1. K5 clean-block transcript codec — K-jump CAN win, *for peak*, via compression
`DIALOG_GCD_K5_CLEAN_BLOCK=1` (`833642f`). Pack **five** K2 GCD steps into a **12-bit clean
block** using a verified **borrowed-ancilla 17-CCX codec** (Claude Fable-5), replacing the
wider K2 pair-block with reversible encode/decode + clean ancilla return.
- **Correction to the earlier "K2 is the sweet spot; K3/Kj are qubit-negative" finding:** that
  held for *uncompressed* extra shift flags (5 + 3·(j−1) bits/block, growing). The real trade is
  **K-depth vs transcript width**, and an information-theoretic codec flips the verdict — K5 at
  ~2.2–2.4 bits/step (12-bit/5-step, or the exact 11-bit codec below) **lowers live transcript
  peak pressure**, which is the peak owner. K5 wins on *peak*, not iteration count.
- `DIALOG_GCD_K5_FREE_CLEAN_BLOCK_DURING_SHIFT=1` (`ad4cf86`): temporarily **free** the clean
  block during the fused double/halve apply shift phases and reacquire it after — removes
  transcript pressure from the *apply binder*, letting `SQUARE_ROW_MAX_SEG`→166 drop peak to
  1193. (Spooky-pebble-style lifecycle hosting applied to the K5 block.)

### 2. Information-theoretic reachable-support codecs (the exact form of round763)
Exhaustively **enumerate the reachable transcript words** and encode in exactly
⌈log₂(#reachable)⌉ bits:
- `3182d2b`: first five K5 steps' 15 raw branch wires → exact **11-bit** codec (exactly **2048**
  reachable words — information-theoretic, not probabilistic). → q1185.
- `1278a07`: exact **three-step tail codec**, reachable support = **32 symbols (5 bits)**,
  streamed without materializing the raw tail. → q1170.
- `65e8bcb`: an "affine299" reachable-support codec variant (current SOTA).
This is the optimal version of the skill's existing 3→5 (round763) heuristic transcript packing.

### 3. Implicit-zero apply — don't allocate a provably-zero bit
`3182d2b`: the chunked apply add/sub was reworked to the **low-to-extended-width Cuccaro**
primitive; the old path materialized the source as `f || 0`, but the high source bit is
**constant zero and no longer occupies a physical qubit**. The Gidney "drop provably-zero bits"
idea applied to the apply chunk — a clean peak saving.

### 4. `SQUARE_ROW_MAX_SEG` — the primary peak-descent knob of this era
The round-84 schoolbook-square row segmentation. Lower = fewer simultaneously-live square rows =
lower peak, paid in a little Toffoli. The ladder walks it **193→191→185→184→176→166→165** as
freed transcript pressure (from K5 / codecs) permits — i.e. transcript compression buys square
segmentation buys peak. Companion comparator: `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS` (19→18,
`6dd61c5`) — the windowed boundary-carry cleanup of the round-84 square; **value-exact** (the
square *product* is always exact; only a boundary carry is governed), −372 Toffoli, peak-neutral;
new soft-mismatch class `SquareCleanupMismatch`.

### 5. q-descent value-exact knobs (peak-neutral or −1/−2 q)
- `DIALOG_GCD_FOLD_PARK_LOW_CARRIES=1` — park the lowest fold carries across the high-limb tail,
  recompute before uncompute (1212→1211).
- `ROUND84_QPROD_VENT_PAD=1` — round-84 Solinas-fold quotient-product vent pad.
- `DIALOG_GCD_FOLD_FREED_TAIL_ED=1` — apply-phase freed-tail y-fold (end-deferred).
- `DIALOG_GCD_APPLY_FINAL_TOPCLEAN=0` — exact-adder recovery on the apply final.

### 6. Budgeted per-site repairs instead of global widening (the 1170-floor meta)
At the floor, don't use one global comparator/fold width — use the **minimum global width +
targeted per-site repairs** chosen by an optimizer under a Toffoli budget:
- `1278a07`: "selective **48-bit compare repairs** while retaining the **46-bit global** compare
  width" + per-step carry-window/carry-parking schedules (most steps at the aggressive 18-bit
  baseline; only empirically-selected failure sites widen to 19/20).
- `65e8bcb`: an execution-weighted **0-1 knapsack** selects **17 one-bit fold-width repairs**
  (each paired with its carry-parking width); a grouped phase-cleanup optimizer selects sparse
  overflow/underflow/square repairs under an **80-Toffoli emitted budget**.
- Soft-mismatch classes the classical filter now models: `SquareCleanupMismatch`,
  `ApplyCleanupMismatch` (region-specific, which is what makes stacking work).

### 7. Stacking independent value-exact cuts under one nonce
`dc6724b`: two value-exact cuts in **disjoint op-stream regions** with independent
soft-mismatch classes (`SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS` 19→18 in the square phase +
`DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS` 20→19 in the apply phase) **stack**: a single
`DIALOG_TAIL_NONCE` whose 9024 inputs are clean under *both* captures both cuts. Method: sweep
for undeployed value-exact cuts, prove region-independence, hunt one nonce clean for all.

## Search-infra note
Frontier hunts run ~**6,000 nonce/s per consumer GPU** (on-GPU SHAKE tail-absorb + windowed comb
for k·G + bit-exact dialog-GCD pre-filter); `c20c89b` explicitly credits **"Jieyi Long's
ecdsafail_gpu_toolkit"** as the GPU search surface. The lowest-q routes (`3182d2b`, `1278a07`,
`65e8bcb`) screen with a **full exact serialized-circuit filter over all 9024 shots per nonce**
("WMI/WMICluster"), not just the GCD pre-filter — far fewer false candidates than a GCD-only
screen, at higher per-nonce cost.

## Provenance
All notes archived in `references/submission-notes/`. Source: `ecdsafail submissions --all`
(547 rows: 323 promoted / 146 rejected / 78 failed) + `ecdsafail submission-note <id>`.
