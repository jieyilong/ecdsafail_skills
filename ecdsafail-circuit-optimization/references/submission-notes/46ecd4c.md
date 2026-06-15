Model: GPT-5 Codex

# Active259 1322q four-chunk width-slope island

This submission takes the current 1320q apply-teardown frontier and uses a small
qubit/Toffoli tradeoff: keep `ACTIVE_ITERATIONS=259` for verifier density, move
the apply route to a four-chunk layout at `52/104/156`, and tighten the GCD width
slope to recover enough Toffoli that the product still improves.

## Circuit knobs

- `DIALOG_GCD_ACTIVE_ITERATIONS=259`
- `DIALOG_GCD_WIDTH_SLOPE_X1000=1014`
- `KAL_DOUBLE_CARRY_TRUNC_W=22`
- `KAL_FOLD_CARRY_TRUNC_W=22`
- `DIALOG_GCD_COMPARE_BITS=51`
- `DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS=19`
- `DIALOG_GCD_BODY_CARRY_BAND_TRIMS=0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2`
- `DIALOG_GCD_APPLY_FINAL_LOWQ=1`
- `DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS=4`
- `DIALOG_GCD_APPLY_CHUNKED_F_CUSTOM4=1`
- `DIALOG_GCD_APPLY_CHUNKED_F_CUSTOM5=0`
- `DIALOG_GCD_APPLY_BOUNDARY_SPLIT=52`
- `DIALOG_GCD_APPLY_CHUNKED_F_CUT=52`
- `DIALOG_GCD_APPLY_CHUNKED_F_CUT2=104`
- `DIALOG_GCD_APPLY_CHUNKED_F_CUT3=156`
- `DIALOG_GCD_APPLY_CHUNKED_F_CUT4=200`
- `DIALOG_TAIL_NONCE=198702767358738`

## Rationale

The more aggressive active258 routes save more Toffoli at 1320q, but their hard
inputs cluster around GCD convergence at step 259. This route spends two extra
qubits to keep the active259 convergence margin, then uses the four-chunk
apply layout and a tighter width slope to reduce average executed Toffoli.

Relative to the previous promoted best:

| route | qubits | avg Toffoli | score |
|---|---:|---:|---:|
| previous best | 1320 | 1,556,187 | 2,054,166,840 |
| this submission | 1322 | 1,553,445 | 2,053,654,290 |

Net improvement: `512,550` product points.

## Validation

Official `ecdsafail run`:

- tested shots: 9024
- classical mismatches: 0
- phase-garbage batches: 0
- ancilla-garbage batches: 0
- all 9024 shots OK
- qubits: 1322
- average executed Toffoli: 1,553,445
- score: 2,053,654,290

Model: GPT-5 Codex.

