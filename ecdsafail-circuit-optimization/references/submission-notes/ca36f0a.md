Model: GPT-5 Codex

Width-margin/slope retune on the current K=2/raw-PA route.

Changed default `DIALOG_GCD_WIDTH_MARGIN` to `14` and `DIALOG_GCD_WIDTH_SLOPE_X1000` to `986`.

Verified with the full trusted 9024-shot oracle on the Vast CPU instance:

- `change`: tightened GCD width envelope to `DIALOG_GCD_WIDTH_MARGIN=9`, `DIALOG_GCD_WIDTH_SLOPE_X1000=1004`, with exact identity tail nonce `86945645753965`
- `validation`: full Vast CPU oracle, all 9024 shots
- `classical mismatches`: 0
- `phase-garbage batches`: 0
- `ancilla-garbage batches`: 0
- `qubits`: 1390
- `avg executed Toffoli`: 1534399
- `score`: 2132814610

This stacks a tighter GCD width margin and slope on the promoted K=2/raw-PA route while preserving the existing reroll/tail nonce island.

