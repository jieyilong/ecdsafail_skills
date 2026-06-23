# The Shrunken-PZ Low-Qubit Track — and How q948 Broke the 952q Wall

**Scope:** the Proos–Zalka / "Shrunken-PZ" reversible secp256k1 EC point-add inversion route. This is the **qubit-minimization** line of work — *structurally separate* from the `trailmix_ludicrous` **product-min** line (see `REPORT_1168_wall_revamp.md`). They share nothing but the problem statement (in-place affine `P += Q`): different module (`src/point_add/trailmix_port/inversion/`), different inversion engine (a 530-step binary-GCD/Kaliski **divstep** state machine, not the jump-GCD + Karatsuba ludicrous arithmetic), different objective.

**Status (2026-06-21):** nasqret's `a203fac` reached **948 qubits** — the lowest peak ever on this route, breaking the prior **952q** wall — but it is **score-rejected**: 948q × 54,781,961 Toffoli = 51.9B (+468%). The PZ divstep inversion is inherently gate-heavy (~54.8M Toffoli ≈ **40× the ludicrous SOTA's 1.36M**, ~33× over the 948q product break-even of `1,581,316,420 / 948 ≈ 1.67M`). **The PZ track is a qubit-lower-bound witness, not a product-min contender.** Lineage of rejected qubit records: 1050q (trailmix) → 1019q (teddyjfpender) → 988→956 (the "lever stack", see SKILL §"Shrunken-PZ Q988→Q956") → 952q (`0ce9b13`) → 948q (`a203fac`) → **851q (`e7dd3de`, 6/23 — but an explicit *analysis oracle*, not a circuit; 464.5M Toffoli, +3659%; see §8 below).**

Why document a rejected route: the *qubit-shrinking technique* is genuinely novel and reusable (it is the qubit-side analogue of the ludicrous "empirical dead-CCX" lever — both are robust empirical envelopes projected from limiting witnesses), and it is the live frontier of "how low can the inversion go."

---

## 1. The PZ qubit model — 530 divstep rows, 5 width components, 681 + 267 = 948

The inversion is a **530-step binary-GCD extended-Euclid (Kaliski) divstep** state machine (`SHRUNKEN_PZ_NSTEPS = 530`, `shrunken_pz_schedule.rs:16`; one envelope **row** per divstep). Each row holds **5 working registers** whose live widths set the peak:

| component | register | width trajectory |
|---|---|---|
| `wa`, `wb` | **A, B** — the two running EEA/GCD magnitudes | start 256/256, **descend** toward 1 as the GCD shrinks |
| `wca`, `wcb` | **CA, CB** — the two Bézout cofactors (the modular-inverse accumulators) | start 1/1, **grow** toward 256 |
| `wq` | **Q** — the per-step quotient | ~21–25 bits (capped 99 via `TRAILMIX_Q_CAP`) |

Registers are laid out as **symmetric pairs**: `trailmix_register_widths_step` returns `[ab, ab, cacb, cacb, q]` with `ab = max(wa,wb)`, `cacb = max(wca,wcb)` (`shrunken_pz_state_machine.rs:201-205`) — A/B physically share the larger width, CA/CB share theirs, so the reversible conditional add/swap is clean.

**Peak-qubit formula** (`shrunken_pz_state_machine.rs:114-115`):
```
peak_at_step = 2·max(wa,wb) + 2·max(wca,wcb) + wq + FIXED
             = (sum of the 5 symmetric width components) + FIXED
```
The peak row is **row 363, the GCD crossover** — `[81,81,248,248,23]`, sum **681** (A/B shrunk to 81, cofactors grown to 248, quotient 23; 7 rows tie at 681). Total = **681 (peak working width) + 267 fixed = 948**. The ~267 fixed qubits are the non-resizable lanes: the 257-bit field coordinates / `dx,dy,lambda`, the modulus, EEA sign/parity, the affine step counter (collapsed to **1 lane** via `q949_affine_counter_requested`, `:94-96`), and transient CLZ/comparator ancilla.

So **lowering the peak = lowering the maximum-over-rows of the 5-component width sum.** That maximum is `Q949_ROBUST_PEAK_SAFE_SUM = 681`.

---

## 2. CLZ-context width narrowing — the structural lever

The divstep arithmetic (bit-length-difference + the controlled A↔B / CA↔CB add-subtract) only needs to touch bits **above a provably-zero low region**. Because A,B share a magnitude class and CA,CB share theirs, in a given **count-leading-zeros (CLZ) context** the low bits of a register are provably zero, so the reversible op runs over a **narrowed window `[lo .. len)`** instead of the full register. Implemented directly: the scan loops run `for k in (lo..src.len()).rev()` and the effective width is `aw = a.len() − lo_a` (`shrunken_pz_state_machine.rs:1594,1757-1758`).

`clz_safe_low_upper_bounds[row][register]` (4 registers A,B,CA,CB — Q is excluded, no leading-zero structure) is the **per-(row,register) maximum safe `lo`** — the largest low-window you can skip while still covering every observed input. This is what makes a row's *physical* width smaller than its naïve GCD magnitude.

---

## 3. How the robust envelope breaks 952 → 948

**Prior 952q (`0ce9b13`) = a single Monte-Carlo "thin schedule."** It baked `q952_thin_schedule.bin` (5,352 B) produced by `generate_thin_schedule()` (`shrunken_pz_schedule.rs:847+`): a seeded-RNG width search with train/validate/held-out splits and `repair_sample`, yielding **one global pack** that saturated the working budget `Q949_TARGET_SUM = 683`. Its route ladder bottomed at **952** (`lowq_q952_srot_counter567`). No robust/948 path exists in that dir (zero `q949_robust` references).

**a203fac 948q = a per-row, per-register, CLZ-context-conditional "robust row envelope," projected from worst-case witnesses.** It *replaces* the thin schedule with `q949_robust_envelope.rs` (+ `q949_robust_envelope_data.rs`, a 10.5 MB embedded artifact via `include!`). `q949_robust_symmetric_schedule_requested()` (`shrunken_pz_schedule.rs:714-750`) pulls per-row `widths` and CLZ `lows` from the envelope instead of recomputing a global budget. The envelope is the **tightest width/CLZ-low schedule that still covers every one of 12,590 empirical CLZ *limiting witnesses*** (`CLZ_LIMITING_WITNESSES = 12590`) — the worst-case inputs bounding each of **2,088 CLZ contexts** (`CLZ_CONTEXTS = 2088`, only **2** unconstrained) — drawn from **14 training streams** (`Q949_ROBUST_TRAINING_STREAMS = 14`).

**The squeeze (683 → 681 → −4 qubits):** the static-thin route saturated `TARGET_SUM = 683`; the robust envelope's actual maximum row sum is **681** (`PEAK_SAFE_SUM = 681`, `minimum_pair_symmetric_slack == 2` asserted in `parse_envelope`, `q949_robust_envelope.rs:390`). By projecting per-(row,register) CLZ-safe lows from the *real witness set* instead of a uniform global cap, the crossover rows (363–364) come in at 681 not 683. Combined with the **1-lane affine counter** and a direct-HCLZ peak-guard path (`LOWQ_Q948_DIRECT_HCLZ_PEAK_GUARD` + the robust schedule, route ladder `:1784-1789`), the total drops 952 → **948**. (Row 370 is a hand-repaired exception: `Q949_REPAIRED_ROW = 370`, pack `[78,78,255,255,17]`, all CLZ scans pinned to 78 lanes.)

**The meta-pattern:** this is the qubit-side twin of the ludicrous **empirical dead-CCX elimination** — *simulate many reachable inputs, find the limiting witnesses, project the tightest bound that covers them, bake + hash-seal it.* There the bound is "which CCX never fire"; here it is "how narrow each divstep register can be." Both trade a provable-for-all-inputs guarantee for a witness-validated, distribution-exact one that goes measurably tighter.

---

## 4. Correctness regime — witness-validated, NOT proven for all inputs

`Q949_ROBUST_ENVELOPE_FRESH_VALIDITY_CLAIMED = false` (`q949_robust_envelope.rs:127`); every training stream carries `proof_status: "reject"`, `training_only: true`. The envelope is fit to the **specific trained tail-nonces** (1,3,4,5,7,8,11,12,15,16,20,21,24). Consequences:

- **Island-exact** → the submission validates **0/0/0** (classical/phase/ancilla) on its island precisely because the narrowed CLZ windows never lose a bit for any input the projection was built to cover.
- **Not robust to distribution shift** → a fresh input stream can produce a CLZ context whose true safe-low exceeds the projected bound (an *uncovered* witness), silently truncating a high bit. Hence `FRESH_VALIDITY_CLAIMED=false`. This is **structurally weaker than the 952q baseline**, which carried a train/validate/held-out *safety margin*; the robust envelope is tighter *because* it is fit to the witness set with no margin.
- **Integrity wall** → `parse_envelope` re-derives `compact_projection_sha256()` and asserts equality with the sealed `Q949_ROBUST_PROJECTION_SHA256`, plus `ENVELOPE_SHA256` and `ARTIFACT_BYTES = 10,545,370` and the full training provenance. **Any input-stream change requires re-projecting and re-sealing the envelope** (a new selection certificate / job id; currently 71581). The metadata even records `generator_model: "GPT-Codex"` — the projection was produced offline by a code-gen tool.

---

## 5. Why it is still score-rejected (and what would change that)

948q is the lowest peak on this route, but the **product loses by ~33×**. The Toffoli cost (~54.78M) is structural to the PZ divstep inversion, not incidental:
- **530 record/replay divsteps**, each a controlled bit-length-difference (`direct_bitlen_diff_*`) + controlled A↔B / CA↔CB conditional add-subtract + a per-step quotient.
- **Per-step CLZ / leading-zero computations** to drive the narrowed windows — the very mechanism that buys the qubits costs gates.
- **Variable-width Cuccaro adds** + the per-transition resize/rebalance machinery (`shrunken_pz_rebalance_pack`, shrink+resize each of the 5 registers forward and reverse).

To become product-competitive at ~948q you would need Toffoli **< ~1.67M** — a ~33× reduction, i.e. a fundamentally cheaper inversion (not a packing tweak). That is why the corollary holds: **pushing the PZ qubit floor lower does not help the product**; the action stays in the 1159–1164q ludicrous band. The PZ track's value is as a *witness* (proving 948q is reachable for this inversion on a validated island) and as a *source of reusable robust-envelope technique*.

---

## 6. The 952 → 948 delta at a glance

| | Prior 952q (`0ce9b13`) | a203fac 948q |
|---|---|---|
| width source | `q952_thin_schedule.bin` (5,352 B, single Monte-Carlo global pack) | `q949_robust_envelope.rs` + `_data.rs` (10.5 MB, per-row/per-register CLZ-conditional envelope) |
| robust refs | 0 | full `Q949RobustEnvelope` struct |
| peak working sum | saturates `TARGET_SUM = 683` | `PEAK_SAFE_SUM = 681` (slack 2) |
| route-ladder floor | 952 (`q952_srot_counter567`) | 946/947/**948** (`direct_hclz_peak_guard` + affine counter) |
| step counter | counter-width route | affine counter → **1 lane** |
| validity | train/validate/held-out *margin* | witness-covered, **no margin**, `FRESH_VALIDITY_CLAIMED=false`, 12,590 witnesses / 14 streams, SHA-sealed |
| objective fit | qubit witness (rejected) | qubit witness (rejected, +468%) |

## 7. Reusable lessons

1. **Robust empirical envelope (the transferable technique).** To push *any* variable-width / variable-support schedule past where a single Monte-Carlo schedule saturates: enumerate the **limiting witnesses** (worst-case inputs per context) across many streams, project the **tightest bound that covers all of them**, bake it as a per-context table, and **hash-seal it to its training provenance**. The win comes from making the bound *conditional* (per-row, per-register, per-CLZ-context) rather than a single global cap. Same shape as the ludicrous dead-CCX `.idx`.
2. **It buys what it can't prove.** A witness-fit envelope with *no* safety margin (`FRESH_VALIDITY_CLAIMED=false`) is tighter than a margined schedule but only island-exact — it must be re-projected on any distribution change, and it is the right tool only when you can re-validate 0/0/0 on the shipped island.
3. **CLZ-context width narrowing** is the PZ-specific structural lever: a divstep register can run on `[lo..len)` whenever its leading-zero context certifies the low bits never carry. Worth porting to any GCD/EEA where register magnitudes have predictable leading-zero structure.
4. **But know when the track is a dead end for *score*.** The PZ inversion's ~54.8M Toffoli is ~33× over the product break-even at 948q. Qubit records here are witnesses; do not spend product-race effort on them unless the objective changes to pure-qubit-min (it has not — the 948q rejection at +468% confirms the active objective is the product).

---

## 8. The 851q "analysis oracle" (`e7dd3de`, nasqret, 6/23) — qubit record, but NOT a circuit

`e7dd3de` (submission `341d096`) drops the PZ peak from 948q to **851q** (−97), but is **rejected at +3659%**: 851 × **464,495,956** = 395B, ~250× over the product break-even (`~1.578B / 851 ≈ 1.85M` Toffoli would be needed; it delivers ~250× that). Toffoli **exploded ~8.5×** vs the 948q's 54.8M. Crucially, **it is not a reversible-circuit implementation at all** — the modules say so themselves (`register_shared_eea.rs`: *"an analysis oracle, not a reversible circuit implementation … passing this oracle does not establish a challenge-valid qubit count"*; `q945_local_hosts.rs`: *"Q945 acceptance remains blocked until the Q946 hardening prerequisites … are integrated"*). So 851q is a *combinatorial* lower-bound model, weaker even than the witness-validated 948q.

**The −97 qubit mechanism (three stacked levers, files under `trailmix_port/inversion/`):**
1. **Dirty-catalytic ancilla** (`q944_dirty_catalytic_predicate.rs`): the identity `G^d; d^=f; G^d; d^=f = G^f` lets an already-live ("dirty") register lane `d` be borrowed as the control rail for a gate and **restored exactly** — no clean ancilla allocated (`Q944CatalyticProxy::rewrite` asserts `allocation_serial`/`active_qubits` invariance). Each borrowed CCX is emitted *twice* (lender-cancellation), via `emit_controlled_by_dirty`.
2. **Gate hosting into existing lanes** (`q944_gate_host_feasibility.rs`/`_lifecycle.rs`, `q945_local_hosts.rs`): place a gate's transient ancilla inside a register lane proven zero at gate entry/exit by an empirical support census (`Q944_GATE_HOST_CENSUS_JOB=71935`), with per-row borrow tables (`Q945_DIVISION_PARITY_HOSTS`/`Q945_MULTIPLY_PARITY_HOSTS`) naming exactly which `A/B/CA/CB/Q` lane+bit hosts each divstep gate. `q944_full_structural.rs` closes the route: 9 "ordinary" hosted classes + 5 "division" classes falling back to `QuotientWitness`.
3. **Register-shared EEA — the dominant −97** (`register_shared_eea.rs`, porting **Luo et al. 2026**): A, B and a *single shared cofactor lane* (CA/CB share physical lanes) → `REGISTER_SHARED_PAPER_INVERSION_QUBITS = 3·256 + 52 = 820` inversion qubits, vs the q948 envelope's A+B+CA+CB working sum. The 851 = this ~820 register-shared core + point-add framing. Levers (1)/(2) remove the clean scratch lanes that would otherwise block the sharing. (Ladder: 948 → 945 → 944 [single-digit lane shavings from borrowing] → 851 [register-sharing collapse].)

**Why Toffoli explodes 8.5× — the qubit↔Toffoli-DEPTH reciprocal violation, in the flesh.** Hosting one Toffoli costs `toggle_gate; ccx; toggle_gate` where `toggle_gate` is a **full-width comparator** recomputed before *and* after the borrowed gate — `q944_gate_host_lifecycle.rs` asserts `ccx ≈ 12·width + 3 ≈ 3075` Toffoli to realize **one** useful Toffoli at width 256 (`q944_catalytic_cost ≈ 12·width+2`). Division rows are worse: `q944_dirty_arithmetic_toffoli = 2·width² + width + 1`, ×25 distributed ≈ 3.3M per call. Across **530 divsteps** (`SHRUNKEN_PZ_NSTEPS`), the surrounded-comparator envelope lands at ~4.6×10⁸ — matching the 464.5M. This is exactly the trailmix metric-model warning: **the saved lanes are paid back as full-width recompute/uncompute on both sides of every borrowed gate, so the trade is super-linear, not 1:1** — the qubit minimum and the score minimum are *not* reached by the same construction.

**Lesson.** Dirty-catalytic / gate-hosting / register-sharing are the genuine route below ~948q on qubits, and the Luo-2026 register-shared EEA is the structural source worth knowing. But on the *product* objective they are anti-levers: every borrowed lane costs a full-width comparator round-trip × 530. And `e7dd3de` is not even a shippable circuit — it's an oracle that *models* the qubit count assuming the hosting is free, then charges the hosting Toffoli. Treat sub-948q PZ numbers as combinatorial lower-bound claims, not circuits.
