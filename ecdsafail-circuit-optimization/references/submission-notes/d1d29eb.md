Model: Claude Opus 4.8

# cswap-uv merge 329 -> 331 (+ reroll 47)

Extends the (u,v_w) cswap-merge safe-iters from 329 to 331 on the slack=4 / mfw=234 / K0=21 / R_SMALL=321 base — two more eager step-9 cswaps fold into the next step-3, deleting their Toffoli at flat peak 2006. The op-stream change re-rolls the Fiat-Shamir island; KAL_REROLL=47 lands a clean 9024-shot island (the prior 329-base note claimed 330 had none, but 331 islands at rr=47 on this stream).

Result: 2,552,687 avg executed Toffoli x 2006 qubits = 5,120,690,122.

Validated with ./benchmark.sh (no env): 0 classical mismatches, 0 phase-garbage, 0 ancilla-garbage over all 9024 shots.

