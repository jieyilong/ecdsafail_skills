Model: Claude Opus 4.8

Extends the peak-1302 route's apply schedule.

**Config delta**
- `DIALOG_GCD_BODY_CARRY_BAND_TRIMS = 0,3,3,3,3,3,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,3,3`
- `DIALOG_GCD_FUSED_OVFCLEAR_MEASURED = 1` (measured overflow-clear in the apply)
- `DIALOG_GCD_APPLY_CHUNKED_F_CUT4 = 189`
- `DIALOG_GCD_COMPARE_BITS = 48`, `DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS = 18`

Together these reduce the average executed Toffoli count to **1,456,963** while holding the peak at **1302 qubits**, for a score of **1,896,965,826**. All 9024 benchmark shots validate clean (0 classical / 0 phase / 0 ancilla).

