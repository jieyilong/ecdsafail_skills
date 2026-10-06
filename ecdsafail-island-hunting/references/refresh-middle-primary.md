<!-- Generated from repository references/refresh-middle-primary.md; source SHA256 06d24f7b666268a105c7adf373e635798c7630add6bca648b545bdd3e2be9a73. Edit the maintained source, then run scripts/sync_shared_references.py. -->

# Primary review: Q834 HIR optimizer, indices 331–334

These four reviews inspect full public notes and active Rust consumers, with
raw-byte patch SHA256 and exact parents bound in `reviews-middle-primary.json`.
They do not execute contestant code or rerun note-reported tests/benchmarks.

## Predicate cleanup instead of generic gate skipping

[`c4bdf3cb`](https://github.com/Layr-Labs/ecdsafail-challenge/commit/8f57ebb6be4370f9ae1c5d86b30231079da4964a)
uses the single-bit measurement-uncompute identity on the final modular-reduction
predicate. The flag must already equal `ctrl AND (accumulator < addend)` on the
canonical-operand interface. The same comparator at subtraction entry computes
that flag and is excluded. `predicate_cleanup` validates the complete 2053-gate
block before HMR and a measurement-conditioned phase comparator, changing only
its output CCX into CZ. Nodes 2262/2265/2267 and their exact offsets yield 1284
dynamic occurrences through the unchanged HIR expansion.

This reduces expected charged work because the phase oracle runs on half the
measurement branches. It is not a sampled dead-control table. The independent
local note tests and its complete trusted packet support different obligations:
the algebraic flag premise, actual source placement, and finite whole-circuit
validation. The parent affine exceptional-case domain remains incomplete.

## Sound compiler precision as a resource lever

[`29957dc2`](https://github.com/Layr-Labs/ecdsafail-challenge/commit/040ae0b23e30e205df863a3e65e6c1feeb289de9)
doubles the exact Boolean-expression cache. `Values::fresh` uses checked monotonic
IDs. Eviction forgets expression definitions without recycling existing IDs or
inventing equality. XOR/AND transfer, classical-condition snapshots, and measured
bit updates remain unchanged. Keeping more identities admits 25927 additional
clean-AND uncomputes at no quantum-width cost. The 25944 rounded official T
change differs because the new hashed stream has different measurement-conditioned
execution. Construction RSS, source counts, expectation, and official T are
separate measurements.

## Shared carry/sum product with an exact zero query

[`5b1a172d`](https://github.com/Layr-Labs/ecdsafail-challenge/commit/46531cc1901c8d80781dae50402234f317838b55)
shares `ctrl*b` between controlled carry and sum updates instead of materializing
`ctrl*a` and recomputing `ctrl*b`. The seven-record forward/inverse signature
checks its phase child, measurement bit, wires and condition structure. The pass
flushes pending operations, queries the existing exact zero proof, and leaves
unknown scratch cases unchanged. The replacement's phase oracle must change to
the shared product. A dirty-scratch counterexample demonstrates that the clean
premise is essential. The source checks local wire distinctness; a generic port
must additionally establish the physical scatter-map alias premise.

The actual default stays at a 1M proof cache, rather than importing the separate
2M successor. All generated operations pass through the ordinary emitter and
proof-transfer path. This is a local interface identity, not a stronger total
point-addition theorem.

## Retention must close the classical boundary too

[`aa33e35a`](https://github.com/Layr-Labs/ecdsafail-challenge/commit/d72fa23b54251a40533148f71ce9d68c41c29d55)
keeps seven prefix products between two uses after exactly restoring their factor
bits. The middle target/control are disjoint from factors and products. The full
65-record, 571-byte fixtures include a surviving HMR/CZ suffix that overwrites
the reused classical bit before any read. The shorter 61-record interval changed
that bit's output despite matching quantum outputs and phase.

Eligibility requires seven exact zero-entry products and rejects aliases among
19 mapped quantum wires. Banks 531 and 540 use the same topology; byte binding,
shifted-map tests, enclosing conditions and dirty-entry negative cases are
inspectable. Removed measurement histories need not consume identical sequential
random bytes: compare the corrected channel with a valid coupling of surviving
outcomes. Unaffected events should be aligned by identity rather than by blind
PRNG offsets.

Official sequence at Q834: T68146334 → 68120390 (cache successor), or
T68146334 → 63935388 → 63883373 (shared product then retention). These are
low-width product-rejected outcomes. Use actual parents as well as this
architectural predecessor chain, because candidate snapshots replace a wider
scalar incumbent with the older low-Q source tree.
