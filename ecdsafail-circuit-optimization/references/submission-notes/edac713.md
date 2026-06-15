## Summary

This submission improves the modular point-add implementation with a validated Kaliski `(u, v_w)` CSWAP boundary merge and a retuned clean iteration island.

Claimed score: `7,757,626,800` = `3,358,280` avg executed Toffoli x `2,310` peak qubits.

## Approach

The main algorithmic win extends the existing `(r, s)` CSWAP boundary merge to the Kaliski denominator pair `(u, v_w)` in the early bulk prefix. The identity is:

`cswap(a) * cswap(b) = cswap(a xor b)`

The implementation defers a STEP-9 `(u, v_w)` CSWAP and fuses it with the next iteration's STEP-3 CSWAP. The deferred frame requires correcting early next-iteration logic:

- STEP-1 parity is corrected under the deferred frame.
- STEP-2 comparison is corrected under the deferred frame.
- The merge is restricted to a validated equality-free prefix (`safe_iters = 254`) because the cheap comparator correction is invalid when `u == v_w`.

After porting this into the modular `src/point_add/` layout, a follow-up island sweep found `pair2=397` clean and lower-Toffoli than `pair2=398` on this circuit shape.

## Files Changed

- `src/point_add/kaliski_state.rs`: UV merge flags and safe-prefix default.
- `src/point_add/kaliski_walk.rs`: forward/backward UV CSWAP boundary merge.
- `src/point_add/point_add.rs`: pair2 default retuned to the clean `397` island.

## Validation

Local full validation via `./scripts/eval.sh "modular uv merge safe254 pair2 397" auto` passed all 9024 Fiat-Shamir shots:

- Classical mismatches: `0`
- Phase-garbage batches: `0`
- Ancilla-garbage batches: `0`
- Avg executed Toffoli: `3,358,280`
- Peak qubits: `2,310`
- Score: `7,757,626,800`

## Tooling

Developed with OpenCode using model `vercel/openai/gpt-5.5`, with parallel theory/prototype agents, Python/classical validation for the CSWAP-frame equality edge case, and local full validation through the repository's evolve harness.

