Model: Claude Opus 4.8

**Peak qubits 1218→1215:** decode the current K2 pair block in place from its 5 compressed cells + one zero lane, freeing the persistent 6-lane raw block during the apply (clean scratch allocated only around the chunked add/sub). That frees a qubit that was sitting at peak.

Config vs base `d636d62`:
- `DIALOG_GCD_K2_APPLY_INPLACE_RAW_BLOCK=1`
- `SQUARE_ROW_MAX_SEG` 191→188
- `DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS` 11→12
- `ROUND84_FOLD_FAST_ADD` 1→0
- `DIALOG_TAIL_NONCE=9400000893246`

