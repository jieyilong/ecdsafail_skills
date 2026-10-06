<!-- Generated from repository references/refresh-early.md; source SHA256 bd48ae34ad164744cc19f3fef9b7f646ff100244d51f3a05567388534bd087cb. Edit the maintained source, then run scripts/sync_shared_references.py. -->

# Early submission review, indices 0–194

Source inventory is pinned by `audit/2026-10-06/ledger.json`. The separate
merged `reviews.json` is the completion authority: pending rows are not reviewed
merely because a patch has been normalized, indexed, or hashed. No submission
code, evaluator, GPU job, benchmark, or remote mutation was run in this audit.

Transport-byte SHA-256 and text-normalized SHA-256 must be distinguished.
The direct GitHub diffs containing CRLF initially had LF-normalized hashes in
the inventory. The primary has corrected the canonical inventory to raw bytes;
the continuation records retain matching raw transport hashes and actual parents.

## Tested mechanisms and their limits

The active transition at `3616dbf2` is a fixed-depth ping-pong division pair,
injected through the affine shell's division callback, with explicit inverse
coefficient recurrence. The default dispatcher really selects this emitter.
Its product-register Karatsuba square is active despite a stale “dormant” header.
Q1150/T1284776 → Q1321/T952707 is an architectural Q-for-T trade, not a knob
notch. Fixed rounds, signed-width envelopes and truncated repairs remain
approximate; 9,024 clean shots are finite challenge evidence.

The ping-pong width mechanisms are distinct:

- `7e481634`: clear/loan/restore a redundant terminal sign-extension bit.
- `1cd4a7fe`: erase a boundary carry after its next chunk's last use; lazily
  allocate final carry-out; omit carry/borrow low prefixes with Boolean proofs.
- `21a0ba3f`: generalize terminal loans to every non-sign wire of both terminal
  registers; the proof applies to converged ±1 terminal states. Endpoint54→40
  in the same candidate is still a carry truncation, however small its rate.
- `bc7a7926` and `aac98e98`: interleave replay with the forward walk for divide,
  and with walk-back for multiply; budget transient ladders and terminal batches.
- `1c8dfbea`: narrow exact leading chunks create a finer live-ladder menu.
  Full producer-prefix comparison is exact when there is no incoming carry.
- `4b462367`: dedicated exact two-chunk signed walk adders enable a much earlier
  replay checkpoint. Saved capacity can buy wider replay chunks and fewer phase
  repairs instead of only lowering Q.
- `8cd36b2b`: exact two-segment selected-operand fold retires the low ladder
  before allocating the high one, then rematerializes only the full low operand
  for the exact boundary phase predicate.
- `20376453`: synthesize the final carry directly into the top output; reuse
  existing selector/operand wires; clear and reconstruct derived flags; host
  a final borrow on a freshly cleared low output lane; hold the Karatsuba sum
  in an input half that is restored afterwards.

`7b6ad5c2` replaces analytic slopes with an active sampled 700-entry width table.
`792ac703` adds a greedy replacement table and a real opt-out. `5daefc35` enables
index rescaling and a sparse 100-index +1 repair fitted on training draws and
tested on held-out draws. These tables are empirical support envelopes, not
universal width theorems. The consumer and exact full patch hash matter more
than individually reading every table entry.

`c4906041` has active level-2 Karatsuba on the low and sum branches, a sparse
forward round-zero lift, round-one constant-operand fusion, elimination of two
copy carries, a signed replay frame with truncated `SIGNED_REPAIR=22`, and
top-comparator phase factorization. The source explicitly leaves step-down
top-AND skipping OFF: it increased classical failures from80 to86 and can
break self-healing paths. Do not credit that inactive option as the accepted
optimization. The comparator removes construction of a charged AND/carry;
CZ itself was already a free Clifford in this score model.

## Validation and search lessons

Pure phase comparisons can leave the value permutation unchanged while their
truncated predicate corrupts phase. `9dcbdb80` records classical counts staying
flat while deep comparison cuts saturate all141 phase batches. Use separate
classical, phase and ancilla evidence, then estimate conditional confirmation
yield among screen survivors. Adding marginal classical and phase counts as
independent Poisson hazards can grossly overprice search because their events
are correlated.

`ed30a235` uses a partial phase residual score K to ORDER confirmations.
Rejecting every predicted residual loses valid islands: the measurement bit
can suppress it and multiple contributions can cancel. Its predictor omits
chunk sites and therefore cannot certify phase cleanliness. `54ff37e6` calls
its classical filter exact but records7/565 false positives; “exact” must be
qualified by that evidence and by the unavailable external filter source.

`ea70a28f` retires a jump-GCD GPU model after reading the active ping-pong
dispatcher. It records zero false rejects over649,728 walks, explicitly an
empirical observation. A scanner must reproduce all scalar/XOF consumption
before simulator randomness and use the active width table, current defaults,
exact prefix and tail encoding. HEAD, op-count, source/binary hash and CPU/GPU
canaries should fail closed on mismatch.

Nonce-only rows change sample execution cost but remove no arithmetic gates.
The whole stream hash changes with nonce; the repeated assertion in
`4269cf65`/`236fb8d2` that its full digest should remain unchanged is wrong.
Compare body/prefix equality separately and bind the final candidate to its
own full stream digest. `f827b9c2`'s claimed5,000-T nonce spread is explicitly
corrected to about12 in `c4906041`.

## Lineage and source warnings

The actual parent diff and a relevant architectural predecessor are both
required. Many candidates reinstall an older route after a newer promotion.
`d299f28e` loses the general terminal-loan improvement despite claiming SOTA
against an older baseline. `4af5ba19`, `b97d6dce`, `437da725`, `2f4a7d75`,
`792ac703`, `f827b9c2`, `5daefc35` and `c4906041` have materially different
actual parent-relative changes than their narrow historical note headline.
Repeated dead-low removal/restoration is real lineage behavior, not an
arithmetic refutation. Re-price reusable exact mechanisms after replacements.

`68f90fe4` is a deferred-Lehmer wrapper that still calls TrailMix; its selftest
returns success without testing arithmetic. Baseline reproductions and note-only
commits count for coverage but demonstrate no new circuit mechanism.

`dcbafc56` applies a2101-entry positional CCX deletion set. The consumer checks
gate kind, which catches some misalignment but not a wrong same-kind gate.
A1e8-input zero-firing census is empirical; it does not prove all-input deadness.
The earlier TrailMix census/identity lineage and low-Q EEA/paper2607 block have
now been reviewed. Per-row limitations remain essential: reviewed does not mean
universally correct, reproducible from every named external tool, or promoted.

## Coherent EEA stream cases reviewed

`da67bfe3` actively selects a source-live fixed1,616step EEA. The Rust decoder
lowers packed records into real primitives; its count stub requires explicit
count-only mode and is inactive in the official emission path. Forward and
reverse chunk order restore the EEA input around canonical multiplication.
The supplied certificate's404 quotient-bit bound was not independently
reproved in this read-only audit. Boundary/sample checks and a clean official
packet must not be expanded into a proof for every input.

`7e3b02a9` fixes the physical-wire issue by lending a canonical zero extension
lane without retaining its old ID; a fresh zero lane is allocated on restore,
while the256 ABI data wires retain identity. A Drop guard rejects unmatched
loans. This closes official838→837, despite both prior and new notes predicting
837 live wires. `c703ee07` moves the T-tail predicate and lower borrow/carry
capture into the arithmetic midpoint, sharing a prepared endpoint and unary
path; the selected T-sub/T-add generator calls and paired cleanup are active.

Coverage:195 reviewed,0 pending,195 total. The original106 mechanism reviews were
preserved; this continuation completed89. Full notes, actual active code and
appropriate lineage comparisons were reviewed before status changed. Source
hash/product checks in batches of at most20 are integrity checks, not substitutes
for that work. No submission code was executed.

## Earlier TrailMix: schedule geometry, exact closure, empirical roots

The scoped top22 carry-comparison route exempts the first24 calls because small
Bezout operands need different semantics. Changing ITERS258→261 renumbers
sequential call schedules: stale ordinal certificates must retire, schedule
blocks must be refit, and width/compare schedules must move together. The cap
sweeps sometimes increase Q to buy T; an advertised cap is not the measured
physical peak. A later default can be inert if an earlier default already set
the environment variable. These are real effective-configuration obligations,
not merely nominal knob values.

Several candidates roll back or restore previous exact passes while publishing
only a new census/nonce headline. `0c7f6650`'s branch loses earlier post-strip
fanout; `96c3b0dd` restores the older Q1152 route. The `NORMALIZER_OPS`
CCX→CX edit in `604741ed` is executable even though its brief note omits it.
Credit mechanisms against their architectural predecessors AND actual parents.
The JSON stores the exact source-bound comparisons.

Post-strip exact fanout closure, shared product retention/rebinding and affine
bridges are useful independently of the empirical deletions that expose them.
Cascade cancellation is different: its blocked-pair residual is a three-control
product admitted under measured nonzero risk. Exact descendants do not make
those initial roots exact. Census zero observations, zero stale keys, and one
closed abstract domain do not prove global deadness or an optimization floor.

The later literal affine windows become shape matchers. Reusing the generalized
second bridge requires stronger alias/context guards: its phase0 fanouts do not
exclude the wire that is subsequently chosen as D. That weakens the claimed
generic exactness, although it does not by itself falsify the unique production
window. The Q1150 positional mask checks counts, indices and downgrade gate
kinds, but deletions have no full operation-signature check. Same-length semantic
drift can pass; authenticate the entire parent stream before applying an index
mask. See the [mask consumer](https://github.com/Layr-Labs/ecdsafail-challenge/blob/31f9c58c/src/point_add/mod.rs).

## Low-Q EEA: support-qualified lifetimes and physical sentinels

The Q824 register-shared predecessor hosts a remainder scratch pair in l_q[5]
and t-prime while keeping known-bad coefficient hosting disabled. Q822 dirty
coefficient fusion is a distinct route: local64/9024 results must not override
official failures without metrics. Source-side streaming solves construction
memory pressure but does not remove the evaluator's operation-count cap.

The coherent paper2607 progression shrinks the auxiliary pool from12 through1.
Every co-binding family—R, LC, T-sub, T-add, shift/phase and terminal—must fit;
lowering only a declared constant is not a qubit result. Raw final decoder
levels and restored dirty ladders spend T to buy clean width. Clean-HMR C3X,
exact scan fusion, coordinate orientation and clean-lifetime reuse recover T.
Its packed marker expands to four emitted operations and two Toffolis: replacing
one serialized marker adds three operations, not a three-operation expansion.

Several bounded verifiers missed the actual physical support. High labels
256..259 alias low labels if bit8 is omitted; leaf order matters even on inactive
range-control branches. Phase-B semantic zero is physical l_q=511, not0. The
first Q814 portfolio omitted that reachable step5 endpoint and failed every
trusted shot. Its repair stores the full Phase2 information in Mode. Q813 then
packs exactly256 transformed boundary labels3..258 into eight bits and stores
Iter in the freed high bit; arithmetic labels2/259 remain, but their quotient
equalities must be excluded. See the [Q813 codec source](https://github.com/Layr-Labs/ecdsafail-challenge/blob/364b0429/src/point_add/trailmix_port/inversion/paper2607_data/eea_circuit_s835_exactwidth_dirty12.py).

The Phase2/Iter packing loans exclude certain weight256 endpoints and therefore
need the exact schedule invariant, not an all-basis claim. Outside an active
write window is NOT clean: Work1[0]/Work1[258] lender attempts failed. Generic
one-clean MCX requires a genuinely zero helper. The conditional-zero T-add
pattern is a separate guard-specific identity whose last target action retains
that guard. Do not substitute one contract for the other.

Q815's stable copied carry permits a two-map commutator instead of a four-map
dirty-passenger sandwich. Copy the state that must survive into a certified
clean lifetime, keep it untouched across the dirty map, then uncompute it.
Q818's LC carry/path overlap and direction-select/apply/unselect are additional
exact local levers, not free reductions of every architecture.

The Q819 submission `63470daa` ships transformed primitive shards but a stale
Python generator. Its first decoded shard confirms the clean-helper carry/MCX
ladder mechanism; its complete historical generator/transformer is unavailable
in that snapshot. The later independently reconstructed implementations supply
transferable source, but do not retrospectively establish deterministic
regeneration of the old artifact. Compression-only retries preserve decoded
operation identity, not container hashes; generic server failures do not locate
OOM, timeout or circuit mismatch.

## Small exact passes and deliberate approximation

Q824/Q823 adjacent-CCX cancellation uses complete operation equality and non-CCX
barriers; CCX/CCZ sibling passes use the same involution rule. Fresh draw binding
is required even with no tuned nonce: the Q823 note's “unchanged hash island”
claim is false. Also, CANCEL_ADJACENT_CCX=0 disables the streaming pass but not
the unconditional memory postpass; source-default metrics work, override parity
needs a guard. The [Q973 CLZ fusion](https://github.com/Layr-Labs/ecdsafail-challenge/blob/098ea4ad/src/point_add/trailmix_port/inversion/shrunken_pz_state_machine.rs)
retains A's deposited length across two uses, but inverse deposit must occur
after controlled-add restoration. An early order error failed all9024 shots.

The Q824 bitmap deletion route (`9467668c`) explicitly spends empirical risk.
Its64-bit FNV tripwire hashes only the CCX/CCZ subsequence; Clifford or condition-
stack changes can alter semantics without changing that fingerprint. The bitmap
representation scales efficiently, but fingerprints and occupancy are alignment
checks, not deadness proofs.13/13 clean base redraws do not establish universal
exactness. A natural unappended admission size still selects a transcript; it
does not eliminate selection across tested dose/configuration arms.

The subsequent raw-rfold port (`72813aaf`) is NOT source-proven exact boundary
hoisting: the actual diff merely swaps five canonical multiply/undo calls for
raw variants and adds no reduceF/reduceR boundaries. The active module labels
raw output “rfold-approximate; may be ≥p” and relies on canonical intermediate
preconditions.9024 clean shots cannot supply the omitted range/inverse theorem.
See [raw versus canonical multiplication](https://github.com/Layr-Labs/ecdsafail-challenge/blob/6807eafc/src/point_add/trailmix_port/rfold_mbu.rs).

Q888/Q999 padding is deliberately dominated novelty, not frontier progress.
Q973 has much better scalar score thanQ824 but higher Q, so it does not
Pareto-dominateQ824. Relaxing Q1133's four late trims buys T atQ1134; the scanner
must distinguish selective state widths from default-mode comparator windows.
A known-clean fixture caught a wrong dump format that internal parity probes
missed. Negative34.2M nonce search and local sweeps are not impossibility proofs.

## Q813 exact conjugation stages

Three pinned CCX/CX/CCX target-fanout windows become12,904 guarded windows across
all36 shards, then577,629 bounded commuting-gap X-control conjugations, then
244,108 newly exposed control-CX conjugations. These are actual active emitter
passes, not merely a census. The last two require identical outer CCX, one
noncommuting blocker, every other intervening gate individually commuting with
that outer gate, distinct support, greedy disjoint intervals, expected per-shard
counts, and exact reverse emission. The local permutation equalities preserve
arbitrary superpositions/relative phases without ancillas. See the
[three-stage matcher](https://github.com/Layr-Labs/ecdsafail-challenge/blob/1b50b581/src/point_add/trailmix_port/inversion/paper2607_eea.rs).

A catalogue fixed point is relative to its rules/neighborhood, not a universal
synthesis floor. The notes correctly disclose fresh baseline replay using an
unconfined developer fallback and no fresh local whole modified-candidate replay.
Official resource points remain distinct from promotion and global correctness.

Further inspection priorities: generic affine guards (124), positional parent
authentication (125), stale generator/reducer provenance (76/81), sentinel-domain
induction (80/82/94/95), raw-rfold exactness claim (107), and full packet receipt
scope for the exact Q813 successors (173/174/175/177). These are limitations of
reviewed cases, not uncovered rows.
