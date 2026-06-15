## Summary

This submission improves the accepted pair-specific UV-safe Kaliski implementation by replacing two identical-control STEP1 correction Toffolis with one temp-AND plus CX fanout.

Claimed score: `7,754,110,980` = `3,356,758` avg executed Toffoli x `2,310` peak qubits.

## Approach

In the UV-merged Kaliski bulk prefix, the deferred `(u, v_w)` frame requires a STEP1 correction:

`t = frame & (u0 xor v0)`

The previous implementation applied this correction to both `a_f` and `m_i` with two CCX gates sharing the same controls. This change computes `t` once, fans it out with free CX gates, and then measurement-uncomputes `t` with the phase correction `CZ(frame, u0 xor v0)`.

This is a unitary/phase-clean local rewrite. A Python truth table over `frame, u0, v0, a_f, m_i` was used in the isolated worktree before Rust validation.

## Files Changed

- `src/point_add/kaliski_walk.rs`: replaces duplicated STEP1 UV-frame correction CCXs in forward and backward bulk Kaliski with temp-AND fanout, default-on behind `KAL_UV_STEP1_FANOUT`.

## Validation

Local full validation via `./scripts/eval.sh "uv step1 common-and fanout" auto` passed all 9024 Fiat-Shamir shots:

- Classical mismatches: `0`
- Phase-garbage batches: `0`
- Ancilla-garbage batches: `0`
- Avg executed Toffoli: `3,356,758`
- Peak qubits: `2,310`
- Score: `7,754,110,980`

## Tooling

Developed with OpenCode using model `vercel/openai/gpt-5.5`, with isolated worktree subagents, Python truth-table validation for the algebraic identity, and local full validation through the repository's evolve harness.

