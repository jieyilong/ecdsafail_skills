## Summary

This submission improves the modular UV CSWAP merge by making the safe-prefix limit pair-specific.

Claimed score: `7,756,453,320` = `3,357,772` avg executed Toffoli x `2,310` peak qubits.

## Approach

The previously accepted implementation uses a Kaliski `(u, v_w)` CSWAP boundary merge in the equality-free bulk prefix. The global safe prefix was `254` because `255` fails on one of the two Kaliski pairs.

This change makes the UV-safe prefix tunable per pair and per direction. A validation sweep found:

- Pair1 safe prefix `255` is invalid.
- Pair2 safe prefix `255` is clean.
- Defaulting Pair1 to `254` and Pair2 to `255` saves one additional 256-wide UV CSWAP boundary on pair2.

## Files Changed

- `src/point_add/kaliski_state.rs`: adds pair/direction-specific UV safe caps and environment overrides.
- `src/point_add/kaliski_inv.rs`: passes pair-specific UV caps into bulk Kaliski forward/backward.
- `src/point_add/kaliski_walk.rs`: accepts a per-call UV safe cap instead of using one global value.

## Validation

Local full validation via `./scripts/eval.sh "pair-specific uv safe pair2 255" auto` passed all 9024 Fiat-Shamir shots:

- Classical mismatches: `0`
- Phase-garbage batches: `0`
- Ancilla-garbage batches: `0`
- Avg executed Toffoli: `3,357,772`
- Peak qubits: `2,310`
- Score: `7,756,453,320`

## Tooling

Developed with OpenCode using model `vercel/openai/gpt-5.5`, with isolated worktree subagents, Python/theory validation for the UV-frame equality boundary, and local full validation through the repository's evolve harness.

