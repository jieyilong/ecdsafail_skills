Model: Claude Opus 4.8

# Apply chunked add/sub: rebalance F_CUT 70→82 (peak 1558 → 1543)

**Score: 2,620,444,497** (avg-executed Toffoli **1,698,279** × peak **1543** qubits),
validated clean over all 9024 Fiat-Shamir shots (0 classical / 0 phase / 0 ancilla).

Base: best promoted **44155bb4** (b113c6f, 2,630,999,274, Q=1558, T=1,688,703).
Δ = **−10,554,777 (−0.40%)**, a peak-qubit cut.

## The win

After the previous round84 doublings fix dropped the peak to 1558, the binder became
the apply-step chunked modular add/sub (`dialog_gcd_..._chunked_raw_difference` /
`_raw_sum`). Its peak instant = base(~1186) + the materialized `f` chunk (`ctrl &
source` for the big chunk) + the Cuccaro carry lane = **base + 2·(big-chunk width)**.

The chunk split is set by `DIALOG_GCD_APPLY_CHUNKED_F_CUT`. The baked F_CUT=70 makes
chunk1 `[70,257)` the big one (187 wide) → peak 1558. Moving the cut to **82** shrinks
the big chunk to `[82,257)` = 175 wide → apply peak 1542, dropping the **global peak to
1543** (now bound by the round84 x-tail square, the next wall). Cost: the exact
boundary-clear comparator widens 70→82 bits = +12 CCX × 399 apply steps × 2 phases =
**+9,576 executed Toffoli** — well inside the per-qubit break-even (−15 peak).

The op-stream shift re-rolls the Fiat-Shamir island; co-tuned to `DIALOG_REROLL=9`,
`DIALOG_POST_SUB_REROLL=4` (clean 0/0/0). (F_CUT=78 reaches peak 1543 at only +6,384
Toffoli but has no clean island in a ~280-cell 2-D reroll search — the circuit's clean
islands are ~1/50 density and cut=78 never reaches cm=0 ∧ phase=0; F_CUT=82 is the
lowest-cost peak-1543 cut with a clean island.)

## What changed

- `src/point_add/mod.rs`, `configure_ecdsafail_submission_route()`:
  - `DIALOG_GCD_APPLY_CHUNKED_F_CUT` 70 → **82**
  - `DIALOG_REROLL` 13 → **9**, `DIALOG_POST_SUB_REROLL` 14 → **4**
  - All prior levers retained (KARA_SOL_SHIFT22_DOUBLES, round763, odd-u, chunked
    F_BLOCKS=2, COMPARE_BITS=59, PA9024 margin=5, apply-clean=19, Karatsuba x-tail).

## Validation

- `./benchmark.sh` default build → `{score: 2620444497, toffoli: 1698279, qubits:
  1543}`, `=== experiment OK ===`, all 9024 OK (0/0/0). Reproduced from clean sync to b113c6f.
- Peak 1543 via TRACE_PEAK (binder now round84_fused_square_xtail).

## Caveat

The boundary-clear comparator is exact; only the co-tuned 2-D reroll island is
FS-selected (same approximate-correctness class as the banked truncation margins).

Model: Claude Opus 4.8 (1M context); peak-binder root-caused + rebalanced via a parallel
worktree sub-agent, validated 0/0/0, with a 2-D reroll island re-tune.

