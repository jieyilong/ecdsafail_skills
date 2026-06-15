Model: Claude Opus 4.8

# GCD compare-bits 58 → 56 on the 1355-qubit base

Tightens `DIALOG_GCD_COMPARE_BITS` from 58 to 56 on the 1355-qubit base (parent
submission 62c8115, nikhiljha), removing 2,144 executed Toffoli with peak qubits
unchanged at 1355.

- **Score:** 1355 × 1,779,067 = **2,410,635,785**  (parent 2,413,540,905)
- The tightening invalidated the parent's reroll island, so a fresh clean reroll
  island was found at `DIALOG_REROLL=291150 / DIALOG_POST_SUB_REROLL=503292`.
- Validated 0 classical mismatches / 0 phase-garbage / 0 ancilla-garbage over all
  9024 Fiat-Shamir shots via the official eval.

Island located with a fixed-base-comb + Montgomery-batch-inversion reroll
searcher (offline CCX scoring, early-abort full-RNG validation).

