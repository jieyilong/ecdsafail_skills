Model: Claude Opus 4.8

**Peak qubits 1212→1211:** park the lowest-order carry qubits of the fused GCD fold across the high-limb tail and recompute them just before uncompute, removing one qubit from the peak working set during the apply double/halve phase.

Config vs base `8cd8104`:
- `DIALOG_GCD_FOLD_PARK_LOW_CARRIES=1`
- `SQUARE_ROW_MAX_SEG` 185→184
- `DIALOG_TAIL_NONCE=9800070235165`

