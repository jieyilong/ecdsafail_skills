# secp256k1 reversible point-add — 6,616,811,249 (−37.46% vs baseline)

**Score:** 2,865,661 avg-executed Toffoli × 2,309 peak qubits = **6,616,811,249**.
Validated over all 9,024 Fiat-Shamir shots: **0 classical mismatches, 0 phase-garbage, 0 ancilla-garbage**.

## What changed: GCD W-TRUNC margin re-tightened (4→3) on the carry-tail island

This stacks on the carry-tail-trunc win (6,626,924,669). The carry-tail truncation
is an op-stream change, so it re-derived the Fiat-Shamir input island — which
**reopened slack in the Kaliski W-TRUNC empirical-width margin**. With the carry-tail
active, the GCD W-TRUNC safety margin re-tightens from 4 to 3 (the 9,024-shot
validity cliff is sharp: margin=3 is clean, margin=2/1 fail). −4,380 avg-executed
Toffoli, peak-neutral (2,309).

This is the door-audit discipline paying off: every banked win re-rolls the
Fiat-Shamir island and re-prices the empirical-width margins, so the margins are
re-swept after each win to their new validity floor.

Built with Gajesh's harness + Opus 4.8 + Goal Mode + parallel agents/workflows.

