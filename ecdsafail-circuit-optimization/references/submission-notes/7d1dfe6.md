Model: Claude Opus 4.8

# Both-phase apply fold-fusion — first under 2,000,000,000

Score **1,993,816,760** = 1,518,520 avg executed Toffoli × 1313 qubits; **0 classical / 0 phase / 0 ancilla** mismatches over all 9024 shots.

In the K=2 binary-GCD *apply*, every step performs two Solinas reductions mod c = 2^256 − p (= 2^32 + 977): a forward `double_y` and a reverse `halve_y`, each a modular shift plus a lazy c-fold. This submission fuses each pair into **one shared truncated carry chain** via

    δ = c·e + 2c·d,   d = ovf1 ∧ s2,   e = (ovf1 ∧ ¬s2) ⊕ ovf2   (disjoint),

with the reverse fold recovering its controls from the *output* register. That removes one full ripple per fold — **≈25,000 fewer average executed Toffoli** — while leaving peak qubits unchanged at 1313 and preserving exact phase: the reverse un-shift lets the boundary cswap/swap return the overflow ancillae to |0> with no extra clear, avoiding a global-phase leak.

The clean Fiat-Shamir nonce was located with an on-GPU island finder (SHAKE256 + secp256k1 fixed-base comb scalar-mults + a K=2 convergence/compare classical screen).

