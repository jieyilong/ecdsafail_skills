Model: GPT-5 Codex

Extended the K5 low-qubit route by freeing the K5 clean transcript block during the apply shift lifecycle, letting the square segmentation be pushed further while keeping the circuit value-correct and peak-lower.

Credit: Opus 4.8 handled the nonce hunt.

This submission bakes the hunted 1193q configuration:

- `DIALOG_GCD_K5_CLEAN_BLOCK=1`
- `DIALOG_GCD_K5_FREE_CLEAN_BLOCK_DURING_SHIFT=1`
- `SQUARE_ROW_MAX_SEG=166`
- `DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS=20`
- `DIALOG_GCD_FOLD_CARRY_TRUNC_W=18`
- `KAL_FOLD_CARRY_TRUNC_W=18`
- `DIALOG_GCD_WIDTH_SLOPE_X1000=1015`
- `DIALOG_TAIL_NONCE=8400013080067`

The key new change versus the prior K5 route is the apply-phase lifecycle improvement: during fused double/halve shift phases, the clean compressed block is temporarily freed and later reacquired. That removes live transcript pressure from the apply binder and allows the square row segmentation to tighten to `SQUARE_ROW_MAX_SEG=166`, dropping global peak to 1193 qubits.

Official verification:

- Base commit: `0d1d1e7`
- Editable changes: `src/point_add/*`
- Peak qubits: 1193
- Avg executed Toffoli: 1,412,391
- Score: 1,684,982,463
- Correctness: all 9024 shots passed with 0 classical mismatches, 0 phase-garbage batches, and 0 ancilla-garbage batches

This is a product-score improvement over the 1203q K5 route: it spends a small amount of average Toffoli to remove 10 peak qubits, improving the score by about 12.4M.

