# Independent forward-use audit of the seven refreshed skills

Reviewed 2026-10-06, ending 04:13 UTC. Verdict: the current circuit/island entrypoints and the strict score gate are substantially improved and usable; several contradictory retained instructions and one missing portable checker need correction before publication. This is an artifact audit, not a new circuit benchmark or a proof of submission correctness.

I read all seven actual `SKILL.md` files completely, the shared October reference, the portable middle/late mechanism references relevant to the scenarios, the Q834 primary supplement, the score helper/tests, the tiny codec checker's source, the runtime-model source and the bundle builder's resource selection. I checked Markdown local targets in every package: zero missing targets. I did not run benchmark/GPU/submission code or mutate skills. Only the authored score helper and its tests were executed.

## 1. Source-changed stream, paired nonce counts, and a claimed exact skip

The circuit/island entrypoints provide the right immediate advice: changed bytes mean a changed Fiat–Shamir corpus even at the same nonce; explicit matched inputs and aligned logical measurement events are required for a differential claim. The validation skill correctly distinguishes outcome-wise channel/instrument equivalence from blindly preserving sequential PRNG positions. It also rejects `U†U=I` as a forward specification test and separates final phase debt from a partial-prefix syndrome.

This is actionable: freeze both operation streams and recipes, identify the skip's actual emitter, compare full values/phase/scratch on explicitly fixed inputs, preserve holdout samples, and independently qualify the new native packet. Equal totals cannot establish equality of failure sets or prove a dead control. Source-bound tuple placement is not a reachable-state relation proof.

However, following the entire Toffoli skill still yields contradictory advice:

- **P1 — quantum fire frequency incorrectly becomes executed cost.** `toffoli-reduction/SKILL.md:65` correctly prices the classical condition mask, but its retained Lever E at lines413–418 says a quantum control known zero removes executed Toffoli with unchanged emitted count. In the benchmark, unconditional CCX remains charged regardless of the sampled quantum controls. A valid measured predicate and corrected conditional channel, or an actual semantic gate deletion, is needed. This conflict directly misprices the scenario's claimed skip. Replace Lever E with those two distinct mechanisms and their obligations.
- **P1 — generic measurement repair is advertised as zero Toffoli.** Lines386–391 and438–445 imply that HMR followed by predicate replay is always zero/near-zero T. That is true for an available quadratic phase such as an AND's CZ, not an arbitrary comparison predicate. The Q834 portable supplement itself describes a whole 2,053-gate predicate oracle run on half the measurement branches, not free repair. Price the actual phase oracle and classical branch weight; explicitly restrict zero-T statements to a proved Clifford phase function.
- **P1 — generated evidence can be discarded before inspecting its consumer.** `benchmark-frontier-archaeology/SKILL.md:76` says to ignore generated files. Compiled envelopes, rewrite rows and HIR shards can be the entire submitted implementation change. Retain generated executable/data artifacts and distinguish them from irrelevant build output. The same skill's later instruction to inspect tables cannot repair evidence already filtered out.

## 2. Next route for a low-Q Pareto objective

The portable references support a useful conditional route choice, rather than importing the Q1172 product winner's knobs everywhere:

| Objective/domain | Candidate route | Required next evidence |
|---|---|---|
| Absolute smallest published Q | Q792 fixed-schedule EEA, `ae98f36` | Pay real chart adapters/routing and donor restoration; bind secp256k1 residue/product-width assumptions; official755,617,938T is enormous but product rejection is not a width failure. |
| About833–834Q, exact local optimizer work | Q833 physical HIR coalescing or Q834 Boolean/predicate pipeline | Prove cross-role lifetime zero and scatter-map aliases, retain ABI unknowns and classical-condition snapshots, preserve surviving classical writes, bind byte/graph certificates. Do not use direct-gate alias census alone. |
| More width available for much lower T | Q1072 integer-cofactor Skywalk, `57aa8ae` | Pay history decoding, six product directions, coordinate HMR reconstruction and exact measured-value phase debt; recheck square/fusion interface compatibility. Official2,791,974T is not the global product winner. |

For a minimum-Q user I would start from the Q792 producer/consumer interface; for an834Q budget with cost optimization I would first profile the Q834 proof/cleanup pipeline, comparing it to a source-identical Q833 route rather than guessing dominance. For a1072Q allowance I would evaluate the cofactor route's product/phase cost. The references explain why these are different families. They do not supply a complete sortable portable Pareto dataset, so exact Q833-versus-Q834 cost ranking must come from the current official inventory, as the entrypoint instructs.

The Q834 supplement is particularly good: it identifies canonical predicate premises, immutable proof IDs, unknown-scratch fallback, a dirty-entry counterexample, mapped-wire alias obligations and the surviving HMR/CZ suffix needed to close the classical-bit interface. The Q833 late reference states that physical coalescing's census is necessary but insufficient; the Q1072 reference states that approximate product reconstruction cannot automatically pay exact HMR phase debt.

Remaining misleading guidance:

- **P1 — structural width edits are not all-or-nothing failures on nearly every input.** `peak-qubit-reduction/SKILL.md:97–108` makes that assertion and forbids a graded diagnostic ladder. A wrong alias/support or missing rare terminal case can fail only a small subset. Conversely a deliberate numerical width cut is an approximation even if implemented as a structural edit. Require local promised-domain correctness and lifetime proofs; diagnose finite failures without claiming their frequency is binary. This matters directly for Q833 coalescing and Q792 short-word exceptions.
- **P2 — live allocation is not always the scored physical width.** Peak skill lines48–59 and143–156 equate the metric with maximum live count and imply it can be recovered from the operation list without an allocation contract. The portable middle reference correctly distinguishes allocator live peak from maximum referenced qubit ID plus one. Require both: lifetime accounting for diagnosis and actual emitted physical IDs/allocator reuse for score qualification. A lifetime hole with no physical-ID reuse need not lower benchmark Q.
- **P2 — the old-current labels persist.** Peak lines474–476 and Toffoli lines302–304 still call June's1159Q TrailMix line current/live. Their new opening historical warning helps, but a reader routed directly to that section receives contradictory currentness. Rename every retained section/body claim historical-as-of-June; avoid describing narrower cap changes as automatically lowering Q by one.
- **P2 — knob transfer is overbroad.** Archaeology line163 says structural knobs port directly. The actual Q792/Q834/cofactor descriptions show that they transfer only after interface/support/lifetime/cost obligations are re-established. Change the classification from directly portable to reusable hypothesis with a specified port contract.

## 3. Strict score helper at Q1172

Executed the actual portable helper from the circuit skill's directory, plus `python3 -m unittest scripts/test_score_gate.py` from the repository. Three tests passed. Results:

| Incumbent | Q | Candidate rounded T | Candidate score | Strict win / margin |
|---:|---:|---:|---:|---|
| 1107975918 | 1172 | 945335 | 1107932620 | true /43298 |
| 1107975918 | 1172 | 945371 | 1107974812 | true /1106 |
| 1107975918 | 1172 | 945372 | 1107975984 | false /−66 |

The integer bound `(S0−1)//Q = 945371` is correct and excludes equality. It accepts an already-rounded positive T, does not silently use Python's rounding of an unrounded mean, and reports the real product/margin. No mathematical fix needed. Specify the skill directory as the command's working directory, or provide its resolved script path: `scripts/score_gate.py` is absent at repository root, where a reader may otherwise run the displayed command.

## 4. Tiny measured product/codec before full adoption

The October reference and validation skill give the right separation: enumerate legal support and all HMR outcomes; compare forward values and relative phase against an independent specification; inspect clean scratch before reset; restore arbitrary borrowed passengers rather than assuming zero; then bind the actual producer, lifetime and source consumer. Only after these local obligations should the whole native point-add packet qualify the adopted source.

I inspected `scripts/test_shared_pair_codec.py` without executing it. It has the legal nine HL pairs, four outcome pairs, ordinary-pack comparison, independent inverse, both phase equations and a wrong-product negative case. Its documented support is correctly narrower than the emitter: it does not prove every retained carry has the supplied product or that intervening operations preserve it. This is a useful small algebraic test, not a full gate-level/instrument simulation or universal point-add test.

- **P1 — the cited checker is not portable.** Every skill's October reference names `scripts/test_shared_pair_codec.py`, but none of the seven skill directories contains it. The bundle builder selects skill-local resources and explicit extras; this root checker is not selected. The checker exists only in repository development scripts. Copy it into an appropriate routed skill resource, or explicitly preserve it as a bundled extra and explain how to materialize/run it. A text claim that it was checked is not a usable portable validation artifact.
- **P2 — restore promised state, not zero for every scratch wire.** Validation line89 requires every ancilla to return to zero, contradicting borrowed dirty-lender protocols discussed in the other skills. Owned clean scratch must return to zero; arbitrary borrowed registers, possibly entangled with spectators, must implement identity on the borrowed interface. Add this distinction to the actual per-channel test instructions.
- **P2 — sample-zero occurrence is not necessary for an out-of-sample clean packet.** Validation lines135–154 still labels each channel reaching zero somewhere in the finite panel a necessary condition. A rare reachable jointly-clean packet may simply be absent from that panel. Keep this as a diagnostic heuristic; a genuinely necessary condition concerns the candidate domain, not sampled observations. The adjacent finite-sample caveat does not make the stated necessity valid.

## Portable resources and runtime helper

All Markdown local links resolve in the current directories. Historical references remain available, and the bundle builder preserves selected UTF-8 files with hashes and fences rather than deleting large resources. The circuit score helper is self-contained and the island runtime helper imports only the Python standard library. Development tests are not automatically portable; the codec checker is the concrete missing dependency above.

Static inspection of `ecdsafail-island-hunting/scripts/island_runtime_model.py` found two output claims stronger than the refreshed entrypoint allows: `funnel_from_counts` calls ancilla deterministically zero after a finite all-zero panel (lines134–137), and the ordinary panel output labels no observed phase/ancilla leaks an independent-mode/subset conclusion (lines210–215). Replace these with observed-zero/observed-leak descriptions and confidence limitations. Its marginal fallback explicitly assumes independence when the conditioning subset is too small; preserve that warning for every fallback channel. The two-stage d*q formula is usable only if d is the actual screen-pass rate and q measures full C/P/A success conditional on that pass, not merely a presumed GCD-classical event. I did not execute this helper.

The portable October reference still says complete review is in progress, and the portable middle/late checkpoints still describe pending delegated portions. That is honest at this review snapshot, but must be reconciled with the final merged coverage before publication. Root and copied references have different contents; rerun reference synchronization and rebuild bundles after the review merge/fixes, then audit those actual outputs rather than assuming a previous bundle remains current.

## Readiness decision

Publish only after the P1 contradictions and missing codec resource are fixed, P2 sample/borrowed-state/currentness language is corrected, references are synchronized to the actual merged coverage, and the score helper is rerun from the documented portable path. A fresh semantic forward-use audit should check the corrected entire instructions, not only matching phrases or links. The numerical score boundary and the new source/measurement/certificate distinctions already pass this audit; full circuit correctness and runtime-model calibration remain outside its scope.

Read SKILL.md SHA256 snapshot:

```text
benchmark-frontier-archaeology 17d72b066c45c1a5f5dc26542353c5de7a4920d2c3e3c235fc83fc5c10f6f36f
ecdsafail-circuit-optimization fea33fe13394631c1903178309a80747b54fe00e89c918b39f2ac4783f897b09
ecdsafail-island-hunting 445307146f96211feb216659c51a17045f8c8b7a5ac30cf4b8c5486c419ef2b7
ecdsafail-multi-agent-collaboration 3c473f7cb59298e16f8bd33b8e41e475a823e7be621b3d8fd42f8243869acb4a
peak-qubit-reduction 73c06004475cd05ec7d1f1129aeaefccca543ba032fdae20dbf9365d0e5093d2
reversible-circuit-validation 53be9891015a2fb8b5bad9719300b507cd7b178384f166985320df7894761870
toffoli-reduction d84aded8c6f6a2ddb5a6157ed43aaac0f26ecd9edde6ddf614965c04eb69cfeb
```

## Fresh resolution recheck — 04:23 UTC

The major technical corrections pass the scenario-level recheck:

- The new100-line canonical Toffoli core charges the classical condition mask, distinguishes quadratic AND/CZ cleanup from a potentially non-Clifford whole-predicate phase oracle, requires full quantum/classical interfaces for sharing and cancellation, and prices measurement/feed-forward separately. The old catalogue is explicitly archived and its erroneous pricing/free-predicate claims explicitly noncanonical. A researcher can no longer infer a Toffoli saving merely from a sampled zero quantum control or a free comparator from HMR.
- Archaeology now retains generated runtime envelopes/tables/HIR shards and verifies their consumers/provenance; it also distinguishes a reusable mechanism from a proved portable port. This permits the source-bound Q792/Q834/cofactor choice without discarding the actual implementation evidence.
- Peak's main failure-mode instructions now admit rare structural support/lifetime failures, require local invariant and full-boundary checks, and distinguish live occupancy from the actual scored emitted physical IDs. It now permits coherent or properly corrected measurement clearing and requires arbitrary borrowed-state restoration. An occupancy reduction alone is no longer presented as an official Q reduction.
- Validation now requires identity on dirty borrowed state, including spectator entanglement, and prohibits testing arbitrary borrowed data by reset/measurement. Sampled channel zeros are correctly a heuristic rather than a necessary observation for an unseen rare clean packet. Event/channel coupling and forward-boundary checks remain intact.
- The score example now specifies the skill directory/resolved path. The score helper's3 tests pass again; its strict integer threshold remains945371 at Q1172 for incumbent1107975918.
- All seven portable `scripts/test_shared_pair_codec.py` files exist, match the maintained checker body exactly after the generated provenance comment, and are selected by the actual bundle resource function. They retain the nine legal pairs, all four outcome pairs and wrong-product counterexample without expanding proof scope. I did not execute the checker or submission code.
- The runtime model now defines d as the actual matching prescreen pass rate and q as full C/P/A success conditional on that pass. It reports finite observed-zero/leak facts, labels marginal fallback independence assumptions for both channels, validates finite/positive parameters, and uses `N*d=k/q` for calibrated passes. These fixes resolve the substantive earlier overclaims/accounting issue. The helper remains a planning approximation, not a runtime or filter-soundness theorem.

Two minor canonical residuals remain in peak: lines255–256 still label codecs binary-failure, and lines382–384 call new primitives binary-failure and ask focused tests to prove value-exactness. The early corrected section removes the near-every-input assertion, so this is not evidence that the old global failure-frequency claim still controls the entire core. Nevertheless, these later instructions should say promised-support/restoration obligation and specify whether the check is exhaustive over a stated finite domain, symbolic/proved, or sampled. Otherwise a reader arriving directly at the plateau protocol can overpromote focused tests to unrestricted proof. I have requested this narrow cleanup; no skill edits were made by this reviewer.

Runtime wording also has small nonblocking inaccuracies: an exponential distribution is not mathematically heavy-tailed, and displayed screen/evaluation equation labels omit calibration k when k differs from1, although the computed numbers and pass count include it. Say exponential-tail approximation and print the calibrated equations. Concurrent `max` is a queue/throughput planning approximation, not an exact expected first-success latency.

Resolution verdict: the original P1 mechanism/cost/portable-dependency failures are resolved in the corrected canonical artifacts. Final publication remains conditional on the narrow peak test-scope cleanup and the expressly pending coverage/reference synchronization and bundle rebuild. Do not infer that existing copied references or previously built bundles already contain the final merged review. Recheck those actual published outputs after synchronization; this recheck does not certify whole-circuit correctness, final195-row merge completion, or any external publication.

## Final staged-publication verdict — 04:40 UTC

PASS for the actual final staged packages. The remaining canonical peak passages now distinguish promised-support reversibility, exhaustive/symbolic operator checks and sampled focused tests; they no longer impose a binary failure-frequency model or use finite focused tests as unrestricted proof. Runtime labels include calibration k and correctly describe exponential tails as mathematically light-tailed. The concrete archived host paths/IPs are replaced by placeholders; generic historical `/root/<route>` templates remain examples, not local-host dependencies.

I checked the actual `publication-staging/bundles/bundle-manifest.json` and seven Markdown artifacts, not just the builder source. All seven bundle byte counts/SHA256 values match. All400 selected resource entries match their source byte counts/hashes and occur with exactly preserved content in their appendices. The eight shared references per skill give56 copies, each identical to the maintained root reference after its provenance header, with matching source hash. The portable codec checker is included in every package; the score/runtime helpers remain preserved in their routed packages. Every bundle begins with its current actual SKILL.md. Largest artifact is1,189,581 bytes, below the2MB limit.

The first final pass found four broken relative links inside the newly archived Toffoli catalogue. Those links were corrected and the actual bundles rebuilt. The repeated final pass found zero missing local Markdown targets, zero selected-resource/hash/content mismatches and no actual `/Users`, `/home`, historical concrete q1153 host path or removed private-IP dependency. Current shared references have no remaining draft/global-in-progress/delegated-pending coverage claim. Their historical585-row Q1172 snapshot is now clearly distinguished from the closing winner.

The current ledger and merged review file each contain586 records, all marked reviewed. The shared coverage statement557 public diffs plus29 explicit source limits sums to586. Closing UUID `e37cd0cb-ef31-4a17-9887-483b671ee311` has official Q1171/T946021/S1107790591 and actual parent `9db31da9a0971a2185e54d12d9441c36838aba40`. The closing reference separates Git parent, architectural starting point and product comparison, and explicitly distinguishes SAT claims, zero-failure census rows and59 positive-error census rows. It does not label all377 table rewrites proven exact. The scoped local codec proof remains separate from real capture/lifetime and whole-circuit accuracy.

Final manifest SHA256: `971d663f63451cfe59aeaebbbbd13c5bd50e0294b61c9824a81210d7a490b013`. The final Toffoli artifact is274,426 bytes; island artifact238,604 bytes. This verdict supersedes the earlier conditional publication verdicts for these exact staged hashes. It is permission-neutral and does not certify external upload/readback or universal circuit correctness. No candidate, benchmark, evaluator, generator or GPU code was executed during this final QA; only read-only artifact checks were performed.
