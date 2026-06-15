# ECDSA Fail submission note

This submission improves the promoted baseline by combining three validated changes in
`src/point_add/mod.rs`:

- Keep the low-qubit shift-by-22 Solinas path by default, but use the
  measurement-uncomputed fast Cuccaro form only for the forward `pos=32`
  sub-add. The symmetric fast path was not valid in the full harness, but the
  forward-only `pos=32` case stayed under the existing 2708-qubit peak and
  validated cleanly.
- Lower the normal pair2 Kaliski iteration count from 398 to 397. This was
  phase-fragile on the prior circuit hash, but with the forward `pos=32`
  shift22 change the fixed benchmark harness validates it cleanly.
- Route single offset-bit modular adds through a bit-register-aware adder by
  default (`POINT_ADD_BITREG_OFFSETS`, opt-out with `=0`). This avoids
  materializing the classical offset addend as qubits for `mod_add_qb`, using
  classically-conditioned carry propagation and phase-correct measurement
  cleanup instead. Only the add path is enabled; sub/double offset variants
  were probed separately and were not phase/correctness clean.

Official local benchmark command:

```text
./benchmark.sh --note default-bitreg-offset-add-official-validation
```

Result:

```text
avg executed Toffoli  : 3541837.000
avg executed Clifford : 21097198.273
emitted ops           : 26599864
qubits                : 2708
score                 : 9591294596
```

The run completed all 9024 correctness shots with zero classical mismatches,
zero phase-garbage batches, and zero ancilla-garbage batches.

Work was done with GPT-5 Codex as the coding agent, using the local
`ecdsafail` CLI and benchmark harness. Additional isolated sub-agent searches
tested Kaliski/inversion and arithmetic/reduction variants; only the clean
bit-register add-offset patch from that search is included here.

