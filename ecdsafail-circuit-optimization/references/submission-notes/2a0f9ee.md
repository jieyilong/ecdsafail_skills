Model: GPT-5 Codex

# Active259 follow-up width/apply island

This submission continues the active259 custom-apply frontier. It keeps
the active259 convergence margin and adjusts the apply chunking plus GCD width
parameters to reduce average executed Toffoli while staying below the live
qubit-Toffoli product.

## Circuit knobs

- DIALOG_GCD_ACTIVE_ITERATIONS=259
- DIALOG_GCD_WIDTH_SLOPE_X1000=1009
- KAL_DOUBLE_CARRY_TRUNC_W=22
- KAL_FOLD_CARRY_TRUNC_W=22
- DIALOG_GCD_COMPARE_BITS=47
- DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS=19
- DIALOG_GCD_BODY_CARRY_BAND_TRIMS=0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2
- DIALOG_GCD_APPLY_FINAL_LOWQ=1
- DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS=5
- DIALOG_GCD_APPLY_CHUNKED_F_CUSTOM4=0
- DIALOG_GCD_APPLY_CHUNKED_F_CUSTOM5=1
- DIALOG_GCD_APPLY_BOUNDARY_SPLIT=100
- DIALOG_GCD_APPLY_CHUNKED_F_CUT=50
- DIALOG_GCD_APPLY_CHUNKED_F_CUT2=100
- DIALOG_GCD_APPLY_CHUNKED_F_CUT3=150
- DIALOG_GCD_APPLY_CHUNKED_F_CUT4=200
- DIALOG_TAIL_NONCE=256973122702329

## Result

- qubits: 1320
- average executed Toffoli: 1553327
- score: 2050391640

Before submission, the live best was rechecked and a fresh official
`ecdsafail run` was required to pass all 9024 shots with 0 classical, phase,
and ancilla failures.

Model: GPT-5 Codex.

