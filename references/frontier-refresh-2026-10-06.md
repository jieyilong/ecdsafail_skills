# Current evidence and reusable lessons, 2026-10-06

This refresh starts after skills commit `08a60e4f8fafb26363b43a9d206d815e3f7d618a`
at `2026-06-28T19:15:59Z`. The closing official API snapshot contains 586 later
submissions. The per-submission audit records notes, exact candidate/parent SHAs,
diff hashes, official outcomes, and separate current/historical Pareto status.
All 586 have technical reviews of the full available note and active source
changes: 557 exact-parent public diffs and 29 explicit no-public-commit limits.
See the published [audit ledger](https://github.com/jieyilong/ecdsafail_skills/tree/main/audit/2026-10-06).
This is source analysis, not an independent whole-circuit benchmark execution.

## Current product winner

The three resource objectives select different operating points in the pinned
official metric corpus:

| Objective | Submission | Q | Rounded T | Product S |
|---|---|---:|---:|---:|
| Lowest product | `e37cd0c` | 1171 | 946021 | 1107790591 |
| Lowest Toffoli | `ab11959` | 1250 | 888879 | 1111098750 |
| Lowest width, best T at that width | `ae98f36` | 792 | 755617938 | 598449406896 |

The full current nondominated set has 29 submission records, including ties and
four pre-cutoff records. The post-cutoff audit includes 25 of them. A historical
Q792 record with higher T is not the current minimum-width representative.

The closing product winner is submission `e37cd0c`, source
[`05161d3`](https://github.com/Layr-Labs/ecdsafail-challenge/commit/05161d300867edfeec94a4d7fc3edc087e9527d2),
with Q=1171, rounded T=946021, S=1107790591. It spends 686 rounded Toffolis for
one qubit relative to the previous product winner, improving S by 142029.
Its actual Git parent is the prior winner `9db31da9`; the note also credits the
author's Q1173 architectural line and ports the prior winner's shared-pair idea.
Git parent, architectural lineage and current score comparison must be recorded
separately. Read [the closing source
review](refresh-closing.md) for active recipes, rewrite-row proof classes, accuracy
tradeoffs and attribution. The note reports lambda=19.333 +/-0.032 on 16384 fresh
packets: below the stated 19.5 preference at two standard errors, but above the
earlier 18 preference. Neither preference is an all-input correctness theorem.

The immediately preceding product winner is submission `73c5e2a`, source
[`9db31da`](https://github.com/Layr-Labs/ecdsafail-challenge/commit/9db31da9a0971a2185e54d12d9441c36838aba40).
It uses Skywalk at Q=1172 and rounded mean T=945335, giving S=1107932620.
Skywalk's public architecture credit is Matt Zweil and MAI-A.A.E. of the Mochimo
Foundation, building a reversible realization of Stein's established binary-GCD
recurrence. The low-space fixed-schedule EEA lineage credits Han Luo and the
coauthors listed in the submission notes; subsequent local mechanisms are
attributed by their source-linked audit entries.
The exact parent is `e3fd358e6c56c477d8c7378c1987de34d79b9ede`, verified through
GitHub's commit metadata. The parent uses Q=1173 and T=944566. This is a
one-qubit reduction that spends 769 rounded Toffolis and improves S by 43298.
Preserve raw and rounded means separately: the note reports mean 945335.112256
from 8530704053 executed Toffolis over 9024 shots. The official score is Q times
the rounded mean, not Q times the raw mean.

The parent-relative diff contains many executable-bit changes and CRLF/LF
changes. After removing line-ending noise, the substantive changes are in
`heo_carry.rs`, `mod.rs`, the bridge-room profile, and the compiled rewrite table.
The active recipe tightens the cap and several compare/fold windows, enables
`EXACT_PAIR_CARRY`, and uses `cap1172_exact_rows.txt`. Count the active table:
it contains 46 rows, despite an inherited source comment still saying 105.

The note reports 78 outer pair-carry groups and independently replayed clean
9024-shot validation. It also reports a fresh-packet failure-batch estimate
lambda=19.531 +/-0.250 over 256 packets, exceeding the inherited stated limits.
That is a disclosed tradeoff in the note, not an exact accuracy-preserving cap
reduction. A source-identical clean packet, a population accuracy estimate, and
an all-input proof are different forms of evidence. Keep them separate.

## Shared nonlinear witnesses and deferred phase repair

The Q1172 codec reuses a product retained from the walk in a later pair pack.
The pack consumes and measures that product instead of recomputing it. Its
measurement outcome remains in `m_pair`; unpack repairs the resulting phase on
an AND that unpack already needs. `outer_shared`, per-group assertions, and
`all_consumed()` extend the lifetime/cleanup bookkeeping.

The local equations are checked by `scripts/test_shared_pair_codec.py`:
two HL-encoded trits have legal states {(0,0),(0,1),(1,0)}, and the supplied
product wire must hold w=a(1-c)(1-d). The source calls this wire `p`; it is not
the prime field modulus. For all nine legal pairs, the shared pack matches
the ordinary pack's values, and the independent unpack restores the input.
The immediate measurement correction is h XOR(c' AND d'); the deferred product
correction is anc XOR(anc AND b'). All four measurement-outcome pairs leave
zero residual phase. Supplying the wrong product gives a counterexample.

This check establishes the promised-support algebra. It does not establish that
every retained wire in the full emitter has that exact product, that its support
is preserved across intervening cells, or that the whole point-add circuit is
correct. Those are additional source-binding and lifetime obligations.

The transferable technique is to share an already computed nonlinear witness
across adjacent operations and discharge measurement debt at an existing inverse
AND. Track its value, support, producer, consumers, measurement outcome, and exact
repair point. A wire that is cheap to measure is not automatically safe to free.

## Evidence lessons established in the early tranche

- `68f90fe` introduces a deferred-Lehmer wrapper, but its active function calls
  the incumbent TrailMix emitter and its selftest returns success without testing
  arithmetic. Its official metrics tie the incumbent. Do not credit projected
  Lehmer savings as an implemented circuit.
- `78f8c2b` changes only a memory document. It usefully identifies which earlier
  `set_default_env` calls win over later stale recipe blocks. Diagnose effective
  configuration precedence before attributing a knob change to a resource win.
- `608eed4` calls a knob a skipped cswap, but the active replacement mode emits
  the complete CX/CCX/CX cswap. Read the operation sequence, not the knob's name.
- `97f9498` adds an unused dead-Toffoli helper and changes classical-bit static
  analysis from Zero to Unknown. The conservative seeding is a useful soundness
  rule; the unused helper's alleged gate deletion is not an active improvement.
- `c387ef1` changes identity-tail targets and fails the benchmark with no official
  metrics. Even a mathematically identity tail changes the derived corpus and can
  alter width accounting. Do not admit failed claimed points to the clean frontier.

## Validation corrections

For a unitary U, composing its own exact adjoint gives U-dagger U=I even if U
implements the wrong arithmetic or leaves forward scratch entangled. Inspect
scratch at the forward boundary and compare values and relative phases against
an independent specification. For measured uncompute, check the outcome-dependent
channel and corrections, not an assumed unitary adjoint.

No observed zero-error packet in a finite sample does not prove a structural
floor. A positive lower bound derived from an invariant can rule out an island;
finite observations only constrain a probability estimate. Likewise, a no-fire
census is empirical support evidence, not a universal proof that a gate is dead.

## How to use the refreshed playbook

For the Q834 exact Boolean-proof/predicate work, also read
[`refresh-middle-primary.md`](refresh-middle-primary.md). It distinguishes
whole-predicate measurement uncompute, cache precision, shared carry/sum products,
and retention that closes the classical-bit boundary as well as quantum phase.

Select a route family before importing knobs, error models, or GPU prescreens.
The June TrailMix schedules are historical and are not Skywalk parameters.
Rejected submissions with official metrics may be Pareto successes while losing
the product objective. Failed/local-only claims are separate. Compare every
candidate to its actual parent and its architectural predecessor, because a
submission snapshot may reinstall an entire older source tree.

Read the complete architectural timeline in [early](refresh-early.md),
[middle](refresh-middle.md), [middle supplement](refresh-middle-extra.md),
[late](refresh-late.md), [late supplement](refresh-late-extra.md), and
[closing submission](refresh-closing.md). Current values are snapshot facts,
not evergreen records; refresh the official inventory before a new campaign.
