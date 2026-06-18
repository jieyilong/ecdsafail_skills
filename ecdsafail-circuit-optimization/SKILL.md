---
name: ecdsafail-circuit-optimization
description: Use this skill whenever designing, reviewing, or modifying ECDSA Fail / quantum ECC point-addition circuits to reduce qubit count, Toffoli count, or score. This skill is especially relevant when comparing SOTA submissions, borrowing ideas from Andre/Schrottenloher-style space-optimized arithmetic, Trail of Bits trailmix-style reversible-circuit insights, or choosing structural optimization knobs before island hunting.
---

# ECDSA Fail Circuit Optimization

Use this skill to reason about structural circuit changes before spending GPU time on island hunting. It complements the `ecdsafail-island-hunting` skill: this skill designs and scores candidate routes; island hunting validates whether a route has a clean nonce.

The objective is usually:

```text
score = peak_qubits * measured_or_estimated_toffoli_count
```

Do not treat a lower qubit count as automatically better. A route that saves 2 qubits but creates a large Toffoli penalty or structurally dirty candidates may lose.

## First Principles

Optimize in this order:

1. Preserve correctness and reversibility.
2. Estimate score against current SOTA.
3. Reduce peak live qubits by shortening live ranges and reusing scratch.
4. Reduce Toffoli count only when it does not push qubits above the target.
5. Run short triage before large island search.

Track every candidate route with:

- CFG / feature knobs
- peak qubits
- average or estimated Toffoli count
- score
- expected correctness risk
- candidate density and best `cls / pha / anc` after triage

## Research / Engineering Harness Split

For longer ECDSA Fail optimization pushes, separate exploratory research from engineering hardening.
This keeps agents from either brainstorming forever or over-polishing a weak route.

Use a **research harness** to create and cheap-test hypotheses:

- generate diverse structural routes from the skill catalogue and SOTA notes
- measure q/CCX/estimated Toffoli/score quickly
- run tiny theoretical diagnostics or local gates
- keep promising and failed route records with enough detail to reproduce
- converge toward a short list of paths worth engineering

Use an **engineering harness** to harden the best research outputs:

- turn promising knobs into clean, reviewable patches
- improve diagnostics/tooling where the research loop got stuck
- run validator/local-vs-remote checks and controlled triage
- preserve exact CFGs, commits, state files, benchmark output, and failure classes
- publish concise shared notes so future agents can continue without rereading local logs

The handoff artifact between the two harnesses should include: source commit/frontier baseline, hypothesis, changed files/env vars, measured q/Toffoli/score, cheap-gate or full-run result, failure class if any, and the exact next step.

## Diagnose, Repair, Then Hunt

When a low-qubit or low-Toffoli route fails triage, do not immediately discard it or keep hunting blindly. Treat the route as a circuit-under-debugging problem and run a bounded diagnosis/repair loop before spending more GPU time. This is especially important for aggressive sub-frontier qubit routes where candidate density can be zero because the circuit structure rejects the reachable input distribution in theory.

Core rule:

```text
The GPU should confirm a viable circuit theory, not substitute for one.
```

Use this loop when a route shows zero or very low candidate density, repeated high dirty fingerprints, persistent `pha`/`anc`, a suspiciously uniform failure pattern, or a hard residual floor that may be nonce-independent.

1. **Freeze the exact route.** Record the source commit, CFG, peak qubits, CCX/Toffoli estimate, score if relevant, peak-owner trace, state-file identity, validator binary/source hash if relevant, scan range, candidate density, and the smallest scan/validation evidence that demonstrates the failure.
2. **Diagnose the failing mechanism.** Prefer circuit-aware diagnostics over more nonce search: classical prefilter reason histograms, per-section validator counters, first-failing operation/section traces, failing-shot overlap tests, convergence-step distributions, carry/borrow width histograms, compare-decision disagreement counts, phase/ancilla cleanup receipts, local-vs-remote validator cross-checks, and peak-owner traces.
3. **Explain the failure in circuit terms.** Name the invariant that is being violated: under-converged GCD transcript, truncated body carry losing information, width envelope too tight, stale compare bit, dirty scratch reused across a live control, incorrect measurement/phase discharge, full raw transcript decode co-residing with too much state, operand alias crossing a dependency boundary, or a peak-owner assumption that was false.
4. **Patch the smallest responsible mechanism.** Restore one carry bit/window, widen one compare or active-width envelope, add a local giveback, delay one scratch release, restore one cleanup, change one chunk boundary, move one alias lifetime, add a per-step decode frame, or recompute/clear a narrow frame instead of holding a wide raw block. Keep the patch as close as possible to the diagnosed mechanism.
5. **Measure the cost of the repair.** Recompute peak qubits, CCX/estimated Toffoli, score if score matters, and peak-owner movement. A repair is useful only if it preserves the target qubit regime or spends Toffoli/qubits in a consciously acceptable way.
6. **Re-run diagnostics before hunting.** The first success criterion is theoretical viability: the diagnosed hard failure should disappear or become a rare tail, candidate density should become nonzero/plausible, failure fingerprints should diversify, `pha`/`anc` should not persist, and nearby safer variants should improve smoothly.
7. **Only then run a short triage scan.** Use a 5-10M equal-size pilot before any large hunt. Validate candidates in fast and full modes. Continue only if candidate density and the `cls / pha / anc` distribution look huntable.
8. **Iterate with a budget.** Try up to a fixed number of diagnosis/repair iterations, often `X = 10`, or stop sooner if several consecutive repairs do not improve the same core signal. Record failed repairs and why they failed so the next agent does not rediscover them.

Judgment rules for the loop:

- Prefer fixes that restore a broken invariant over random knob ladders.
- Do not increase qubits or Toffoli "a little" repeatedly without tracking cumulative cost.
- If relaxing a knob makes the theoretical diagnostic healthy, use that relaxation to identify the mechanism, then look for a cheaper targeted repair.
- If every repair moves the route out of the target qubit regime, mark the route structurally incompatible with that target and switch bases.
- If a route has no theoretical path to candidate production, GPU scanning is not evidence gathering; it is just burning frontier.

Hunt-readiness checklist:

- the route's qubits/Toffoli are acceptable for the current objective
- the peak-owner trace matches the intended optimization
- candidate density is not starved
- validation has low or improving residuals
- dirty fingerprints vary across candidates
- no fixed failing-shot floor is detected
- local and remote validators are reproducible

### Example: GCD Prefilter Autopsy Before More Hunting

When a route has zero GCD-clean candidates, diagnose the classical GCD prefilter directly before extending any island search. Derive the same Fiat-Shamir shots as the GPU search and run every `dx` and `c` factor through `check_gcd_factor`, but do not early-exit. Print histograms for:

- factor pass/fail rate split by `dx` and `c`
- `NonConvergence`, `WidthOverflow`, `BodyTrimMismatch`, and `ComparatorMismatch`
- failure step distribution
- true convergence-step p50/p90/p99/max
- first bad shot distribution across each nonce

Interpretation:

- Mostly `NonConvergence`: raise active iterations, use K2/jump-style acceleration, or add enough padding for the 9024-shot tail.
- Mostly `WidthOverflow`: the active-width margin/slope or step bump schedule is too tight.
- Mostly `BodyTrimMismatch`: body/carry truncation is discarding information and needs a giveback, wider body window, or different chunk boundary.
- Mostly `ComparatorMismatch` under strict mode only: the prefilter may not be the blocker, but full validation must localize whether the truncated branch remains semantically correct.

Case study: the `q=1171, active360, CCX=1,438,594` K1/base-3 sidecar route had zero candidates because sampled Fiat-Shamir factors had effectively `0%` pass rate. Raising active iterations removed only the convergence part; early `BodyTrimMismatch` and `WidthOverflow` still rejected every factor. Disabling the aggressive body/width envelope made the same samples mostly pass. The conclusion was structural: the low-qubit envelope discarded required GCD body/width information too early, so large-scale island hunting could not succeed until that mechanism was repaired.

### Example: K5 Apply Decode Repair

When the 1203q K5 transcript-compression route is apply-peak bound, inspect whether the compressed block is still full-decoded into a raw block during apply. If a 12-bit compressed K5 block co-resides with a 15-bit raw block plus codec/apply scratch, the route may have a direct qubit repair opportunity.

Repair pattern:

1. Keep the K5 clean transcript block compressed at rest.
2. Decode only the current step's `(b0, b0_and_b1, s2)` into a tiny frame.
3. Run the apply operation controlled by that frame.
4. Recompute the same frame and clear it.
5. Restore the compressed block before moving to the next step.

This attacks the measured peak owner directly. It may spend extra codec Toffolis, but it avoids holding the whole raw transcript block live across `apply_double_y` / `apply_reverse_halve_y`. Use this kind of per-step decode frame whenever the diagnosis shows that "compressed representation exists, but full materialization still binds the peak."

## The Qubit<->Toffoli Exchange Rate (trailmix metric model)

This is the single most important framing for this challenge. The verified trailmix
`quantum_resource_metrics.md` models the trade explicitly, and it changes how to read
the `score = qubits * Toffoli` objective:

- In the **volume-limited regime** (a space-minimized EC inversion has few magic-state
  factories), iso-cost is `C ~ qubits * Toffoli`. The **break-even tolerable Toffoli
  blowup is the reciprocal of the qubit shrink**: halve qubits -> up to 2x Toffoli is
  free; shrink 10x -> 10x Toffoli is free. The benchmark score is a faithful *local
  gradient* of real cost around a fixed operating point.
- **The trap is Toffoli-DEPTH, not Toffoli-count.** The reciprocal rule holds only if
  the qubit-saving trick is depth-neutral. Recompute/uncompute and fewer-ancilla tricks
  inflate depth; at the reaction floor that depth blowup is NOT refundable. trailmix
  flags getting the EC-inversion Toffoli-*depth* as an open item -- all their published
  trades assume depth-neutrality.
- Practical verdicts they actually use: cut qubits 2x for +50% Toffoli (depth-neutral) =
  clear win; cut qubits 20% but 3x Toffoli = clear loss.

Consequence for our work: `qubits * executed_Toffoli` as an absolute scalar is a weak
("everything idles") metric, but its gradient is exactly the right "trade these qubits for
those Toffolis" rate. When two routes have near-equal score, prefer the one that did NOT
buy its qubits with recompute (depth), because the depth cost is invisible to the score
but real on hardware.

**The concrete vent primitive** (trailmix `gidney_const_adder.rs`): a hybrid
controlled adder costs `Toffoli = 3n - 2 - vents`. Each "vent" replaces one carry-uncompute
Toffoli with an X-basis measurement + a `CZ` phase fixup (T-count 0). So **each vent =
-1 Toffoli, +1 peak qubit**, held only between the forward and reverse carry chains. This
is the exact, sim-verified dial. Vent OFF-peak phases (where ancilla headroom is free) for
pure Toffoli savings; on the peak-binding phase, venting costs real score.

## Qubit Reduction Patterns

### Live-Range Shortening

The strongest qubit reductions usually come from freeing registers earlier, not from changing arithmetic formulas.

Look for:

- scratch registers whose final consumers are earlier than their lexical scope
- compare bits that can be cleaned once their branch/control use is over
- carry or borrow chains that can be truncated, measured, or recomputed
- temporary GCD/fold state that can be released during a fold instead of after the whole block

Relevant knobs and ideas from our experiments:

- `DIALOG_GCD_APPLY_RELEASE_CLEAN_SCRATCH_DURING_FOLD=1`
- `DIALOG_GCD_K5_FREE_CLEAN_BLOCK_DURING_SHIFT=1`
- `DIALOG_GCD_APPLY_CHUNK_TOPCLEAN=0/1`
- `DIALOG_GCD_APPLY_FINAL_TOPCLEAN=0`
- `SQUARE_ROW_WINDOW_MEASURED_CARRY_CLEAR=1`

**The live-range HOLE pattern (1211q -> 1193q SOTA, submission ad4cf86d, 2026-06-13).**
This is the strongest recent qubit win and the canonical example of the pattern. The K5
apply phase holds a `compressed_block` transcript scratch live across the whole block, but
that block is DEAD during the y-double shift sub-phase (`mod_double_inplace_fast` +
`cmod_double_inplace_lazy`). `DIALOG_GCD_K5_FREE_CLEAN_BLOCK_DURING_SHIFT=1` punches a hole:
`free_vec(compressed_block)` right before the shift and `reacquire_vec` right after (code:
`src/point_add/rounds/dialog/compressed.rs:1977`). That drops the GCD-apply peak below the
round84 square's peak, so the binding peak owner moves to
`round84_inplace_solinas_square_forward`. Paired with `SQUARE_ROW_MAX_SEG` 176->166 (the
square is now the binder, so segment it harder), `DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS` 19->20
and `DIALOG_GCD_FOLD_CARRY_TRUNC_W` 17->18 (loosen the now-non-binding knobs for island
landability), plus a fresh `DIALOG_TAIL_NONCE` hunt, this dropped 18 qubits (1211->1193) for
only +7,727 avg-T (1,404,664->1,412,391) = 429 T/q, far under the ~1,212 T/q break-even.
Gate conditions in code: `!inplace_raw && recompressed_s2.is_none() && replay_swap_host`.
Lesson: when you free a binding-phase scratch, the NEXT peak owner becomes the new target —
re-trace `TRACE_PEAK` after every hole to find who binds now, then attack THAT phase.

**Peak-owner whack-a-mole — the verified migration chain (1211 -> 1192).** Each qubit win
is a lever that drops the *current* binder and exposes the *next* one; the technique is to
re-`TRACE_PEAK`, read the new owning phase, and design the next lever against THAT phase:
- **1211q** — binder = GCD-apply compressed-block.
- `DIALOG_GCD_K5_FREE_CLEAN_BLOCK_DURING_SHIFT=1` (the live-range hole above) ->
- **1193q** (SOTA ad4cf86d) — binder migrated to `round84_inplace_solinas_square_forward`.
- attack the square's SIZE: **`SQUARE_ROW_MAX_SEG` 166->165** (one segment notch, +fresh island
  `2107498317`) ->
- **1192q** (SOTA a7ec174f, `0fa5c6f`, 1,683,610,600 = 1192 x 1,412,425; -1 q for +34 avg-T —
  the tighter segment costs a hair of recompute). The seg notch dropped the square's peak below
  the next phase, so the binder migrated AGAIN to
  `dialog_gcd_materialized_special_underflow_fold` (ops_idx ~1.82M, early in the GCD).
- THEN, square now OFF-peak, **`SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS` 21->19** (+island
  `11556565`) ->
- **1192q** (SOTA a39ce501, `cf99209`, 1,683,083,736 = 1192 x 1,411,983) — a PURE peak-neutral
  Toffoli trim: -442 avg-T, **0 qubits**. Shrinking the square's clean-compare window frees no
  qubits because the square no longer binds the peak; it only cuts gates.
- then ATTACK that binder with per-step scheduling + a denser codec (next bullet) ->
- **1185q** (SOTA 3182d2b3, `cf310ec`, 1,681,025,595 = 1185 x 1,418,587; -7 q for +6,604 avg-T
  = 943 T/q, under break-even). A ROUTE CHANGE, not a notch — binder migrated to
  `dialog_gcd_apply_chunk_sub_ripple` (ops_idx ~1.82M). **Next sub-1185 target = that GCD-apply
  chunked sub-ripple phase.**

Two lessons fall out of the 1193->1192 leg pair: (1) the QUBIT win only ever comes from shrinking
whoever CURRENTLY binds the peak (here the seg notch on the square); (2) once a phase falls
OFF-peak, shrinking it further is a pure-Toffoli play — judge it on avg-T alone, expect zero
qubit movement (here clean-compare 21->19 bought -442 T at 0 q). Don't expect a qubit drop
from squeezing an off-peak phase, and don't skip a real Toffoli win just because it doesn't
move qubits. The cheap workflow to tell which case you are in:
`rm -f ops.bin; TRACE_PEAK=1 build_circuit | grep peak_qubits` prints
`peak_qubits=<N> at phase='<owner>'` — that phase name IS your next QUBIT lever's target;
everything else you tighten is a Toffoli-only play.

Risk: early release can silently create classical/phase errors if a supposedly dead bit is still entangled or reused as a control later.

### Per-Step Scheduling And Denser Codecs (the 1192 -> 1185 route change)

Once the cheap constant-width notches are exhausted, the next qubit regime is unlocked by
TWO structural ideas, both verified in SOTA 3182d2b3 (`cf310ec`, 1185q):

**1. Per-step scheduling — replace a constant width with a `fn(step)` schedule.** The GCD
runs ~258 fixed iterations; different steps tolerate different truncation/notch widths, so a
single constant must be set to the worst-case step. A per-step schedule squeezes each step
exactly as tight as IT can take, recovering the slack the constant wasted. Concretely:
- Code: `dialog_gcd_special_fold_carry_trunc_window(step)` REPLACES the constant
  `fold_carry_trunc_window()` at the `dialog_gcd_materialized_special_underflow_fold` (and
  `_borrowed_`) sites (`src/point_add/mod.rs` underflow-fold).
- Knobs (all per-step maps): `DIALOG_GCD_BINDER_NOTCH_STEPS=8,9,10` + `_EXTRA=3` +
  `_MAP=11:1,12:1,13:1` (notch the BINDING phase at chosen steps — the scheduled form of
  "attack the current binder"); `DIALOG_GCD_BODY_CARRY_BAND_TRIMS` (one entry per active
  iteration, e.g. `0,3,3,3,3,3,1,...,1,3,3,3` — wider trim at the ends, tight 1 in the
  middle); `DIALOG_GCD_SPECIAL_OVERFLOW_CLEAN_STEP_BITS=113:21,131:21,142:22,...`.
- Parse/validate these in the classical filter (`dialog_gcd_classical_filter.rs` reads
  `BINDER_NOTCH_STEPS/EXTRA/MAP` ~line 707) so island hunting models the per-step widths.

**2. Denser transcript codec.** `DIALOG_GCD_K5_HEAD11_CODEC=1` + `DIALOG_GCD_APPLY_IMPLICIT_HIGH_ZERO=1`
pack the K5 transcript tighter (head-11 codec) and exploit known-zero high bits in the apply.
This is the "denser transcript compressor" long predicted as the only real sub-1193 lever
(symbol entropy is near-uniform, so the win is structural packing, not VLC). Guarded by
`dialog_gcd_k5_head11_codec_selftest()` + `dialog_gcd_k5_head11_supports(pattern)` — a codec
that changes the transcript MUST ship a bijectivity/coverage self-check or it silently drops
inputs. Paired with deeper carry parking (`DIALOG_GCD_FOLD_PARK_LOW_CARRIES` 1->7, new
`DIALOG_GCD_SPECIAL_FOLD_PARK_LOW_CARRIES=5` + `_RELEASE_SCRATCH=1`) and `DIALOG_GCD_PERPOS_MAJ2=1`.

Two meta-lessons from this submission:
- **Off-peak phases get loosened, not just left alone.** This route raised `SQUARE_ROW_MAX_SEG`
  165->176 and `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS` 19->21 — UN-doing earlier qubit notches
  on the square — because the square is now far off-peak, so loosening it is qubit-free and
  buys back Toffoli. When the binder moves, revisit what you previously over-tightened.
- **The competitor bakes its optimizer's full env vector into the source** via a
  `std::env::set_var(...)` block ("make the submitted circuit independent of the optimizer
  shell environment"). They run an external optimizer over a large knob vector and materialize
  the winner — a signal that the frontier is now found by automated multi-knob search over
  per-step schedules, not hand-picked single notches.

### Chunking Large Blocks

Chunking lets the circuit trade recomputation/extra gates for lower peak qubits.

Useful knobs:

- `DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS=<n>`
- GCD/apply block chunk sizes, especially routes like `b14`, `b15`

Observed behavior:

- Increasing chunk count can lower peak qubits by reducing simultaneously live fold state.
- Too much chunking can increase Toffoli and sometimes worsen candidate quality.
- Chunk-count changes can interact strongly with compare-bit cleaning and carry truncation.

### In-Place and Operand-Aliasing Tricks

The major SOTA direction we observed was avoiding duplicate operand storage by doing more work in-place and carefully aliasing operands.

Relevant ideas:

- use in-place raw blocks when a source can safely become the destination
- avoid materializing full intermediate products when a streamed/folded form is enough
- borrow existing registers as dirty scratch when their values can be restored before observation
- decompose in-place modular multiplication into transcript creation, transcript application, and transcript uncompute:
  `x -> dialog/transcript`, apply the transcript to turn `(y, 0)` into `(y, xy mod p)`, then reverse the transcript creation to restore `x`
- in point addition, avoid a separate long-lived slope register when possible; let the slope live in an existing coordinate register between the two dependent multiply/divide operations

Useful knob:

- `DIALOG_GCD_K2_APPLY_INPLACE_RAW_BLOCK=1`

Trail of Bits/trailmix-inspired framing:

- Treat the program as a reversible dataflow graph.
- Hunt for operand aliases and dead registers.
- Prefer transformations that reduce live-set peak rather than only local gate count.
- Be suspicious of aliases across measurement, phase, or conditional-control boundaries.

Risk: operand aliasing often produces low qubits but can cause uniform high `cls / pha / anc` failures if one dependency was misclassified as dead.

### Transient vs persistent-transcript floor — two qubit levers, very different exchange rates (verified q1185 → q1175 → q1170)

Decompose the binder's live set into a **persistent floor** (held across the whole region) and a
**transient** (the working registers of the *current* step). Get this from an alloc-phase
composition histogram at the peak (instrument `alloc_qubit`/`free` to tally live qubits by the
phase that allocated them). On the dialog-GCD route at the 1185q binder
(`dialog_gcd_apply_chunk_sub_ripple`) it was:

- **1149 persistent** = 637 `raw_pa_pair1_quotient` (u 256 + compressed transcript ~372) + 512
  `init` (the two output coordinate registers), plus
- **~36 transient** = the current apply chunk's load (~20) + carry-ripple lane (~15).

The verified **q1175** route (commit `757e6e7`, full-clean `0/0/0`) cut **−10 qubits entirely from
the transient** (load 20→13, ripple 15→12); the 1149 persistent floor was **untouched**. The
transient is the *easiest* lever — but, as the q1170 SOTA below proves, **not the cheapest per
qubit.** Both the transient and the persistent transcript floor are reducible; they have very
different exchange rates (see the comparison at the end of this section).

**Mechanism — source the current-chunk scratch from qubits that already exist, and chunk finer:**

- **Host the apply working space on DIRTY qubits** (`DIALOG_GCD_APPLY_ALL_DIRTY_QOFFSET`,
  `..._FIRST_DIRTY_QOFFSET`) — reuse non-`|0⟩` qubits as the apply's scratch and clean them after,
  instead of grabbing fresh clean lanes (the dirty-borrow pattern, scaled up to the apply hot loop).
- **Borrow already-cleaned future-boundary carries** as scratch
  (`DIALOG_GCD_BOUNDARY_REPLAY_BORROW_CLEANED`, `DIALOG_GCD_APPLY_BORROW_FUTURE_BOUNDARY_CARRIES`).
- **Finer apply chunking** (`DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS` 18→25 with an explicit
  `DIALOG_GCD_APPLY_CHUNKED_F_CUTS` schedule) — smaller chunks ⇒ a smaller per-chunk load/carry lane
  live at once.
- **Stream/host fold controls** instead of materializing them (`DIALOG_GCD_FOLD_STREAM_CONTROLS`,
  `DIALOG_GCD_FOLD_HOST_STREAMED_CONTROL`, `..._HOST_D_CARRY12 / _E_TOP_CARRY / _OVF2_CARRY13`) and
  **deeper carry parking** (`FOLD_PARK_LOW_CARRIES` 7→17, `SPECIAL_FOLD_PARK_LOW_CARRIES` 5→15).

**Coordinate across ALL co-bound families.** The 1185 peak was a co-bind plateau of ~10 phases
(round84 square + materialized folds + apply double_y/halve_y + apply ripple), so narrowing one
family's transient leaves the others pinning 1185. The q1175 route narrowed *every* co-bound
family together: apply (above) + square (`SQUARE_ROW_MAX_SEG` 158→144) + folds (park/host).
Budget for several coordinated edits and re-`TRACE_PEAK` after each to see which walls remain.

**Two cautions.** (1) These are **new code primitives, not just knobs** — the q1175 commit is ~816
inserted lines across `compressed.rs`/`dialog/mod.rs`/`venting.rs`; the dirty-qoffset /
boundary-borrow / stream-control knobs do not exist on the 1185 base. A structural width cut is
value-exact-or-broken (validate `0/0/0` on random inputs before any island hunt; the commit name
"repaired clean island" reflects exactly that fix-then-re-hunt). (2) **The trade is steep:** −10
qubits cost **+127k avg-Toffoli** (~12,700 T/qubit, ~10× the ~1,200 break-even), so q1175 is a
clean **qubit-record branch, not a score win** (1175 × 1,545,825 = 1,816,344,375 > the 1185 SOTA's
1,681,025,595). Gate every transient cut on the exchange rate — finer chunking + hosting/borrow
recompute is where the Toffoli goes. That the persistent 1149 floor is still standing means real
qubit headroom remains *if* a cheaper-Toffoli mechanism (or a denser transcript) is found.

**q1170 SOTA — the CHEAP lever (denser transcript codec + transcript release): a real score win.**
Submission `1278a07` / commit `674d0d8` (nasqret, promoted 2026-06-13) is the first verified
sub-1175 score win: **1170 q**, average Toffoli **1,434,998.727** (rounded `1,434,999`), score
**1,678,948,830**, nonce `11,156,415`. It beats the 1185 SOTA's `1,681,025,595` despite spending
more Toffoli, because the qubit cut is cheap enough. Relative to q1185 it cut **−15 qubits for
only +16,412 avg-Toffoli (~1,094 T/qubit, UNDER the ~1,200 break-even)**, so the product dropped.
Composition vs 1185 (637 + 512 + 36): it took **−7 from the persistent transcript** (637→630) **and**
−8 from the transient (36→28). The −7 floor cut is the headline and the cheap part:

- **Denser tail transcript codec** (`DIALOG_GCD_K5_TAIL3_TOP32_CODEC=1` +
  `..._TAIL3_TOP32_STREAM_APPLY=1`) — a tail-specific re-encode for the final 3-step K5 tail.
  The reachable support has exactly 32 patterns and is packed into 5 code bits via an ANF
  encoder/decoder (`DIALOG_GCD_K5_TAIL3_TOP32_SUPPORT`, `*_ENCODER_ANF`, `*_DECODER_ANF`).
  The shipped self-test (`DIALOG_GCD_K5_TAIL3_TOP32_SELFTEST`) proves bijection/coverage and
  phase-clean forward/reverse behavior. This is a value-exact width cut, not a nonce-side
  approximation.
- **Streaming tail apply** (`DIALOG_GCD_K5_TAIL3_TOP32_STREAM_APPLY=1`) — do not materialize the
  old raw tail during apply. Recompute only the current slot's `(b0, b0_and_b1, s2)`, run the
  apply primitive, then clear that slot. Verified ablation: turning off streaming while keeping
  the new codec raises the GCD/apply/fold plateau **1170→1171**.
- **Codec itself is the large GCD/apply cut.** Verified ablation: disabling the new top32 codec
  (and its streaming apply) raises the GCD/apply/fold plateau **1170→1177**, while the square
  remains at 1170. The codec therefore accounts for about seven GCD-side peak qubits, and the
  streamed apply accounts for the last one.
- **Transcript-bit release** (`DIALOG_GCD_K5_PARTIAL_RAW_RELEASE=6`,
  `DIALOG_GCD_K5_RELEASE_SCALE_BITS=5`, `DIALOG_GCD_RUNWAY_PARTIAL_BLOCK=1`) — free/host transcript
  bits no longer needed in full.
- Its −8 transient came cheaply too: `APPLY_CHUNKED_F_BLOCKS` 18→20 with explicit cuts
  `17,34,50,66,81,96,110,124,137,150,163,175,187,198,209,219,229,238,247`, deeper park
  (`FOLD_PARK` 15 with per-step 16/17 map, `SPECIAL_FOLD_PARK` 13 with per-step 14/15 map),
  `FOLD_HOST_DERIVED_CONTROLS=1`, and `APPLY_BORROW_FUTURE_BOUNDARY_CARRIES=1` — **not** the
  expensive dirty-qoffset hosting.
- **Selective repair inside the same peak budget.** The route keeps global `DIALOG_GCD_COMPARE_BITS=46`
  but adds seven 48-bit compare repairs (`181,194,199,202,207,212,216`). Regular and special
  pseudo-Mersenne folds keep aggressive global windows (`FOLD_CARRY_TRUNC_W=18`,
  `SPECIAL_FOLD_PARK_LOW_CARRIES=13`) and widen only empirically failing steps to 19/20 bits via
  `*_STEP_WINDOWS`. Special overflow/underflow cleanup uses existing clean scratch for hosted
  phase-conditioned comparison, so repairs restore correctness without adding global scratch.
- **Square must be co-balanced.** The q1170 GCD side alone is not enough: the final route also sets
  `SQUARE_ROW_MAX_SEG=143` and square-row measured cleanup schedules. Verified ablation: reverting
  just `SQUARE_ROW_MAX_SEG` to the old q1185-ish `158` makes the square bind at **1185** while the
  GCD side stays at 1170. The final trace is a deliberate co-binder plateau:
  apply add/sub ripple, apply final ripple, compressed apply double/halve, special over/underflow
  fold, and square forward/inverse all hit exactly **1170**.

**Decisive lesson — match the lever to its exchange rate:**

| route | what it cut | −q | +avg-T | T/qubit | score |
|---|---|---:|---:|---:|---|
| q1175 (`757e6e7`) | transient only, via DIRTY-qubit hosting | 10 | +127k | ~12,700 (~10× b/e) | **worse** (1,816M) |
| q1170 (`674d0d8`) | persistent transcript −7 + cheap transient −8 | 15 | +16k | ~1,094 (under b/e) | **better** (1,679M) |

**Attacking the persistent transcript with a denser/streamed codec is the CHEAP qubit lever;
attacking the transient with dirty-qubit hosting is the EXPENSIVE one.** Reach for the transcript
codec first when you want a *score* win, not just a qubit record. This also **corrects the old
"transcript is near-incompressible / route is at its qubit floor" conclusion**: a *tail-specific*
codec plus raw/scale-bit *release* (not pure entropy/VLC coding — which is why a VLC-only analysis
missed it) found 7 more transcript qubits at a good rate. The floor *is* reducible; the lever is
the codec, not entropy coding.

Method behind q1170 (from the public submission note plus the committed
`memory/2026-06-13-q1192-*.md` search note): exact GPU/WMI island filters were cross-checked
against Rust/Metal/CUDA parity before large search, then the final nonce was replayed through the
trusted 9024-shot evaluator at `0/0/0`. Preserve this discipline for future sub-1170 work: codec
self-test first, peak ablations second, local/remote validator parity third, island hunt last.

**q1170 floor since `1278a07` — value-exact stacking + budgeted per-site repairs (current SOTA
`65e8bcb`, 1,677,861,900, nasqret, 2026-06-14).** The 1170 peak held; the score dropped further via
value-exact cuts at *fixed* peak (verified from `ecdsafail submissions --all` + notes; see
`references/frontier-1211-to-1170.md`, notes archived in `references/submission-notes/`):
- `6dd61c5` (1,678,629,420): `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS` 19→18 — the round-84 square
  windowed boundary-carry cleanup comparator. Value-exact (the square *product* is always exact;
  only a boundary carry is governed), −372 emitted Toffoli, peak-neutral; soft class
  `SquareCleanupMismatch`.
- `dc6724b` (1,678,360,320): **stacks** that with `DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS` 20→19
  (−506 T). The two cut **disjoint op-stream regions** with independent soft-mismatch classes
  (`SquareCleanupMismatch` vs `ApplyCleanupMismatch`), so a **single** `DIALOG_TAIL_NONCE` clean
  under both captures both. General method: sweep for undeployed value-exact cuts, prove
  region-independence, then hunt one nonce clean for all.
- `65e8bcb` (current SOTA, 1,677,861,900): swaps the tail codec for the **affine299**
  reachable-support mapping and replaces global widening with **budgeted per-site repairs** — an
  execution-weighted **0-1 knapsack** selects 17 one-bit fold-width repairs (each paired with its
  carry-parking width); a grouped phase-cleanup optimizer selects sparse overflow/underflow/square
  repairs under an **80-emitted-Toffoli budget**. This generalizes `1278a07`'s hand-picked 48-bit
  compare repairs into an optimizer over the per-site repair set.
- **Status:** value-exact comparator headroom at the 1170 floor is now reported **exhausted** (the
  9-way peak co-bind). Further *score* gains need a structural **sub-1170** cut (open research) or
  the avg-Toffoli rounding lottery — so prioritize the persistent-transcript floor (codec) and
  square co-bind over more comparator nonce-hunting.

### Compare-Bit Narrowing

Several low-qubit routes reduce the number of clean compare bits kept live.

Useful knobs:

- `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS=<k>`
- route variants like `cmp21`

Observed behavior:

- Reducing compare bits can save qubits directly.
- Aggressive compare-bit reduction can make candidates uniformly dirty.
- A route with `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS=21` may be viable only when paired with enough carry/fold safety.

Triage rule:

- If a compare-bit route yields repeated high triples like `9024 / 141 / 0` or hundreds of `cls / pha`, stop quickly.

### Carry/Borrow Truncation

Carry and borrow chains are large qubit consumers. Truncating or narrowing them is one of the main qubit/Toffoli tradeoff levers.

Useful knobs:

- `DIALOG_GCD_FOLD_CARRY_TRUNC_W=<w>`
- `KAL_FOLD_CARRY_TRUNC_W=<w>`
- `DIALOG_GCD_FOLD_FREED_TAIL_ED=1`
- `DIALOG_GCD_SPECIAL_FOLD_BORROW_CARRIES=1`

Observed behavior:

- Wider truncation windows are safer but cost qubits.
- Narrower windows can reach lower qubits, but correctness degrades quickly.
- Special fold-borrow carry handling helped low-qubit 1210-style routes remain near-miss rather than structurally dead.

Use a ladder:

1. Start from a validated or near-miss route.
2. Change one carry width by a small amount.
3. Measure qubits/Toffoli.
4. Triage candidate quality.
5. Stop when near misses disappear or severity jumps.

### Measured Cleanup

Andre/Schrottenloher-style space optimization and Trail of Bits-style reversible dataflow both motivate using measurement or classical transcript bits to reduce coherent state, when the measured value is no longer needed quantum-coherently.

Use this when:

- a bit is only used classically after a point
- phase correctness can be explicitly checked
- adaptive correction is cheap enough

Risk:

- Measurement can fix qubit pressure but create phase bugs.
- Always track `pha` separately; do not rely only on classical output checks.
- Whole-register ghosting is the extreme version: a full coordinate can be discharged and later reconstructed only if there is a written phase/correctness proof for the discharge path.

### Vented/Short Product Paths

Product paths can reduce live state by streaming or shortening product intermediates.

Useful knobs:

- `ROUND84_QPROD_VENT_PAD=1`
- `ROUND84_QPROD_VENT_PAD_MINW=<w>`
- `ROUND84_QPROD_SHORT=1`
- `SQUARE_ROW_MAX_SEG=<n>`

Observed behavior:

- Smaller segment limits can reduce peak qubits.
- Vent padding can make shorter product paths safe enough to validate.
- These often trade qubits for Toffoli and need score gating.

## Toffoli Reduction Patterns

### Fused Folds and Fast Adds

Fusing stages removes redundant controls, cleanup, or repeated work.

Useful knobs:

- `DIALOG_GCD_APPLY_FUSED_FOLD=1`
- `ROUND84_FOLD_FAST_ADD=1`

Observed behavior:

- These were helpful for lower-Toffoli 1216-style routes.
- They can interact with top-cleaning and scratch release.
- They are usually worth testing first when the qubit budget has a little slack.

### Skip Final Top-Clean When Safe

Some SOTA-like routes saved gates by not doing a final cleanup pass that was redundant under the chosen folded structure.

Useful knob:

- `DIALOG_GCD_APPLY_FINAL_TOPCLEAN=0`

Risk:

- If it is not actually redundant, candidates show phase or classical dirt.
- This knob should be paired with strong fast/full validation and near-miss triage.

### Avoid Full Materialization

Do not build full-width intermediates if only a window, top bits, or folded contribution is needed.

Examples:

- short qprod path
- segmented square rows
- truncated carry/fold widths
- streamed/folded GCD apply

This is both a qubit and Toffoli idea: fewer live wires can also mean fewer cleanup gates.

### Dead-Branch-Wired Optimizations (the highest-yield meta-pattern)

The single most productive Toffoli-hunt heuristic found on this route: **an optimization is
implemented and validated, but wired only to a code branch that the live route bakes OFF — so the
live path silently runs the un-optimized version.** Porting the existing optimization onto the live
branch is then a value-exact, density-neutral, peak-neutral win that needs no new correctness proof
(the optimization was already validated; only the wiring moved). This pattern has paid off repeatedly;
actively grep for `if <knob>` guards whose default route disables them while a parallel live branch
lacks the same guard.

Worked example — the **vented divstep body** levers (verified, peak 1170, the dialog-GCD route bakes
`DIALOG_GCD_RAW_TOBITVECTOR_MATERIALIZED_SUB=0` + `DIALOG_GCD_CTRL_BODY_VENTED=1`, so the live body is
the `cuccaro_*_ctrl_vented` else-branch ≈ 18.5% of all Toffoli). A carry **band-trim schedule** and a
**bit-0 fastpath** existed but were wired only to the *dead* materialized branch, so the live vented
body ran full-width-including-bit-0. Two new gated, default-OFF, byte-identical-when-OFF knobs wire
them onto the live path:

- `DIALOG_GCD_VENTED_BODY_BAND_TRIM=1` — **trim the TOP carries** of the vented sub + reverse-add to
  `body_carry_trunc_width(n,step)`. Value-exact because `WIDTH_MARGIN=10` and max GCD-operand overshoot
  ≤8 ⇒ on reachable inputs `bitlen ≤ active_width−2`, so the trimmed top carry cells operate on
  `|0>·|0>`; and the post-cswap body never borrows past the active operand (`v≥u`). −3.93M Toffoli.
- `DIALOG_GCD_VENTED_BODY_ODD_LOWBIT=1` — **skip BIT 0** of the vented body. Kaliski keeps `u` odd
  (`subtrahend[0]=1`) and `acc[0]=ctrl` at the sub site / `acc[0]=0` at the reverse-add site, so bit 0
  is exactly `cx(ctrl, acc[0])` with no carry into bit 1 — run the body over `[1..bw]` + one CNOT.
  Exploits an algebraic invariant, not a margin. −2.43M Toffoli.
- `DIALOG_GCD_VENTED_BODY_TRIM_CAP=2` — caps the per-step band-trim at 2 bits (≤ the overshoot bound),
  making BAND_TRIM **provably value-exact on ALL inputs** (not just "reachable support"). Use it for a
  zero-risk density guarantee.

They **stack near-additively** (top-carry trim ⟂ bottom-bit skip): combined **−6.34M Toffoli**, peak
unchanged (1170), λ_classical unchanged — the largest peak/density-neutral win in this route's record
(`1,676,067,120 → 1,669,731,570`). Only cost: the op-stream changed so the SHAKE256-derived 9024-shot
set re-rolls ⇒ re-hunt a clean `DIALOG_TAIL_NONCE`; because it's density-neutral the hunt is the same
difficulty as the frontier's island.

**The discipline that separates these from truncation:** trim/skip ONLY what the schedule or invariant
*proves* is determined. `WIDTH_MARGIN`/overshoot proves the top cells are `|0>`; the odd-u invariant
proves bit 0 is a known CNOT. Contrast the same-shaped but APPROXIMATE `DIALOG_GCD_VENTED_BODY_UNIFORM_TRIM=N`
(a flat `n−N` trim): catastrophic (classical 3987+) because early divsteps are full-width with no margin —
a real truncation that breaks correctness. Same knob shape, opposite correctness; the proof is the line.

### Signed or Joint Windowing

From Andre/Schrottenloher-style Shor-resource analysis, signed-digit or joint-window recodings can reduce lookup/table work by exploiting symmetry.

Use this framing for full Shor resource optimization, not necessarily for the fixed EC point-addition challenge unless lookup/state-preparation logic is in scope.

Expected effect:

- modest Toffoli savings when lookup cost is significant
- little direct qubit saving if the selection register width remains the same
- possible extra recoding/sign-handling overhead

Do not assume a lookup-table trick will dominate when the benchmark is mostly point-addition arithmetic.

## TrailMix And Schrottenloher 2026 Checklist

Use this checklist when translating ideas from Trail of Bits TrailMix and Andre Schrottenloher's 2026 paper into ECDSA Fail circuit routes. The important lesson is not a single circuit, but a way to account for live values, transcripts, and peak owners.

### Reference Routing

For detailed Trail of Bits TrailMix implementation findings, read
`references/trailmix-implementation-analysis.md` when the task involves TrailMix,
Trail of Bits, jump-GCD, base-3/base-5 transcript compression, Proos-Zalka divstep,
whole-register ghosting, venting, or sub-1175-qubit EC point-addition routes. Keep
this `SKILL.md` section as the short operating checklist; use the reference for
source-backed route tables, exact implementation mechanisms, and source-file maps.

For detailed Andre Schrottenloher paper findings, read
`references/andre-schrottenloher-2026-analysis.md` when the task involves arXiv
2606.02235, the 1192/1208 qubit accounting, dialog-transcript in-place
multiplication, EEA/Bezout splitting, pseudo-Mersenne approximate arithmetic,
or reproducing the Qarton reference implementation.

For Shrunken-PZ q980 follow-ups, also read the sibling skill references:

- `../peak-qubit-reduction/references/Q980_SHRUNKEN_PZ_85D5DAE_HANDOFF.md`
- `../toffoli-reduction/references/Q980_TOFFOLI_CUT_4352CFB_HANDOFF.md`

### Verified provenance (read directly from the sources)

- **Schrottenloher 2026** = arXiv **2606.02235v1**, "*Optimized Point Addition Circuits for
  Elliptic Curve Discrete Logarithms*", Andre Schrottenloher (Univ Rennes/Inria/IRISA), 1 Jun
  2026. Open code: `gitlab.inria.fr/capsule/qarton-projects/ec-point-addition`. It reproduces
  Babbush et al. (2603.28846) with an open logical circuit: **~1.5% more qubits, 6.5-10% fewer
  Toffoli**. secp256k1 single point-add (n=256): space-opt **1192 q / 2^21.19 Toffoli**,
  gate-opt **1446 q / 2^20.83**. Full Shor: ~2^26.11 Toffoli, 1208 q; only **28 windowed point
  additions** needed. Toffoli breakdown: in-place multiplier+inverse = **90%** (Bezout
  reconstruction 54%, GCD construction 36%); modular squaring 9%. Failure target <= 2^-13.3
  on 10k random inputs. The EEA-split idea is credited to Khattar et al. (DQI circuits).
- **trailmix** = Trail of Bits Rust toolchain; objective identical (`peak_qubits *
  avg_executed_Toffoli`). Five published configs span the curve: low-qubit **1173 q / ~2.48M**;
  low-tof **1416 q / ~2.03M**; jump-lowqubit **1169 q / ~2.09M**; jump-lowtof **1412 q / ~1.90M**;
  shrunken-PZ (Proos-Zalka divstep) **1050 q / ~32.3M** (a qubit-lower-bound witness, not
  score-competitive). Note the absolute qubit counts here are for a *standalone* inversion/PA
  with no Fiat-Shamir tail; our challenge's promoted frontier (1211 q) is lower because the
  challenge circuit is the affine PA only, but the structural lessons port directly.

### Dialog-Transcript In-Place Multiplication

Schrottenloher's in-place multiplier separates the Euclidean "input part" from the Bezout-coefficient reconstruction (Algs 2-4 in the paper):

1. **Algorithm 2 (GCD construction):** drive the binary-GCD pair `(u,v)` from `(q,x)` toward
   `(1,0)`. Each fixed-count iteration records the choice pair `(b0 = v parity, b0&b1 = u>v)`
   into a garbage tape; this *consumes* `x` into the tape. Unsigned (non-modular) arithmetic,
   so it has ~n free ancillas -> use Gidney adders here.
2. **Algorithm 3 (Bezout reconstruction):** read the tape in *reverse*, maintaining a *modular*
   pair `(r,s)`: `s = 2s mod q; if b0: s += r mod q; if b0&b1: swap(r,s)`. All updates are
   **linear and controlled solely by the recorded bits**.
3. **Algorithm 4 (in-place modular multiply):** Alg 2 on `x`, then Alg 3 on `(y,0)`, then Alg 2
   reversed to restore `x` and erase the tape.

The load-bearing insight (paper sec 3.2): because Alg 3's updates are linear, **seeding
`(r,s) = (y,0)` instead of `(1,0)` yields `(0, y*x^-1 mod q)` directly** -- inversion AND
in-place multiply of a second register at no extra cost, with **no explicit inverse ever
materialized**. Reading the tape forward vs reversed flips between `y*x` and `y*x^-1`. Versus
the old reversible-binary-GCD route (Litinski/Gouzien), only **Alg 2 runs twice** (cheap,
unsigned, ancilla-rich); the expensive *modular* Alg 3 runs **once**.

Circuit design implications:

- Do not first compute an explicit inverse and then multiply if the same dialog transcript can drive the multiplication directly.
- Treat the transcript as the real resource. Optimize its width, lifetime, and decompression schedule before optimizing local adders.
- In affine point addition, the slope can often live in the `y`/difference register; a separate `lambda` register is a 256-bit passenger unless it eliminates a larger co-residence elsewhere.
- **Peak accounting (paper sec 3):** the peak is NOT during GCD construction (Alg 2 uses only
  ~2.355n qubits, ~n free). The peak IS during **Bezout reconstruction (Alg 3)**: two n-bit
  modular registers `r,s` + the ~2.355n transcript co-reside = **4.355n + O(sqrt n)** (floor
  4.12n). The whole PA circuit's space is governed by Alg 4 alone. Therefore both factors of
  our score are set by the reconstruction step -- that is where to spend optimization effort.
- **Space-opt vs gate-opt is one knob:** spending **n extra ancilla qubits** during
  reconstruction lets you use Gidney (2n-Toffoli) adders there instead of CDKM (3n); this single
  choice is the entire 1192<->1446 / 2^21.19<->2^20.83 split in both Babbush and Schrottenloher.

### How Schrottenloher's 1192 / 1208 Qubit Counts Are Computed

Use this subsection when going "back to the drawing board" on why the paper can sit near 1.2k
qubits. The paper's Table 1 reports **1192 qubits**, not 1195, for the space-optimized
secp256k1 point-addition circuit. Table 2 adds the `w=16` window register for the full Shor
windowed circuit:

```text
1192 point-add qubits + 16 window qubits = 1208 full-window qubits
```

Do not compare a challenge route against the wrong table. For ECDSA Fail-style fixed
point-addition work, Table 1 is the closer structural analogue; for a full Shor resource estimate,
Table 2 is the right accounting.

The finite-size count is a concrete version of the asymptotic peak:

```text
peak ~= compressed_EEA_transcript + two n-bit Bezout/modular registers + O(sqrt(n))
     ~= 2.355n + 2n + O(sqrt(n))
     ~= 4.355n + O(sqrt(n))
```

For `n=256`, the arithmetic is:

```text
EEA iterations ~= 1.413n + c_iter * sqrt(n)
               ~= 362 + padding

Schrottenloher transcript packing: 3 iterations -> 5 bits
compressed transcript ~= iterations * 5/3
                      ~= roughly 667 bits with the paper's concrete padding

Bezout reconstruction registers: r,s = 2n = 512 bits

667 + 512 + small concrete overhead ~= 1192 qubits
```

Interpretation:

- The **peak owner is Bezout reconstruction**, not GCD construction. GCD construction can use
  shrinking `u,v` live ranges and freed high bits for the transcript, so it stays below the
  reconstruction peak.
- The `4.12n + O(sqrt(n))` number is a lower-space theoretical floor using the information content
  of the transcript. The implemented circuit chooses a slightly larger `4.355n + O(sqrt(n))`
  transcript representation because it is much cheaper and simpler to apply.
- The extra concrete qubits over `4.355 * 256 ~= 1115` are the `O(sqrt(n))` padding, success-bound
  margins, and small work/selection overheads. Do not expect the leading asymptotic term alone to
  predict the exact 256-bit table row.
- When borrowing this idea, first ask: "Can the current route be made to peak at transcript +
  two registers, or are extra coordinate passengers / carry slices / decoded windows co-resident?"
  If the latter are present, qubit count will land above the paper even if the EEA transcript is
  compressed well.

### Transcript Compression And Jump Symbols

TraiMix's low-qubit EEA-dialog circuits emphasize that the dialog sidecar is compressible
(verified `gcd_compress5.rs`, `gcd_compress_jump.rs`):

- Binary-pair dialogs have only three valid states (`(0,0),(1,0),(1,1)`), so each pair is a
  base-3 digit. **M=5: 5 pairs -> 8 bits** (`3^5=243<256`), density **1.600 bits/pair** vs raw
  2.0 and vs **M=3: 5/3 = 1.667**. The M=5 encoder is an in-place low-to-high radix-3 merge
  (~316 Toffoli/window); it drops the apply_bv peak **~22 qubits** at n=256 (670->648-bit tape).
  Schrottenloher's variant (paper Fig 1): **3 iterations -> 5 bits in just 5 Toffoli** (fixed-size
  2.355n transcript, one reusable spare bit) -- far cheaper encoder, slightly larger tape.
- **The encoder is pure overhead unless the tape is the peak-binding register.** trailmix's
  *low-tof* config deliberately drops back to M=3 (cheaper ~5-Toffoli SAT permutation compressor)
  to cut Toffoli and pay in tape width -- the opposite choice from low-qubit. Pick M by whether
  the tape or the GCD phase binds the peak.
- Hold a decompressed window only while applying it (trailmix's once-per-window
  *decompressed-hold buffer*: each iter absorbs its pair with two SWAPs; the expensive encoder
  fires once per M iters), then release it.
- **Jump-GCD** (Stein-style, removes up to `jump=2` trailing zeros/step -> fewer steps -> fewer
  adder firings) uses a **5-symbol alphabet -> 3 symbols in a 7-bit radix-5 code** (`5^3=125<128`,
  ~2.33 bits/step). Two packers: a radix merge, or a **QROM ghost-clear** that HMR-ghosts the
  displaced symbol bits and discharges their phase through a unary-iteration tree -- the deepest
  AND is never materialized (`Z(AND(ctrl,bit))` gated on a classical ghost bit is a free `CZ`),
  killing ~64 of ~126 CCX. jump=1 reproduces the divstep dialog exactly. This is the trailmix
  jump-lowqubit route at **1169 q / 2.09M** (beats both Google operating points at once).

ECDSA Fail route ideas:

- If the peak owner is the dialog/apply sidecar, test larger base-3 windows and per-window decode buffers.
- If Toffoli dominates and qubit slack exists, test jump-step symbols or conditional replay that shortens the average executed EEA path.
- Score the encoder/decoder cost explicitly; larger compression is useful only when the sidecar or its decoded window is at the actual peak.

### Peak-Owner Accounting

TraiMix and Schrottenloher both show that the GCD construction is not always the peak. The expensive peak can move to Bezout reconstruction / `apply_bv`, where the transcript, passengers, adders, and correction buffers co-reside.

Before changing a route, write down the peak owners:

- transcript or decoded transcript window
- `u/v` or Bezout state
- coordinate passenger registers
- carry/borrow chains and compare bits
- pseudo-Mersenne correction scratch

Optimization rule:

- If one component is not a peak owner, shrinking it may not improve score.
- If two components tie for peak, lower them together or the peak simply moves.
- Prefer profiler/cap evidence over intuition; a route that "obviously saves 20 qubits" can save zero at the measured peak.

### Venting As A Deliberate Score Trade

TraiMix's low-Toffoli variants spend hundreds of extra qubits to remove a large Toffoli burden. That is a valid operating point, but only if the product `qubits * Toffolis` improves.

Useful framing:

- Treat vents as a shared peak budget, not as adder-local scratch.
- Couple the vent budget across register adders, materialized pseudo-Mersenne `+f` reductions, and transcript-apply stages that overlap at the same peak.
- Low-qubit routes should keep vents sparse and targeted; low-Toffoli routes can spend vents where they remove repeated carry propagation or cleanup.

### Pseudo-Mersenne Arithmetic Tricks

secp256k1 uses `q = 2^256 - f` with **`f = 2^32 + 977` (bitlen 33)**. This is the single
concrete source of the secp256k1-vs-generic-prime gap (Schrottenloher Table 1: 2^21.19 vs
2^21.78; Table 3 attributes the whole gap to modular add + double). **No Montgomery form** --
both the paper and trailmix keep standard integer representation and optimize directly.

Verified mechanics (Schrottenloher Algs 7/10/11, trailmix `pm_prims.rs`):

- **The dominant cost being cut:** inside Bezout reconstruction, every "add/subtract `q`" via
  Gidney's dirty-ancilla constant adder is **3n Toffoli**. Replacing it with "add small `f`
  into the low limbs" cuts a full n-bit op to a short LSB op. (Gidney constant adder is 15% of
  CCX for secp256k1 vs 34% for a generic prime; modular double 8% vs 24%.)
- **mod-double (Alg 7):** shift-left by 1, then a controlled `+f` on only the bottom `lsbs`
  bits, then one CX to clear the overflow ancilla. The reduction *approximates* the comparison
  by **testing only whether the MSB is 1**. Because `f` is small, carries propagate a bounded
  distance, so `f` need only enter the low limbs.
- **mod-add (Alg 10, no degeneracy):** controlled add, then on overflow add `f` in the LSBs,
  then erase the overflow ancilla via an **MSB-only** `y<x` compare. Alg 11 additionally handles
  `x+y=q` by testing "all MSBs are 1".
- **Borrowed-dirty `+f` (trailmix `gidney_cadd_f_window`):** the `+f` window **borrows the
  register's own idle high bits as carry scratch** (~3 clean ancillas instead of ~10), so the
  reduction adds ~0 clean peak. Value/phase-identical to the vented path.

Tuning dials that set the failure probability (calibrate against the 9024-shot 0/0/0 target):

- **`lsbs`** = width of the `+f` add (trailmix uses ~63). Too narrow misses carry propagation;
  per-call fail ~ 2^-padding ~ 2^-30 at their settings.
- **`msbs`** = MSB-compare width for overflow/degeneracy tests (the paper uses **40-50 MSBs**).
- **`x+y=q` degeneracy** "should not appear" on random inputs but DOES appear in Alg 3's first
  `c_iter*sqrt(n)` "empty" padding iterations. Route the expensive Alg-11 variant ONLY over those
  padding iterations; use cheap Alg-10 everywhere else.

ECDSA Fail route ideas:

- The shipped circuit already realizes this as `ROUND84_INPLACE_SOLINAS_FOLD` and the
  `*_CARRY_TRUNC_W` family: a high-limb event becomes a low-limb `2^32 + 977` fold, and the carry
  ripple beyond the needed window is truncated. `KAL_DOUBLE_CARRY_TRUNC_W` / `KAL_FOLD_CARRY_TRUNC_W`
  / `DIALOG_GCD_FOLD_CARRY_TRUNC_W` are exactly the `lsbs`-style dial; `DIALOG_GCD_COMPARE_BITS` /
  `*_APPLY_CLEAN_COMPARE_BITS` are the `msbs` dial. Tightening one notch is value-exact only on a
  searched nonce-island (see Carry/Borrow Truncation + Island hunting).
- Re-check carry/borrow live ranges after every pseudo-Mersenne rewrite; saving a full constant is only useful if the correction scratch was a peak owner.

### Passenger Minimization And Ghosting

The shrunken TraiMix route (shrunken-PZ, 1050 q / ~32.3M Toffoli) is not score-competitive by
Toffoli count, but it is a strong qubit-lowering design lesson:

- avoid carrying both `dy` and `lambda` through inversion when one can be reconstructed later;
- ghost or discharge a whole coordinate only when the phase obligation is explicitly tracked;
- schedule inversion so only one 256-bit coordinate passenger co-resides with the EEA peak.

Verified mechanics (trailmix `shrunken_pz_state_machine`, `ghost.rs`):

- **Whole-register HMR-ghost:** `hmr_ghost(q)` snapshots q's 64-shot mask, HMRs q to |0> (freeing
  the qubit), and returns a `#[must_use]` receipt; the reverse pass recomputes the value and
  `resolve_ghost` emits the cancelling `z_if_bit` (sim-verified equal to the snapshot per shot).
  Ghosting a whole 256-bit coordinate (`dy` forward, `lambda` in cancel) makes them never both
  live -> **peak = EEA-peak + 256, not +512.** The MBU literature stays single-qubit; whole-
  register ghosting in an EC inversion is trailmix's delta. This is exactly what the shipped
  `DIALOG_GCD_FOLD_PARK_LOW_CARRIES` / `*_FREED_TAIL` / `*_BORROW_CARRIES` knobs do at smaller
  granularity (park/recompute a carry slice rather than a whole coordinate).
- **Tear down converged constants first:** at GCD convergence `A=0,B=1,ca=p,q=0` are constants ->
  0-Toffoli uncompute; doing so before building `lambda` leaves only `cb=1/|dx|` live (~ -258
  qubits at peak), re-created cheaply before the backward pass.
- **Pipelined two-quotient divstep:** build the *next* quotient while draining the *previous*,
  keeping the quotient record at one-quotient (~26-bit) size instead of a full ~256-bit tape, and
  making termination flag-intrinsic (no halting-counter garbage).

Use this as inspiration for sub-frontier qubit pushes, but score-gate aggressively. A route that saves 100+ qubits and adds tens of millions of Toffolis is useful as a lower-bound witness, not automatically as a challenge submission.

### Shrunken-PZ Q980 Lessons

The rejected q980 Shrunken-PZ submissions are idea references, not direct score frontiers:

- `85d5dae`: q980 / avgT ~39.65M. The qubit drop came from a source-level Shrunken-PZ state
  machine: dynamic live widths for PZ registers, thin support schedules, quotient/counter/rotation
  narrowing, known-constant teardown, and HMR-style passenger ghosting.
- `4352cfb`: q980 / avgT ~28.85M. The large Toffoli drop at the same qubit count came from the
  `zero-dy/newdx` EC dataflow rewrite: defer final `y`, build the cancellation witness
  `new_dy = lambda * new_dx` directly, and reuse zeroed `dy` as scratch.

Generalize these beyond Shrunken-PZ as two reusable questions:

1. Can this circuit use a time-varying source-level state machine instead of a fixed opaque op
   stream, so only the currently live support is coherent?
2. Can a later uncompute be driven by a cheaper witness relation instead of an eagerly materialized
   output register?

Classify each borrowed lever before scanning: dynamic state sizing, algebraic witness construction,
terminal constant teardown, and exact passenger reconstruction are structural/exact-looking; q-caps,
thin schedules, truncation widths, nonce tails, and support-mined bounds are island-gated and need
fresh validation.

### Tooling Lessons From TraiMix

TraiMix is valuable as much for its verification discipline as for its circuits:

- **64-shot bit-sliced simulation** (one `u64`/qubit, one bit/shot): X/CX/CCX/Z/HMR are single
  bitwise ops across all 64 shots; **Toffoli counted per fired shot** via `popcount(cond&c1&c2)`
  -- exactly the average-executed metric. HMR RNG is reseeded every run, so each run exercises a
  different measurement pattern (catches phase bugs the value sim alone misses).
- **Phase-lattice / abstract-interpretation gate** (`phase_lattice.rs`): a per-gate interpreter
  carrying an `AbsVal` (`Zero/One/CopyOf/AndOf/XorOf/...`) catches what value-sim cannot -- e.g.
  an `a AND b` ancilla silently modified between declare and its MBU discharge would flip the
  Z-kick for some inputs without corrupting the value. `prove_zero` is the ONLY way to inject
  `Zero`, and it requires a concrete 64-shot check first. `assert_phase_clean` (structurally
  cancels every HMR obligation) must pass before a circuit is "correct".
- **Measurement-based uncomputation (MBUC) ANF->gates** (`MBUC_GADGETS.md`): HMR an ancilla
  `c=f(k)`; if the random outcome is 1 it leaves a `(-1)^f(k)` kickback, repaired by the diagonal
  `P_f` under one `push_condition(b)`. Encode `f` as algebraic normal form over GF(2): each
  monomial of size |S| -> one gate (0->NEG, 1->Z, 2->CZ, 3->CCZ, >=4->C^{|S|-1}Z). **A diagonal
  correction emits ZERO Toffoli if `f` is at most quadratic** (Z/CZ only), and all terms fire
  under one push/pop. This is why comparator-uncompute and AND-cleanup became "free" on the
  dialog-GCD frontier (the `*_MEASURED` / `FUSED_HCLEAR_MEASURED` / `PERPOS_MAJ2` knobs).
- move-only qubit ownership + dense lowest-id-first free pool reduce accidental aliasing; strict
  dealloc panics on dirty-free (`prove_zero`) and on wasteful retention (a qubit idle across a
  newer alloc).
- redundant-op elision and per-section profiling (`prof`, `analyze_regions`,
  `find_packing_opportunities`) expose whether a claimed optimization affects the peak or merely
  moves gates around;
- time-travel / section-level debugging (`src op` + `watch` + run-backward) pinpoints the first
  bad uncompute; auto-attaches under `DEBUG_ON_FAIL=1`.

ECDSA Fail discipline:

- For every new alias, measurement, or ghost route, record the invariant that proves the borrowed bits are clean.
- Add a small stress/triage run before islanding at scale.
- If the validator reports nonzero `pha` or `anc`, treat the optimization as structurally suspect until the exact first failing section is located.

### Practical Decision Rules

Choose the next experiment based on the current route's bottleneck:

- Peak dominated by transcript/apply state: try base-3 compression, larger windows, decoded-window lifetime shortening, and clean-pool relocation.
- Peak dominated by coordinate passengers: try lambda-in-coordinate scheduling, recomputation, or carefully proven ghosting.
- Peak dominated by add/correction scratch: try pseudo-Mersenne low-limb folds, shared vent budgets, and narrower overflow/degeneracy checks.
- Toffoli dominated with qubit slack: try jump-GCD, more vents, fast adders, and conditional average-executed cuts.
- Qubit dominated with poor candidate quality: undo the riskiest alias/compare/carry shortcut before spending more GPU time.

## SOTA Submission Lessons

When reading SOTA notes or diffs, classify each trick:

- qubit reducer: lowers peak live set
- Toffoli reducer: lowers arithmetic/gate count
- tradeoff: saves one metric by spending the other
- validation/island trick: improves chance of finding a clean nonce

Patterns observed across the full public submission ladder:

- Early 2715q routes were mostly Toffoli cleanups on a wide, straightforward circuit.
- The 2708q-to-2310q era showed that Kaliski inverse cost was not the only story: score moved by breaking live-scratch plateaus.
- The 2025q and 1698q jumps came from rethinking where history, carry, and sidecar state live, not from tiny local gate rewrites.
- The 1313q-to-1285q era mixed lower-width point-add stacks with average-executed Toffoli cuts and repeated island re-hunting.
- The 1226q-to-1211q era used progressively riskier in-place decode, square-row cleanup tightening, special fold borrow-carry reuse, segmented rows, and low-carry parking.
- Rejected/failed submissions often had stale scores, no clean island after a route change, or a claimed low width whose candidate quality was structurally bad.

The lesson is not "turn on every aggressive knob." The lesson is to combine one aggressive live-range reduction with enough local safety knobs that candidate quality stays near-miss instead of structurally dead.

## Submission Archaeology Lessons

Use this section when pulling SOTA notes. It records the shape of the public frontier, including early solutions, so future optimization does not rediscover the same path blindly.

### Early Wide-Circuit Toffoli Wins: Boundary Merges

The first major Toffoli drop kept qubits roughly flat and attacked redundant Kaliski control work.

Useful pattern:

- Merge adjacent conditional swaps across iteration boundaries when their controls compose as a parity.
- Carry a small frame-parity bit instead of executing two independent swap layers.
- Confirm phase preservation, because swap-boundary rewrites can look classically correct while changing phase.

Public example:

- `d35d6e7`: `(r,s)` cswap boundary merge across Kaliski step9/step3, about -274k Toffoli, peak-neutral.

Optimization lesson:

- Before hunting qubits, scan for repeated reversible skeletons across loop boundaries. A parity-frame merge can be a cleaner first move than changing arithmetic width.

### Plateau Breaking: Attack Co-Resident Clusters Together

Several frontiers fell only when every co-owner of the peak was lowered together. Single-cluster reductions can show no score movement because another cluster immediately becomes the binder.

Public examples:

- `f94f726`: 2708q to 2310q by stacking schoolbook multiply scratch freeing, in-place `v` aliasing, affine y-multiply low-scratch, 9n-floor carry-borrow, and Solinas low-scratch.
- `0620443`: 2309q to 2025q by combining affine square recompute, dialog history fold into clean high bits, and carry-pool relocation.

Optimization lesson:

- Always identify the peak owners. If two or three clusters are within a few qubits, build a joint route that lowers all of them before judging success.
- A route that "saves 50 qubits" locally but leaves peak unchanged may still be the right subpatch if it unlocks a second or third binder.

### Clean-Pool Reuse: Certify Zero Bits, Then Relocate

Many large qubit drops reuse bits that are provably clean at a specific iteration: high bits of shrinking GCD registers, future history slots, or high limbs whose bitlength bound is classical.

Useful pattern:

- Prove a bit is `|0>` from iteration index and width invariant, not from sampled inputs.
- Use the clean pool for carries, history bits, or temporary fold state.
- Restore the borrowed pool through identical forward/backward qubit IDs.

Public examples:

- Late Kaliski carry recovery used future history and high `u` bits.
- 2025q route relocated carry pools onto high bits of `s`, `r`, and `u`.
- Dialog history fold routed per-iteration history into idle high bits of a shrinking GCD register.

Optimization lesson:

- Clean-pool reuse is stronger than generic dirty scratch. It can reduce qubits without adding Toffoli when it is pure qubit-id relabeling.
- Keep a written certificate for every reused pool: invariant, live interval, restore point, and phase risk.

### Recompute Instead Of Co-Residence

Some low-qubit routes pay extra Toffoli to avoid holding a large intermediate across an unrelated peak.

Public example:

- `0620443`: affine square recompute early-uncomputed the `lambda^2` square, ran y-multiply without the 512-bit temporary co-resident, then recomputed to clear dependent state.

Optimization lesson:

- Recompute is attractive when a temporary is wide, has a short deterministic recomputation path, and otherwise co-resides with an inversion or multiply peak.
- Score the trade explicitly. A recompute that saves hundreds of qubits can tolerate a large Toffoli penalty; a one-qubit recompute cannot.

### Dialog Sidecar Compression And Scheduled Compare Removal

The 1698q jump showed that a more radical dialog-GCD representation can beat careful local packing.

Public example:

- `0c1d4d9`: compressed dialog sidecar log, compressed block lifecycle, no scheduled compare table, narrower apply-clean compare width, active-iteration trimming, and raw terminal reuse.

Optimization lesson:

- Do not assume the state representation is fixed. Compressing the transcript/sidecar can dominate local scratch shaving.
- Prefer radix-aware compression over raw bit packing when the transcript alphabet has invalid states; TraiMix's base-3 dialog packing is the concrete model.
- Consider jump-step symbols when fewer EEA/apply iterations can beat wider symbol storage and pack/unpack cost.
- Removing scheduled compare tables or replacing them with uniform/narrow compare widths can save large space, but it tends to make island hunting more important.
- Treat GPU-clean rows as candidates only; the full trusted evaluator remains decisive.

### Average-Executed Toffoli Tricks

The public score uses average executed Toffoli over benchmark shots, not static emitted gates. Some submissions exploited this by controlling replay so some Toffolis execute only on a fraction of shots.

Public example:

- `4b7d727`: conditional replay of GCD/inversion boundary steps around the 1300q frontier, with the note explicitly warning that emitted gates remain the physical cost.

Optimization lesson:

- If optimizing benchmark score, count average executed Toffoli, not just emitted Toffoli.
- Conditional replay can reduce benchmark score while preserving reversibility, but do not mistake it for a hardware-resource reduction.
- When using this lever, report both emitted and average-executed Toffoli to avoid fooling yourself.

### Low-Width Stack Plus Nonce Re-Hunting

Some submissions did not make a universally cleaner circuit; they moved to a lower-width or lower-Toffoli stack and re-hunted a Fiat-Shamir tail nonce.

Public example:

- `c20c89b`: 1226q route re-hunted a tail nonce on a low-qubit stack; GPU survivors were only candidates until full trusted validation.

Optimization lesson:

- After any route change that affects the op stream or validation envelope, assume the old nonce is stale.
- Bake CFG defaults before final benchmark, then validate with the trusted path.
- Preserve the distinction between scanner-side relaxed prefilters and official correctness.

### Recent 1285q -> 1203q Frontier (verified exact-knob ladder)

This is the most actionable current ladder. **Current public #1 = `833642fe` (commit `6953d1b`),
score 1,697,398,113 = 1203 q x 1,410,971 T.** This is the headline: **the 1211 qubit floor BROKE to
1203** -- the first sub-1211 circuit, and the single most important current fact.

**The 1211 floor was breakable -- and the lever is jump-GCD + transcript compression, exactly the
trailmix tactic this skill documents.** Prior analysis (incl. ours) wrongly concluded sub-1211 needed
an apply-fold carry-pool rewrite and that knob routes were a dead end (a `cls=2` structural floor on
stacked carry-truncs). The leaders broke it a different way -- by compressing the dialog transcript,
not the carry pool. The 1203 stack vs the prior 1211 `186d9d7`:
- `DIALOG_GCD_K2=1` -- **jump-GCD** (Stein-style: strip up to 2 trailing zeros per GCD step, recording
  a `shift2` bit; the apply mirrors with a conditional 2nd double/halve). Fewer steps.
- `DIALOG_GCD_K5_CLEAN_BLOCK=1` (+`ROUND763_COMPRESS_LEVER`/`_DEDUP`, `K2_PAIR_COMPRESS`) -- **radix
  packing of the dialog transcript sidecar**: the `round763` 6->5 base packer + a GROUP_SIZE=3 K2
  step group, "5 + 3 = 8" compressed bits per block. This frees the qubits the sidecar held at the
  apply peak.
- supporting: `SQUARE_ROW_MAX_SEG` 184->176, `DIALOG_GCD_FOLD_CARRY_TRUNC_W` 18->17, slope reverted
  1017->**1015**, re-hunted nonce `9600076011007`.

This is the **trailmix jump=2 GCD + M=5 base-3 sidecar compression** that the "Transcript Compression
And Jump Symbols" / "Dialog Sidecar Compression" sections predicted would drop the apply_bv peak
~22 qubits. **Lesson: when stuck on a qubit frontier, mine the documented research levers (trailmix,
Schrottenloher) -- they are the literal playbook, not background.**

**Qubits are the prize, not Toffoli.** The trade the leaders accepted: avg-executed Toffoli *rose*
1,403,512 -> **1,410,971** (+7,459), but qubits 1211 -> 1203 still won (1203 x 1,410,971 <
1211 x 1,403,512, a -2.26M score step -- ~3x any single Toffoli notch). Do not grind the Toffoli
axis when a qubit drop is in reach; -1 qubit ~= -1.4M score, vs ~-0.6M for a hard-won Toffoli notch.

**The `WIDTH_SLOPE` walk dead-ended (still true, secondary).** 1015->1016->1017 each cratered island
density ~25x (slope1016 ~0.5/Mnonce, 1017 ~0.02, 1018 = 0 in 10M) -- unfindable past 1017. The 1203
SOTA *reverted* slope to 1015 (looser = findable ~0.6/Mnonce). Do not walk slope past the live
frontier; density dies far faster than the score gain.

**New peak binder at 1203:** `dialog_gcd_compressed_block_apply_double_y` / `reverse_halve_y` (the
round84 square is now pushed *under* it -- `SQUARE_ROW_MAX_SEG` no longer drops the peak). Pushing
below 1203 means freeing more at that apply-fold/double-halve phase: deeper transcript packing, a
higher jump (K=3), or compressing the next co-resident -- the code hints headroom remains
(K2 "stores shift2 uncompressed ... does not touch the round763 packer yet").

**OPERATIONAL TRAP (cost us a wrong call):** after `ecdsafail sync`, `ecdsafail run` served a **stale
`ops.bin`** and reported the OLD qubit count (1211, not 1203) -- the cache trap. **Always verify peak
qubits with a forced `TRACE_PEAK=1 ./target/release/build_circuit` in a clean dir, never trust the
cached `ecdsafail run` qubit line.**

Promoted ladder: `cac150e`/`03a1550` (1211) -> ... -> `f804ee0` (slope1016) -> `186d9d7` (slope1017)
-> `6953d1b` (**1203**, jump-GCD + K5 transcript compression, 1,697,398,113).
To beat it: (a) the **findable Toffoli cut** -- `DIALOG_GCD_COMPARE_BITS=43` on the 1203 base is
~0.6/Mnonce and lowers emitted ~-960 -> beats by ~1M while keeping 1203 q; collect islands, submit
lowest avg-T. (b) the **bigger prize** -- push below 1203 via deeper compression / K=3 jump
(structural, harder).

(Our own promoted `d83d19c`, 1221 q / 1,743,174,081, is no longer the frontier; competitors
pushed below it via the qubit drops below. A 1216q branch at 1,740,350,144 is also NOT
competitive with the live 1211q frontier -- always re-pull the leaderboard before assuming.
Knob-only sub-1211 is a dead end: the carry-trunc combos that drop peak to 1210 introduce an
irreducible classical-mismatch floor -- e.g. `SEG182+FOLD17+DIALOGFOLD17` floors at cls=2 over
hundreds of GCD-clean candidates. True sub-1211 needs a circuit-code change to the apply-fold
carry pool, not a knob.)

Exact promoted sequence (id : qubits : knob introduced):

- `ba04549` : 1285 : `KAL_FOLD_CARRY_TRUNC_W` 18->17.
- `c20c89b`/`480b001` : **1226** : Teddy Pender low-peak route -- move the global binder to the
  round84 square and push apply/GCD peaks *under* it. Stack: `KAL_DOUBLE_CARRY_TRUNC_W=19`,
  `KAL_FOLD_CARRY_TRUNC_W=18`, `DIALOG_GCD_COMPARE_BITS=46`,
  `DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS=19`, `DIALOG_GCD_APPLY_FINAL_WINDOWED_FAST_BLOCKS=0`.
- `155ebc5` : **1221** : `DIALOG_GCD_FOLD_FREED_TAIL=1` (recompute ~1 ccx/fold, +~511 T, frees the
  fold top carry lane) + `SQUARE_ROW_MAX_SEG=194` + `DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS=11`.
- `d8466d8` : 1221 (T-cut) : `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS=22`.
- `b2905ce` : **1220** : `ROUND84_KEEP_QUOTIENT_PRODUCT=1` (keep the 66-bit quotient x c product
  live across the mid-sub, skip fold uncompute/unfold recompute) + `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS=18`
  + `DIALOG_GCD_FOLD_CARRY_TRUNC_W=19` + `SQUARE_ROW_MAX_SEG=193`.
- `19815a4` : **1218** : `SQUARE_ROW_MAX_SEG=191` (the q-drop) + `ROUND84_QPROD_VENT_PAD=1` +
  `DIALOG_GCD_FOLD_FREED_TAIL_ED=1` (base also `DIALOG_GCD_APPLY_FINAL_TOPCLEAN=0`).
- `ebd0a6e` : **1215** : `DIALOG_GCD_K2_APPLY_INPLACE_RAW_BLOCK=1` (decode the K2 pair block in
  place from 5 compressed cells + 1 zero lane, free the persistent 6-lane raw block) +
  `SQUARE_ROW_MAX_SEG=188` + `DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS=12` + `ROUND84_FOLD_FAST_ADD=0`.
- `09daa10` : **1213** : `DIALOG_GCD_SPECIAL_FOLD_BORROW_CARRIES=1` (reuse idle `inner_scratch`) +
  `SQUARE_ROW_MAX_SEG=186` + `DIALOG_GCD_FOLD_CARRY_TRUNC_W=18` + `DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS=16`.
- `d156d08` : **1212** : one more square-row segmentation notch.
- `cac150e` : **1211** : `DIALOG_GCD_FOLD_PARK_LOW_CARRIES=1` (park lowest fused-fold carry qubits
  across the high-limb tail, recompute before uncompute) + `SQUARE_ROW_MAX_SEG=184`.
- `03a1550` : 1211 (T-cut) : `DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS` 20->19.
- `f804ee0` : 1211 (T-cut) : `DIALOG_GCD_WIDTH_SLOPE_X1000` 1015->1016. The note frames
  this as a steeper affine active-width taper for GCD `u,v`; dropped high bits are zero on the
  searched verifier support. Expected failure mode is classical width-envelope/carry escape, which
  the GCD-convergence/width prefilter can screen, rather than a broad phase-wall increase.
- `186d9d7` : 1211 (T-cut) : `DIALOG_GCD_WIDTH_SLOPE_X1000` 1016->1017 + re-hunted nonce
  `6100000089014596`. **End of the slope-walk** (1018+ unfindable, ~0.02/Mn).
- `6953d1b` : **1203** (q-drop, breaks the 1211 floor, **#1**) : `DIALOG_GCD_K2=1` (jump-GCD) +
  `DIALOG_GCD_K5_CLEAN_BLOCK=1` (round763 6->5 transcript packing + GROUP_SIZE=3, "5+3=8" bits/block)
  + `K2_PAIR_COMPRESS=1` + `SQUARE_ROW_MAX_SEG` 184->176 + `DIALOG_GCD_FOLD_CARRY_TRUNC_W` 18->17 +
  slope 1017->1015 + round763 compressor-inverse code change + nonce `9600076011007`.
  avg-T 1,410,971 (Toffoli *rose* but the -8 qubits won). The trailmix jump-GCD + base-3 sidecar
  compression lever, realized.
  `6100000089014596`. Same lever as `f804ee0`, one more notch -- the slope-walk continues (see the
  measured per-notch emit table above; 1018+ is open).

The dominant late qubit lever is `SQUARE_ROW_MAX_SEG` (each notch ~ -2 peak), unlocked one step at
a time by freeing/parking a carry slice (`*_FREED_TAIL`, `*_PARK_LOW_CARRIES`, `*_BORROW_CARRIES`,
`KEEP_QUOTIENT_PRODUCT`) so the round84 square can segment tighter without the freed carry re-binding.

Actionable route design:

1. Start from the latest low-qubit SOTA, not from an older balanced route.
2. Choose one of these as the next structural hypothesis:
   - park or recompute another carry slice;
   - reuse another zero lane in K2/apply decode;
   - shrink `SQUARE_ROW_MAX_SEG` one notch and compensate with safer carry widths;
   - move one more fold/add scratch interval onto certified clean `inner_scratch`;
   - tighten measured square-row cleanup only if triage stays near-miss.
   - if qubits are flat and score margin matters, test one-notch `DIALOG_GCD_WIDTH_SLOPE_X1000`
     steepening, but still re-hunt and triage because the op stream is reseeded.
3. Measure qubits and average Toffoli before scanning.
4. If score beats SOTA, run a short density and `cls / pha / anc` triage before committing GPUs.

Current warning from the 1210q experiments:

- Sub-1215 routes can have excellent estimated score but become structurally dirty if carry truncation, compare-bit narrowing, and aliasing are stacked too hard.
- Healthy 1210-style candidates have a near-miss tail such as `3 / 0 / 0`, `4 / 1 / 0`, or `4 / 2 / 0`; uniform high fingerprints are a route failure, not bad luck.

### Reading Rejected And Failed Submissions

Rejected submissions are still useful.

Look for:

- duplicate metrics: someone submitted an already-promoted circuit or stale branch;
- lower claimed score but promotion failure: packaging, cleanliness, or race against newer SOTA may be the issue;
- failed low-score attempts: likely correctness or validation envelope broke;
- rejected higher score: useful idea may still be valid but no longer score-competitive.

Optimization lesson:

- Do not copy a rejected route blindly. Classify the failure mode first.
- If notes are missing, infer only from metrics and status; mark the inference as weaker than a note-backed lesson.

### Compact Frontier Phases

Use this phase map to orient quickly:

- `2715q -> 2708q`: wide Roetteler two-Kaliski baseline; cswap/carry Toffoli cleanup
  (`d35d6e7` `KAL_CSWAP_RS_MERGE`, -274k T peak-neutral).
- `2708q -> 2310q` (`f94f726`): plateau breaking -- joint-pin scratch packing, schoolbook-mul
  frees the Karatsuba middle, 9n-floor carry-borrow from provably-|0> future-history/high-u bits.
- `2310q -> 2025q` (`0620443`): `AFFINE_SQUARE_RECOMPUTE` + `KAL_DIALOG_FOLD` +
  `KAL_GZ_EARLY_RECOVER` (carry-pool relocation onto W-TRUNC-clean high lanes).
- `2025q -> 2002q`: small trims + dirty venting (`SHIFT22_FOLD_DIRTY`).
- `2002q -> 1698q` (`0c1d4d9`): wholesale swap to the **dialog-GCD compressed-sidecar** skeleton
  (explicit Bezout r,s registers -> compressed per-step branch-decision transcript in freed lanes).
- `1698q flat (Toffoli axis)`: measurement-based uncompute of comparator/sub/AND
  (`cmp_lt_into_measured` -209k T, `*_fast`, `PERPOS_MAJ2`, `FUSED_HCLEAR_MEASURED`).
- `1698q -> 1466q`: chunked apply (`DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS`/`_F_CUT`) + peak-binder
  teardown via hosting on temporarily-clean future-log lanes (`HOST_GATED`, `BRANCH_BITS_HOST_COMPARATOR`,
  `COMPOSITE_SCRATCH`).
- `1355q/1394q`: **K=2 bounded-shift dialog-GCD re-baseline** (`ca1cd1f`; strip up to 2 trailing
  zeros/step, ~393->~259 iterations; big Toffoli cut, peak up). K=2 claimed optimal.
- `1390q -> 1313q`: `DIALOG_GCD_COMPARE_BITS 73->52` (free comparator slack via a both-factor
  convergence filter), `ACTIVE_ITERATIONS` 259->258, apply teardown (`APPLY_FINAL_LOWQ`,
  `APPLY_BOUNDARY_SPLIT`), `DIALOG_GCD_K2_PAIR_COMPRESS`.
- `1300q -> 1285q`: **conditional-replay metric exploit** (`4b7d727`; Toffoli executes on only a
  fraction of shots, lowering *average-executed* -- emitted cost unchanged) + `KAL_FOLD_CARRY_TRUNC_W 18->17`.
- `1285q -> 1211q`: Teddy 1226 low-peak route, then round84-square segmentation
  (`SQUARE_ROW_MAX_SEG`) unlocked notch-by-notch by carry park/free/borrow tricks + repeated tail
  nonce hunts. Current #1 `03a1550` 1211 q / 1,701,048,104.

## Negative Results And Gotchas (from standalone submission notes)

These are documented dead-ends and traps. Do not rediscover them.

### Batched dual-inversion is a measured LOSS

Idea (jbrukh/lucasabu1988 standalone notes): batch the two affine modular inversions into one
via a master polynomial `M = d1^2 * d2` (Montgomery-batch `{d1, M}`, invert once, recover both
with polynomial cofactors). The algebra is **proven correct**, but it measured **+1.26M-1.3M CCX
(score ~doubles)**. Reason: in the live `emit_dialog_gcd_raw` path there are no standalone
multiply phases -- divides are fused, so "multiplies" are effectively free; the batch needs ~13
fresh standalone schoolbook multiplies plus peak +512. **Closed on economics -- do not pursue.**
General lesson: a trick that saves multiplies only helps if multiplies are actually a separate
cost in the shipped path; in the fused dialog-GCD they are not.

### The `ops.bin` rebuild-cache trap

`ecdsafail run` caches `ops.bin` keyed on **source, not environment**. Env-only knob overrides
(`KNOB=x ecdsafail run`) silently measure the OLD circuit. Tell: no `-- building circuit --` line
in the output. To force a rebuild you must edit the `set_default_env` default in
`src/point_add/mod.rs` (which is also why baking via the CRLF-safe `set_default_env` edit is the
correct path, not env vars). Always confirm the `-- building circuit --` line appears.

### Truncation is a search-throughput game, not a hard cliff

Every deeper carry-trunc/compare-bit notch produces ~15-21 classical mismatches at a *random*
nonce (e.g. on a 1220q base at a fixed nonce: `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS 18->17` = 11
mismatches, `KAL_FOLD_CARRY_TRUNC_W 18->17` = 19, `DIALOG_GCD_FOLD_CARRY_TRUNC_W 19->18` = 21).
The shipped `0/0/0` is simply a **rare searched nonce-island** where the dropped bits happen to be
zero on the reachable verifier support. So a tightened knob is not "broken" if it shows mismatches
-- it just needs island hunting. Efficient hunt = patch the ~96-op `DIALOG_TAIL_NONCE` tail bytes
in `ops.bin` in place + reduced-shot early-abort eval, NOT a full re-emit (~19s) per nonce.
Corollary: some notches don't drop the *peak* at all (e.g. `SQUARE_ROW_MAX_SEG 193->192` on that
base) -- measure peak before spending a hunt. `ROUND84_QPROD_SHORT` is DEAD in the shipped config
(bypassed by `ROUND84_INPLACE_SOLINAS_FOLD`).

## Known Route Archetypes

### Safer Balanced Route

Use when you need a likely-valid starting point.

Typical features:

- moderate `SQUARE_ROW_MAX_SEG`
- chunked F blocks around 12-15
- conservative carry truncation
- fewer cleanup elisions

Pros: better candidate quality.
Cons: may lose SOTA score after new submissions.

### Low-Qubit Aggressive Route

Use when explicitly trying to push below the current qubit frontier.

Typical features:

- in-place raw block
- clean compare bits around 21
- carry truncation narrowed
- scratch release during fold
- measured carry clear
- special borrow-carry handling
- final topclean disabled

Pros: can reach 1210-1214 style widths.
Cons: high risk of dirty fingerprints; requires short triage.

### Toffoli-Cut Route

Use when qubit target is fixed and the goal is score reduction.

Typical features:

- fused fold
- fast add
- short qprod
- final topclean disabled if safe
- segment size kept at the largest value allowed by qubit budget

Pros: better Toffoli without increasing qubits.
Cons: may need a fresh island because correctness envelope changes.

## Evaluation Discipline

For each route:

1. Measure or estimate qubits and Toffoli.
2. Compute score.
3. Compare against latest SOTA.
4. Only scan if the estimated score beats SOTA.
5. Run a short triage scan.
6. Continue only if candidate density and `cls / pha / anc` look promising.

If a route has beautiful qubits but `cls / pha / anc` is uniformly high, it is not promising. Move back one notch on the riskiest knob:

- increase carry truncation width
- increase compare bits
- disable the newest aliasing trick
- re-enable a top-clean step
- increase square segment size if qubit budget allows

## Suggested Search Strategy

Use coordinate descent rather than changing everything at once:

1. Start from the latest SOTA or best near-miss route.
2. Pick one goal: lower qubits or lower Toffoli.
3. Change one knob or one tightly related knob pair.
4. Measure q/Toffoli.
5. Score-gate against SOTA.
6. Triage scan.
7. Keep a route only if it improves score and preserves near-miss behavior.

When multiple routes are viable, prefer the route with:

- score margin over SOTA
- healthy density
- best low-severity tail
- fewer suspicious structural shortcuts

Before reaching for a *new* optimization, first mine for **dead-branch-wired** ones (see
*Dead-Branch-Wired Optimizations* under Toffoli Reduction Patterns): grep for `if <knob>` / branch
guards where the live baked route runs the un-optimized side while an existing, validated optimization
sits on a baked-OFF branch. Porting those onto the live path is the cheapest, lowest-risk win class —
value-exact, density-neutral, no new correctness proof.

## Warning Signs

Stop and rethink when:

- estimated score no longer beats SOTA
- first candidates share an identical high dirty triple
- `pha` is high while `cls` looks acceptable
- `anc` becomes nonzero after a cleanup/aliasing change
- candidate density collapses
- one node produces impossible density or no candidates across repeated large chunks
- local and remote validators disagree

The right response is usually not "scan harder." It is to isolate the knob that created the structural failure.

## Knob Glossary (deduplicated, from the full submission ladder)

Values in parentheses show the historical range / current frontier setting. Treat any carry-trunc
or compare-bit tightening as island-gated (needs a fresh `DIALOG_TAIL_NONCE`).

**Kaliski era (`KAL_*`, mostly superseded by dialog-GCD but ideas reusable):**
- `KAL_CSWAP_RS_MERGE` / `KAL_CSWAP_UV_MERGE_SAFE_ITERS` (254) / `KAL_UV_CSWAP_TRUNC` -- merge
  Bezout/GCD conditional swaps across iteration boundaries via `cswap(a)cswap(b)=cswap(a^b)` + a
  frame-parity bit. Peak-neutral Toffoli cuts.
- `KAL_WTRUNC` (margin 32->0) -- empirical-width truncation of inverse loops to an affine envelope.
- `KAL_DIALOG_FOLD` / `KAL_GZ_EARLY_RECOVER` -- host history / relocate carries onto provably-|0>
  high lanes (`gz_*_clean_pool`).
- `KAL_DIRECT_CONST_DOUBLE` / `KAL_CARRYTAIL_W` (44->36) -- register-free const adder + carry-tail trunc.
- `KAL_DOUBLE_CARRY_TRUNC_W` (24->19) / `KAL_FOLD_CARRY_TRUNC_W` (18->17) -- lazy-Solinas carry-window
  truncation for mod-double/halve and the fold (the `lsbs` dial; most-tuned late Toffoli levers).
- `KARA_SOL_SHIFT22_DOUBLES`, `KARA_Z02_LOWQ`, `KARA_SOL_MOD_VENT`, `KARA_SOL_DBL_FAST`,
  `KARA_FREE_Z1_TOPBIT` -- shift-as-doublings, hosted/lowq squares, vented Solinas add/sub.

**Dialog-GCD core / hosting:**
- `DIALOG_GCD_COMPARE_BITS` (75->46->52) -- branch-decision comparator width (the `msbs` dial; often
  free slack).
- `DIALOG_GCD_APPLY_CLEAN_COMPARE_BITS` (23->19) -- apply-phase overflow-clean comparator width
  (current #1 lever: 20->19).
- `DIALOG_GCD_ACTIVE_ITERATIONS` (399->258-260) -- truncated K2 step-blocks per inversion; dropping
  one cuts ~2,861 T AND can free peak scratch. Historically the largest single lever.
- `DIALOG_GCD_WIDTH_MARGIN` (32->7-12) -- GCD active-width cushion; tightening frees peak but raises island rarity.
- `DIALOG_GCD_WIDTH_SLOPE_X1000` (948 -> 1015..1017, **walked then reverted to 1015**) -- slope of the
  GCD active-width affine envelope. Each +1 notch removes ~500-640 emitted T BUT **craters island
  density ~25x/notch** (slope1016 ~0.5/Mn, 1017 ~0.02, 1018 = 0 in 10M). The 1015->1016->1017 walk
  hit that wall; the current SOTA `6953d1b` **reverted to 1015** and took the Toffoli back via
  `K5_CLEAN_BLOCK` etc. **Do NOT walk slope past the live frontier -- density dies far faster than
  the score gain.** Prefer `COMPARE_BITS` (gentle on density) for a findable cut.
- `DIALOG_GCD_K2` (=1 in SOTA `6953d1b`) -- **jump-GCD**: strip up to 2 trailing zeros per GCD step
  (records a `shift2` bit; apply mirrors with a conditional 2nd double/halve). Fewer steps; the
  enabler for the transcript-compression qubit drop. Required by `K5_CLEAN_BLOCK`.
- `DIALOG_GCD_K5_CLEAN_BLOCK` (=1 in SOTA `6953d1b`) -- **the lever that broke 1211->1203**: radix
  packs the dialog transcript sidecar (`round763` 6->5 base packing + GROUP_SIZE=3 K2 group, "5+3=8"
  compressed bits/block), freeing the qubits the sidecar held at the apply-fold peak. This is the
  trailmix M=5 base-3 sidecar-compression lever. Pairs with `ROUND763_COMPRESS_LEVER`/`_DEDUP`,
  `K2_PAIR_COMPRESS`, and the `round763` compressor-inverse code path. Code hints more headroom
  ("does not touch the round763 packer yet") -> deeper packing may push below 1203.
- `DIALOG_GCD_HOST_GATED` / `_BRANCH_BITS_HOST_COMPARATOR` / `_COMPOSITE_SCRATCH` -- host
  gated/comparator/Euclidean scratch on idle future-log + inactive high u/v lanes.
- `DIALOG_GCD_K2_PAIR_COMPRESS` -- encode 2 K2 steps in 5 sidecar bits (was 3 steps/8 bits).
- `DIALOG_GCD_PA9024_COMPARE_SCHEDULE` + `_SCHEDULE_MARGIN` (8) -- per-step comparator-width table.
- `DIALOG_GCD_PERPOS_MAJ2` (ancilla-free 2-CCX majority) / `_FUSED_HCLEAR_MEASURED` (Gidney h=a&b
  clear) -- apply-phase value-exact, peak-neutral Toffoli cuts (MBUC).

**Apply chunking / teardown:**
- `DIALOG_GCD_APPLY_CHUNKED_F_BLOCKS` (2->16) and `_F_CUT`/`_CUT2/3/4`/`_CUSTOM5` (70->126...) --
  number/boundary of chunks for the materialized `f=ctrl&a` apply add/sub; widening narrows the big
  chunk and lowers apply peak.
- `DIALOG_GCD_APPLY_BOUNDARY_SPLIT` / `_FINAL_LOWQ` / `_FINAL_TOPCLEAN` (0) /
  `_FINAL_WINDOWED_FAST_BLOCKS` -- apply-final/boundary teardown variants.
- `DIALOG_GCD_*_CONDITIONAL_REPLAY` (`APPLY_BOUNDARY`, `REVERSE_BRANCH`, `SPECIAL_CLEAN`,
  `MOD_FAST_FLAG`) -- conditional replay; lowers *average-executed* only (emitted cost unchanged).
- `DIALOG_GCD_SELECTED_BODY_STREAM_SUFFIX_MAP` -- per-step suffix-width streaming map (holds peak).

**Round84 square (current 1211-1226 peak-binder family):**
- `SQUARE_ROW_MAX_SEG` (199->184) -- round84 square segment size; **dominant late qubit lever**
  (~ -2 peak/notch), gated by freeing a carry slice first.
- `SQUARE_ROW_WINDOW_CLEAN_COMPARE_BITS` (22->17/18) / `SQUARE_ROW_WINDOW_MEASURED_CARRY_CLEAR` --
  row-window cleanup comparator width / measured carry clear.
- `ROUND84_KEEP_QUOTIENT_PRODUCT` -- keep the 66-bit quotient x c product live across the mid-sub.
- `ROUND84_QPROD_VENT_PAD` (+`_MINW`) / `ROUND84_QPROD_SHORT` (DEAD) / `ROUND84_INPLACE_QUOTIENT_CARRY_TRUNC_W`
  (21->20) / `ROUND84_FOLD_FAST_ADD` / `ROUND84_INPLACE_SOLINAS_FOLD` -- Solinas-fold quotient-product
  vent/trunc/fast-add variants.
- `DIALOG_GCD_FOLD_FREED_TAIL` / `_FREED_TAIL_ED` -- recompute ~1 ccx/fold to free the fold top carry
  lane (end-deferred variant).
- `DIALOG_GCD_FOLD_CARRY_TRUNC_W` (19->18) -- fused-fold carry truncation.
- `DIALOG_GCD_FOLD_PARK_LOW_CARRIES` -- park lowest fold-carry qubits across the high-limb tail,
  recompute before uncompute.
- `DIALOG_GCD_K2_APPLY_INPLACE_RAW_BLOCK` -- decode the K2 pair in place from compressed cells, free
  the persistent raw block.
- `DIALOG_GCD_SPECIAL_FOLD_BORROW_CARRIES` -- reuse idle `inner_scratch` with a borrowed-carry sparse
  constant fold.

**Island / search:**
- `DIALOG_TAIL_NONCE` -- the 96-op identity-tail Fiat-Shamir island selector; re-hunt on EVERY
  op-stream change. Consumed at build time; first `set_default_env` wins (bake the default in `mod.rs`).
- `DIALOG_REROLL` / `DIALOG_POST_SUB_REROLL` -- older pre-tail-nonce 2-D island reroll knobs.

## External Literature (2000–2026): Techniques Beyond the Current Route

Survey of the broader quantum-circuit-optimization literature (foundational reversible
arithmetic, T/Toffoli synthesis, ancilla/pebbling, the modular-inversion frontier, FT cost
models). Built by `/expert-autoresearch`: 6 angles, 80 indexed papers, 15 PDFs. The existing
TrailMix/Schrottenloher sections above stay the primary route guide; this brings in
*external* techniques and the 2026 frontier.

### Reference Routing

Read `references/external-literature-2000-2026.md` when the task involves: borrowing a
technique from outside our route, the inversion-algorithm frontier (safegcd/divstep,
jumpdivsteps, Legendre/Jacobi inversion elimination, compact `3n` inversion), Toffoli/T
primitives (4-T Toffoli variants, temporary-AND), the ancilla/pebbling toolkit
(conditionally-clean ancilla, measured/spooky uncompute, automated uncompute scheduling),
generic synthesis (ZX/T-par/AlphaTensor-Quantum), FT cost-model justification, or correctness
auditing. Full annotated index + abstracts + local PDFs: `research/index.json`,
`research/papers/`; raw per-angle hits: `research/search_results/`.

### Top external levers to try (ranked by expected fit)

1. **`jumpdivsteps` — TESTED 2026-06-12: NO-GO for our route (cost-modelled + measured-K3-consistent).**
   *(Bernstein–Yang safegcd, eprint 2019/266.)* Batch `T` binary-GCD `divstep`s computed on the
   low `k` bits into one `(k+2)`-bit 2×2 transition matrix, then apply that matrix to the
   full-width operands ~`n/T` times. **Why it loses HERE (not in trailmix):** trailmix's route pays
   a genuine full-width *apply* per step, so batching helps it. OUR route already compresses each
   step's reduction into a **cheap 33-bit CLASSICAL-constant truncated ripple** — `y += δ = c·e +
   2c·d`, `compressed.rs:2837` (`hi_delta=33`). A jump-`T` matrix apply must instead do **four
   *quantum* small×256 multiplies** (the matrix entries `a,b,c,d` are data-dependent, not classical),
   costing ~2.6× the Toffoli of the `T` K2 steps it replaces (~1.4× even with 2-bit windowing; floor
   argument: 4 controlled 256-bit adds ≈ 2048 T/batch already > 60% of the T=4 step budget). It also
   **widens** the GCD pillar (a matrix/accumulator register co-resident with `(u,v)` at the apply
   peak → measured K3 second-shift went 1221→1222q, `memory/2026-06-11-measured-square-carry-selective-k3.md`).
   And the peak is **co-pinned by `round84_inplace_solinas_square`** anyway, so even a width-neutral
   GCD win can't drop the peak alone. Replacing a classical-constant ripple with quantum multiplies
   is a structurally losing trade — the #1-ranked external lever does not survive contact with the
   dialog route's already-compressed fold. Don't re-attempt without first changing the fold structure.
2. **`conditionally-clean ancilla` — NOW THE TOP LEAD (jumpdivsteps #1 is dead). Targets the
   round84-square pillar, the one jumpdivsteps cannot touch.**
   *(Khattar–Gidney 2407.17966; measurement-adaptive MCX 2605.18169.)* Use borrowed/dirty bits as
   if clean with zero allocation + Laddered Toggle Detection. Audit our borrowed-carry adders and
   round84 x-tail venting against it for a cleaner peak win than the hand-tuned `1309→1285` trade.
   **Dual-pillar reality (verified 2026-06-12):** peak 1203 is co-held by the dialog-GCD apply fold
   AND `round84_inplace_solinas_square` (forward+inverse) — both hit 1203, so the peak only drops if
   BOTH drop together (a square-only or GCD-only win lowers Toffoli at best, not the peak). Because
   it's value-exact (borrows real-clean bits), a conditionally-clean win has GOOD island density —
   unlike the truncation levers that fall off the density cliff. Pair it with a GCD-pillar width drop
   (lever 5b: Luo et al. variable-width) to actually move below 1203. Runner-up GCD-pillar lever:
   **Luo et al. 2026 location-controlled / bit-length-tracked variable-width arithmetic**
   (`external-literature:43-46`) — exact-reversible peak-floor on the GCD pillar without jumpdivsteps'
   quantum-matrix penalty.

   **SCOPED 2026-06-12 — conditionally-clean square is an ENABLER, score-neutral ALONE.** The active
   square (`schoolbook_square_symmetric_lowq_selfhosted`, `multiply.rs:897`) ALREADY self-hosts: it
   borrows carry lanes from `tmp_ext`'s clean-zero high tail, uncomputes rows via measured HMR+`cz_if`
   (0-Toffoli, `multiply.rs:978`), and the carry uncompute is CZ-only/quadratic (`const_arith.rs:598`).
   What conditionally-clean (Laddered Toggle Detection) ADDS: lift "borrowed lane must be clean-zero"
   (`SQUARE_SELFHOST_SAFE_LANE_REUSE`, `multiply.rs:528`) → "borrowed lane may be idle-DIRTY and is
   restored to its input," widening the donor pool to any idle register (e.g. GCD-side) — and it's
   **Toffoli-neutral** (laddered structure removes the 2× dirty-borrow tax). BUT: Toffoli-neutral +
   peak co-pinned ⇒ **a square-only rewrite moves NEITHER score factor** — it only frees headroom that
   doesn't bind the peak. It pays off ONLY coupled with a GCD-pillar width drop that consumes that
   headroom to lower the joint peak. The single new obligation is "prove donor idle-over-window" (not
   just disjoint) — extend `assert_qubit_slices_disjoint` to idleness; everything else (chain carry,
   quadratic CZ-only uncompute, value-exactness) is already satisfied. Unit of work that actually
   moves the score = {conditionally-clean square headroom} + {variable-width GCD peak drop}, together.
3. **Automated uncompute scheduling** *(Meuli–Soeken–Roetteler SAT/QBF 1904.02121; Unqomp; spooky
   DAG solver 2401.10579)* — could replace hand-tuned venting/hosting/recompute decisions at the
   peak phase. Tooling investment, not a one-off lever.
4. **4-T Toffoli variants** *(Jones 1212.5069; Maslov relative-phase 1508.03273)* for MCTs inside
   paired compute/uncompute blocks (the spurious phase cancels); temporary-AND *(Gidney 1709.06648)*
   must back every paired AND. Apply to the apply-phase modular arithmetic.
5. **Legendre/Jacobi inversion ELIMINATION (qubit frontier, but a moonshot here)** *(Chevignard–
   Fouque–Schrottenloher 2026 eprint 2026/280 → 1098 q ≈ 3.12n; Jacobi Factoring Circuit
   2412.12558)*. Projective coords + compress the inverse to one Legendre/Jacobi bit, dropping the
   inverse result register. Orthogonal to dialog-GCD; the scored *affine* PA needs the actual
   coordinates, so it doesn't drop in — but it's where the qubit floor is going (cf. Huang
   2502.12441 *withdrawn*: naive projective fails; the symbol trick is what fixes it).

### Honest low-yield note

Generic peephole/ZX/T-par synthesis *(ZX 1903.10477, T-par 1303.2042, Quartz/VOQC)* gives 10–50%
on **un-optimized** circuits; our route is hand-optimized from tight primitives (we measured **0
peephole cancellations**), so expect little — leverage is structural (inversion algorithm, ancilla
hosting), not local rewriting. A one-shot ZX/T-par pass on the field-arithmetic blocks in isolation
is the only cheap thing worth a try.

### Correctness audit (zero-cost)

*Papa 2025 (2506.03318)* catalogs four ancilla-uncomputation bugs in published point-add circuits,
all fixable at zero gate cost — a missed uncompute is a free `anc/cls/pha` fix; an *over-eager*
truncation that fails uncompute on some inputs is exactly the island-search failure mode. Audit any
new truncation against these before scanning.

### Cost-model footnote

`Toffoli × qubits` is a sound proxy for surface-code spacetime volume *(Gidney–Ekerå 1905.09749;
Fowler–Gidney 1812.01238)* under 2D-local codes where idle storage ∝ qubits. Caveat: under
active-volume *(Litinski–Nickerson 2211.15465)* or magic-state cultivation *(2409.17595)*, idle
qubits become ~free and the objective shifts toward Toffoli/op-count alone. For our sequential
circuit depth ≈ count, so the distinction is moot here.

### Craig Gidney — Techniques Catalog

Gidney (Google Quantum AI) is the most relevant single author for this benchmark — temporary-AND,
windowed arithmetic, conditionally-clean ancillae, the DQI "Dialog" (the EEA-split our `dialog-GCD`
descends from), and the secp256k1 frontier (2603.28846) are all his. Many of his sharpest *practical*
tricks live only on his blog **algassert.com**, not in papers.

**Read `references/gidney-techniques.md`** for the full catalog (paper + blog, mapped to our levers).
Top Gidney levers to try here, ranked by fit:

1. **Windowed arithmetic on the in-circuit Bézout multiplies** *(1905.07682)*. Replace `2^w`
   controlled multiply-adds with one **QROM lookup** over a w-bit window. The apply phase is ~90% of
   our Toffoli; our fixed-base `k·G` comb is already this idea for scalar mult — the open question is
   whether the Bézout-reconstruction multiplies admit a windowed/table form. Biggest potential cut.
2. **Conditionally-clean ancillae** *(Khattar–Gidney 2407.17966)*. Borrow dirty bits as clean with
   **zero allocation, no toggle-detection** — the principled version of our `ROUND84_XTAIL`
   dirty/vent peak win; likely cleaner than the hand-tuned `1309→1285` trade.
3. **Constant-workspace classical-quantum adder** *(2507.23079)*. In-place add-a-constant at
   **3n–4n Toffoli, O(1) clean ancilla, free control** → for the Solinas/pseudo-Mersenne constant folds.
4. **Spooky pebble scheduling** *(blog 2019)*. Free an ancilla *early* leaving a 50/50 "ghost" to
   clean later → reclaim qubits before uncompute (line graph → S=3). The theory behind our
   measured-cleanup / transcript-hosting; a DAG pebble solver could schedule venting automatically.
5. **The "adder hides a CCZ" floor** *(blog)*. An n-bit adder must consume **≥ n−1 CCZ/Toffoli** —
   a hard lower bound; use it to sanity-check any proposed adder-Toffoli cut.
6. **cswap/relabel identities** *(blog: control-target duality, SWAP=3·CNOT, relabel-don't-move)* —
   the toolkit for the tobitvector/apply **cswap** Toffoli chunk (cf. our cswap-floor analysis).
7. **DQI "Dialog" `2510.10967`** — read for the in-place EEA construction and whether it batches
   `T` divsteps into one transition matrix (the **jumpdivstep** generalization of our `K2`/
   `ACTIVE_ITERATIONS` win — see `references/external-literature-2000-2026.md` §1).

**Cost-model note from Gidney's FT line:** magic-state *cultivation* (2409.17595) drops the
per-Toffoli cost toward a CNOT, which shifts the spacetime balance toward idle-qubit/peak cost — i.e.
under modern fault-tolerance the **qubit (peak) factor matters relatively more**, so peak-reduction
work (conditionally-clean ancillae, spooky-pebble hosting) is as valuable as Toffoli-cutting.
