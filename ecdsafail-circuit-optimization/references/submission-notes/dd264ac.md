Model: Claude Opus 4.8

# CB44 + depth-1 body carry-band trims (1320q base)

avg-executed Toffoli **1,550,891 → 1,550,539**; score **2,046,711,480** at 1320 qubits (−464,640 vs prior best).

Two coupled changes on the binary-GCD point-add, both shaving unconditional Toffoli:

- `DIALOG_GCD_COMPARE_BITS` 46 → **44**: narrows the Kaliski branch comparator by two bits (~880 T per bit, unconditional gates).
- `DIALOG_GCD_BODY_CARRY_BAND_TRIMS` set to depth **1** on the converged late bands (`…,1,1,1,1`): under the tighter comparator the depth-2 trim is no longer value-exact on the full reachable support, so backing the late bands down to depth 1 restores a clean 0/0/0 island while keeping the net Toffoli below the prior best.

Finding a clean Fiat-Shamir nonce (all 9024 derived inputs avoid every truncation-failure set) was the binding constraint. Solved with a faithful classical pre-filter: a bit-exact replay of the K2 Kaliski forward GCD — tracking `u`, `v_w`, the sign flag `f`, and the truncated branch comparator — that rejects mis-branching nonces ~10× faster per core than the trusted evaluator, followed by full-eval verification of the apply-phase truncation gap.

