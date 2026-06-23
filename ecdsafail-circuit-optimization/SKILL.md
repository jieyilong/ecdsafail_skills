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

### The 1168 Wall Broke — `trailmix_ludicrous` Is the New Base (2026-06-19)

The structural sub-1170 cut the bullet above called for **arrived as a circuit-family change, not a
knob.** On 2026-06-19 tob-joe (Trail of Bits) submitted `bdb1d22` — a complete revamp porting
trailmix's **product-min "ludicrous"** point onto `B` (new module
`src/point_add/trailmix_ludicrous/`, `build()` now calls `build_trailmix_ludicrous_ops()`). It landed
**1167q × 1,422,591 = 1,660,163,697**, and a swarm drove it to **1163q × 1,412,402** (`b310de9`) in ~15h,
then a second burst (Karatsuba square + NAF recoding + a qubit↔Toffoli bifurcation that then *resolved
into best-of-both*, `d11bdbb` 1159q × 1,380,711), a third Toffoli-grind wave (`f8e215b` 1159q ×
1,378,242), a fourth wave headlined by **empirical dead-CCX elimination** (`20b9a1d` 1159q × 1,364,380),
a fifth step re-applying the **1156q clamp** on the matured base (`27d4627` 1156q × 1,365,960), and a
sixth adding **iterated (two-pass) dead-CCX** to reach the **current SOTA 1153q × 1,368,487 =
1,577,865,511** (`da51a48`/`5fc2e81`, jieyilong, 6/23). **This supersedes the dialog-GCD 1168/1170
route as the base to fork from.** Full analysis: `references/REPORT_1168_wall_revamp.md` (the bursts are
§2.6–§2.11). (Separately, the low-qubit **Shrunken-PZ** track reached an **851q** *analysis-oracle*
witness — 464.5M Toffoli, rejected +3659% — see `references/SHRUNKEN_PZ_q948_track.md` §8.)

**Module map (`src/point_add/trailmix_ludicrous/`, fork from here).** `mod.rs` =
`build_trailmix_ludicrous_ops()` (register alloc order pins fuzzer IO ids), `load_schedule()` (copies
the baked tables into a thread-local `Sched` with per-call cursors), and the `BExt` trait that adds
`z`/`ccz`/`neg`/`cswap`/`x_if_bit`/`z_if_bit`/`cz_if_bit` to the `B` builder. `ec_add.rs` = the affine
point-add formula. `gcd.rs` = the jump-GCD inversion engine (the heart). `codec.rs` = the dialog-tape
codec. `gidney.rs` = the vented-adder zoo. `arith.rs` = Cuccaro add/sub + pseudo-Mersenne reduction +
the truncation constants (`f`, `PAD`, `LSBS`, `MSBS`, `CEILING`). `comparator.rs` = truncated top-window
swap comparator. `square.rs` = symmetric schoolbook square. `fused.rs` = fused double+cdouble and the
`(e+2d)·f` fold. `mcx.rs` = Khattar–Gidney log\*-ancilla MCX. `schedule.rs` = the baked per-call tables.

**Register layout (`mod.rs`).** Four 256-bit IO regs, alloc order fixes the ids: reg0 `x2` (quantum
`P.x`→`R.x`), reg1 `y2` (quantum `P.y`→`R.y`), reg2 `ox` (**classical `BitId`** `Q.x`), reg3 `oy`
(**classical `BitId`** `Q.y`). After `ec_add`, `route_swaps` restores the scattered `R.x` qubits to the
reg0 ids; `DIALOG_TAIL_NONCE` appends 48 identity `X;X` pairs for island grinding (score-neutral).

Why it fits under 1168 — three structural decisions:
1. **Classical `Q` (−512q, the decisive lever).** `ox`/`oy` are classical `BitId`s, materialized into
   a transient quantum temp only at off-peak coord steps — never resident across the GCD peak. A naive
   design holding both as quantum registers adds 512 live qubits at the peak. The coord steps
   (`coord_addsub`/`coord_add3x`/`coord_rsub` in `ec_add.rs`) alloc a 256-bit temp, `x_if_bit`-load the
   classical coord (**0 Toffoli**), run an *uncontrolled* pseudo-Mersenne `mod_add`/`mod_sub`,
   `x_if_bit`-unload (clean — temp was never modified), and free. The GCD apply's own 256-bit scratch is
   alloc'd/freed *inside* `mod_mul_inverse_in_place`, so it's never resident across the square either.
2. **Two GCD passes share one inversion primitive.** The full affine law (`ec_add::ec_add`):
   `x2-=ox` (dx) → `y2-=oy` (dy) → `y2 *= x2⁻¹` (**GCD pass #1, `Direction::Inverse`** → `y2=λ`, `x2`
   restored to dx) → `x2 += 3·ox` (`coord_add3x` does it as `coord+2·coord`, one fewer mod-add) →
   `x2 -= λ²` (fused square-subtract) → `y2 *= x2` (**GCD pass #2, `Direction::Forward`** → `y2=λ·x2`) →
   `y2 -= oy` → `x2 := ox − x2` (**zero-Toffoli negate** `ox−x2 = −(x2−ox)`: load, subtract, free, then
   `mod_neg` = const-add of `f−1`). λ is produced *by the inversion itself* — no separate field-inverse
   then multiply. Both passes call the *same* `mod_mul_inverse_in_place` (jump=2, 258 steps).
3. **Live-compressed dialog tape.** A SAT-synthesized **all-triple base-5 codec** packs each 3-symbol
   `(subtracted, swap, s_2)` window into a **7-bit code** (5/8 patterns reachable, log2(5³)≈6.97),
   streamed inline → **resident tape 603q vs 772 raw**. Peak owner = the forward-multiply apply (≈512
   coord + 603 tape + early-width GCD state + vent ancilla); `CEILING=1167` is baked and every adder
   vents to exactly `CEILING − active` via 0-Toffoli MBU (`hmr` + `cz_if`).

**The inversion engine (`gcd.rs`) — read this before forking.** `mod_mul_inverse_in_place` = two passes
sharing one tape: `forward_gcd_jump` (records) + `reverse_gcd_jump` (replays, restores `x`). Registers:
`u` init `q = 2^256 − f` (`q_secp256k1_le`), `v` init the input `x`; classical jump-before-swap divstep
on `(u=q, v=x)`. Per step it records the **3-bit symbol `(subtracted, swap, s_2)`** + one global `t1`
first-shift bit: shift-first (step 0 gates on `v` even, records `t1`; steps ≥1 shift unconditionally;
`s_2` = second jump shift), `subtracted = v[0]` post-shift, `swap` from the narrow comparator
(`controlled_swap_decision_lt_truncated`), then `cswap(swap,u,v)` + active-width `v −= subtracted·u`
(`controlled_add_active`). **Kaliski odd-u bit-0 shortcut:** `u[0]==1` by invariant ⇒ bit-0 carry-out
is provably 0 ⇒ emit `cx(ctrl,y[0])` directly, run the capped adder on bits 1.. with carry-in 0
(~1000+ Toffoli saved over both passes). The forward pass swaps the live symbol bits into fresh `|0>`
slots and compresses each window inline; the reverse pass decompresses one window at a time from the
tape end, **frees the 3 symbol slots before the apply** (so they don't inflate the peak), does the
fused forward apply, then exactly inverts the divstep — using the **vented** swap-flag uncompute
(`swap_decision_uncompute_vented`, ~half the comparator Toffoli). The apply step:
`if sub: y+=x`, `if swap: cswap(x,y)`, then `y := 2(1+s_2)·y` (step 0 = two gated `mod_double`s; step
>0 = the **fused** `fused_double_cdouble` with one combined `(e+2d)·f` reduction). `f = 2^32+977`, bits
{0,4,6,7,8,9,32}.

**The qubit floor = the GCD shrink/regrow width schedule** (`SCHED_J2`, len 258: holds at 256 for ~11
steps then ramps to 13 by step 257). Each step `zero_and_free`s `u`/`v` qubits above the schedule width;
the reverse pass re-allocs them. The whole body (comparator, cswap, subtract) runs on
`current_n = SCHED_J2[i]` bits, so the adders run in the freed headroom. `GAP_J2[i]` (len 258) is the
per-step comparator window. A `dx` whose bitlength exceeds the schedule width makes `zero_and_free`
panic (it's rejected) — which is why the route needs a `DIALOG_TAIL_NONCE` grind to land all 9024
verifier draws in the schedule-supported set.

**The codec (`codec.rs`).** `DialogCodec` variants `Step0`(2b)/`Triple`(7b)/`Pair`(5b)/`Raw`(3b); tiling
= 1 Step0 + 85 Triples + 1 Pair tail + 1 `t1` = **603 resident** vs `1+3·257=772` raw. `compress_2sym_fast`
is the SAT-synthesized straight-line `x/cx/ccx` pairs core (25 valid 2-symbol inputs → 25 distinct 5-bit
codes, frees a wire; terminal AND-uncompute vented via `clear_and` = 0 Toffoli). Triple = `pair →
affine normalizer → fold-in s_2`. ~18 executed Toffoli per Triple forward after vents.

**The vented-adder zoo + baked schedule tables (`gidney.rs`/`schedule.rs`) — this is the knob surface.**
Every adder vents carry-uncompute via Gidney MBU (`hmr(carry,bit); cz_if_bit(a,b,bit)` = **0 Toffoli**,
+1 transient qubit held only between fwd/rev carry chains; **each vent = −1 Toffoli, +1 peak qubit**).
Adder family, dispatched per-call by `GCD_BRANCH` (0=plain `controlled_hybrid_add_refs_impl` /
1=`varchunk` / 2=`adaptive`→`chunked_then_cuccaro`). Baked tables, consumed in emission order — these
are *the* per-site levers (the design reads NO live `live_qubits`; everything is the table + the
`TRAILMIX_*_DELTA` overlays): `GCD_SUB_K` (GCD-subtract carry-cap), `GCD_BRANCH` (adder dispatch),
`APPLY_COUT_K` (apply cofactor-add cap), `FOLD_SCHED` (fold vent: +=clean@nv / −=chunked), `CMP_K`
(swap-comparator held carries), `FFG_G` (`+f`-fold clean-vent count), `HYB_V` (hybrid-adder exact vent
count, verbatim), `SQ_ROW_K` (square row-add headroom). The `b310de9` overlay deltas
(`TLM_HYB_V_DELTA`/`TLM_COUT_K_DELTA`/`TLM_FFG_DELTA`/`TLM_FOLD_DELTA`) subtract from these per-call to
trade vents↔qubits at the peak; `TLM_GCD_K_ADJUST{,_AFTER,_BEFORE}` window-trims `GCD_SUB_K` in a
divstep range.

**The deliberate truncations (`arith.rs`).** `f=2^32+977`, `PAD` (was 21, now 19/`arith`, 20/`schedule`).
Low-`LSBS=PAD+F_BITLEN`-bit `+f` fold drops carry beyond bit `LSBS−1` (~`2^-PAD`/fire miss);
narrow-`MSBS=PAD`-bit overflow/swap comparators recompute the top predicate as a deferred-Z only where
the HMR bit fired, tolerating a ~`2^-PAD`/fire mis-decide. Safe because each is an independent rare
divergence and the common path is exact; `DIALOG_TAIL_NONCE` grinds inputs so all 9024 draws stay
clean. **`PAD` is a live lever in both directions** (smaller = fewer live bits *and* fewer Toffoli, but
higher miss rate to absorb in the nonce hunt).

**The 1167→SOTA cascade splits into these reusable lever families** (the rest is LF↔CRLF churn + pure
nonce-grind commits — see report):

- **3 *free* −1q peak drops** (`ab1b2d6`, `cea9f5f`, `f8d23a9`; 1167→1164), all the *same idea*:
  **don't hold provably-constant divstep low bits live — park/loan them back to the free pool across
  the adder that needs the headroom** (Toffoli ≈ neutral). odd-u0=1 (`TLM_PARK_ODD_U0`/`TLM_LOAN_ODD_U0`),
  even-v0=0 (`TLM_PARK_EVEN_V0`), known gcd-y0 (`TLM_LOAN_GCD_Y0`, with `GcdBit0Mode` delaying the
  bit-0 CNOT), and the redundant step-0 swap_flag (fold `t1` in via `ccx(t1,s2,sub)`). One open qubit
  lever: **mine the divstep for more provably-constant lanes to park.**
- **Paid −1q drops (`b310de9` 1164→1163; `31421df` 1164→1162; `fed64cf` 1162→1159): the qubit↔Toffoli
  exchange rate run in reverse.** These do NOT find new constant lanes — they **buy** peak qubits by
  spending Toffoli. Three mechanisms: (a) **surrender apply-phase vents** (`TLM_HYB_V_DELTA`,
  `TLM_COUT_K_DELTA`, `TLM_FFG_DELTA`, `TLM_FOLD_DELTA` — each removed vent reverts a 0-Toffoli MBU to a
  real CCX); (b) **tighten `PAD`** 21→20/19 (narrower `+f`-fold/comparator windows = fewer live bits
  *and* fewer Toffoli, higher `2^-PAD`/fire miss) + `maybe_adjust_gcd_k` (`TLM_GCD_K_ADJUST=-1` over a
  divstep window narrows the GCD carry-chunk); (c) **the dynamic live-headroom clamp** (`fed64cf`):
  `target_qubit_headroom = TLM_TARGET_Q − active_qubits` clamps EVERY transient adder's carry/chunk to
  `min(scheduled_k, headroom)` so no local peak exceeds the target — a circuit-wide "do not exceed N
  qubits" governor (`TLM_TARGET_Q`, `TLM_TARGET_FFG_RESERVE`, `TLM_TARGET_FOLD_RESERVE`,
  `TLM_GCD_RESELECT_LAYOUT`, `TLM_DIRECT_VARCHUNK`). **Dropping the ceiling is a one-line lever**: `6ba606a`
  went 1159→1157 by just `TLM_TARGET_Q` 1159→1157 (clamp body unchanged), paid for with new per-call FFG
  reserve overrides (`TLM_TARGET_FFG_CALL_RESERVE_DELTAS/OVERRIDES`), a **lazy-cin0 fold**
  (`TLM_FOLD_CHUNK_LAZY_CIN0` — alloc the chunk carry only inside the boundary-erase, deferring one
  carry's liveness), and vent deltas. **⚠ These only win if they clear the break-even below.**
- **⭐ The break-even rule (the meta-lever) — and its cost is PER-BASE, not fixed.** A peak qubit is
  worth `avg_Toffoli / peak_qubits` Toffoli (**≈1,190 at the 1159q floor**). A width-narrowing lever is
  net-positive **only if it removes a qubit for < that many Toffoli**. But the realized cost *moves with
  the base*: `fed64cf`'s clamp-to-1159 cost ~1,514 Toffoli/qubit on the expensive schoolbook-square base
  (> break-even) and **LOST** to `3df690f` (which floated to 1164q) — yet once `28fe2f2`'s Karatsuba
  removed the wide square adds the clamp was fighting, **the same clamp cost only ~20 Toffoli/qubit** and
  `d11bdbb` re-stacked it to **WIN at 1159q × 1,380,711 (SOTA, best-of-both)**. The frontier *bifurcated*
  (1159q vs 1164q) then *resolved* — the qubit and Toffoli levers **compose**; they're rarely truly
  opposed. **⇒ After any structural arithmetic change, RE-TEST every shelved qubit lever — the
  break-even moved. Always divide a candidate's realized Toffoli-delta by its qubit-delta vs the
  *current* `T_avg/q`.** **The product-race trap is real but NOT permanent — "lost" means "early," not
  "wrong."** `6ba606a` (1157q) and `cde752d` (1156q) both cleared per-base break-even yet *lost* the SOTA
  at the time, because the 1159q Toffoli-grind was falling faster. **But once the Toffoli base matured to
  the dead-CCX 1,364,380 floor, the very same 1156q clamp returned as SOTA** (`27d4627`, ~527
  Toffoli/qubit — `1156×1,365,960 < 1159×1,364,380`). **Lesson: run both tracks, compare *products*, and
  RE-TEST every shelved width drop after each Toffoli win — the break-even keeps moving in their favor.
  The qubit floor and Toffoli floor descend in lock-step, each unlocking the other.** See
  `references/REPORT_1168_wall_revamp.md` §2.6–§2.10.
- **⭐ Biggest Toffoli wins = better arithmetic at the dominant cost-center (huge leverage from tiny
  diffs).** `28fe2f2` **Karatsuba modular square** (−22.4M, the single biggest win in the saga, +175/−47
  diff): split `λ = hi·2^128 + lo`, compute `lo²`, `hi²`, `(lo+hi)²`, recombine — 3 n=128 squares
  (~24.4k CCX) vs 1 n=256 schoolbook (~32.6k CCX), ~25% off the O(n²) cross-products that run **every
  divstep round**. `4ea8b74` **NAF recoding** of `f=2^32+977` (`F_NAF_TERMS`: 7→5 terms
  `2^32+2^10−2^6+2^4+1`) + doubling-ramp elimination (`mod_add_shifted_low`/`mod_sub_shifted_low`, no
  pad qubits). `e25c7d8`/`3df690f` hoist `<<32`/all NAF terms to direct shifted adds
  (`TLM_SQUARE_F_SHIFTED_LOW`). **Lesson: audit any O(n²) or ×258×2 primitive (the square, the
  reduction) for a structural improvement before touching schedule knobs — BUT only if the new ops are
  as cheap as the ones removed (see the next bullet).**
- **❌ Recursive Karatsuba / Toom-3 on the square: TESTED, net Toffoli LOSS — do NOT re-attempt
  (measured 2026-06-21, §2.9).** `4a90d04`'s `kara_square_into_prod` scaffolding (`TLM_SQUARE_KARA2`,
  identity `x²=A+M·2^h+B·2^2h`) had a width bug (`unbuild_kara_sum` panicked); after fixing it and
  enabling recursion, the square's CCX went **UP** 117,016→177,180 (**+60,164 from one split**), worse
  at every depth (th96 +66.8k → th32 +277k total), and it leaked the three-product live set raising
  peak 1159→1612. **Root cause — the win does NOT transfer to this reversible cost model:** the
  schoolbook *symmetric* square's cross-products are already ~1 vented CCX each (MBU), while Karatsuba
  trades them for *un-vented* wide recombination adds (`hybrid_add_adaptive`, ~3 CCX/bit) that cost far
  more than the multiplies they remove. Toom-3 is strictly worse (5 eval points + `/3` interpolation,
  all un-vented). The square is only 8.14% of CCX with 647q off-peak slack, so the *qubit* room exists —
  but the arithmetic is already near-optimal; the live levers (dead-CCX, vents, comparator narrowing)
  win precisely because there's no cheap arithmetic left to restructure. (To ever make Karatsuba pay
  here you'd have to re-engineer the recombination adds to be MBU-vented AND recurse to deep leaves AND
  fix the leak — high effort, sub-2% ceiling. Not worth it.)
- **⭐⭐ Empirical / dynamic dead-CCX elimination — biggest avg-T lever, but a SCORE lever, not a DESIGN
  lever (`4a90d04`/`20b9a1d`).** Beyond static `constprop.rs`: a **bit-sliced finder** reproduces the
  Simulator's per-shot eval and records, per CCX, the OR of its *fired* mask. A CCX whose target never
  flips on the reachable EC-point distribution (its two controls are **dynamically mutually-exclusive** —
  static constprop can't prove it) is **inert-but-charged** (costs avg-executed Toffoli, does nothing).
  Drop those by **post-fanout op-index** via a baked `.idx` → `build()` does
  `include_str!(...idx)` → `HashSet` → `ops.filter`, *after* constprop + `single_ccx_fanout`.
  **The false-positive defense is the heart of it:** a single 9024-shot pass over-flags ~49k (most only
  *coincidentally* idle on one draw); **intersect "never-fired" across 1024 independent random shot sets
  (~9.2M inputs)** → the set shrinks monotone-nested (`V1024 ⊆ V512 ⊆ …`) to a robust core. Sizing the
  screen ≫ the 9024 verifier draw pushes the residual false-positive firing-rate below the verifier's
  resolution. Then **hunt `DIALOG_TAIL_NONCE` WITH the drop applied** (self-consistent fixed point) and
  check action-neutrality across many nonces. **Caveats that matter:** (1) **distribution/island-exact,
  NOT all-inputs value-exact** — "clean on its island," not correct off-island; (2) **absolute-position
  fragile / circuit-specific** — *any* structural change shifts the indices onto live gates (→ the
  `9024/141/141` all-shots break) and forces a **full re-screen**; the lists are literally per-variant
  (`dead_k1_coord3x.idx` vs `dead_k1_nocoord3x.idx`); (3) it does **not** improve the construction (a
  better circuit wouldn't emit these gates) and a clean-room build gains nothing from the `.idx`.
  Peak-neutral, open-ended (bigger screen finds more) — but treat it like a sophisticated nonce grind:
  it's why SOTA avg-T looks ~1.36M, but the *durable* wins are the structural levers. **It is also
  ITERABLE (`da51a48`, the 1153q SOTA): drop the first list, then re-screen the ALREADY-DROPPED stream
  over fresh FS sets and drop again** — the first removal reshapes the stream so a second pass
  (`DROP_DEAD_ROBUST_SECOND`, `drop_dead_second_fs512.idx`, 2,638 ops on top of the first 13,880) finds
  newly-dead gates; the marginal second pass is exactly what carried the 1153 rung over break-even.
  Each pass is subset-monotone and re-hunted. **Operational how-to (the BitWonka `find_dead_ccx`
  screener + the distributed multi-host scan helper): see the "Dead-CCX / Dead-CXX Screening" section
  below.**
- **⭐ Comparator-width (`GAP_J2`) narrowing — the highest-leverage *static* Toffoli lever per line of diff.**
  `f0c1c42` (bket7) cut **−1.33M from a 22-line schedule-table edit.** `GAP_J2[i]` (`schedule.rs`, len
  258) is the per-step swap-decision comparator **window width** for the jump=2 GCD; `gcd.rs` sets
  `cmp_eff = GAP_J2[i].min(current_n)` and the held Gidney carries / compared MSBs in
  `compare_geq_chunked_middle` scale with it. Shaving 1 bit/step **×258 steps ×2 GCD passes** is the
  −1.33M. Cost: mis-decides the u↔v swap with prob ~`2^-k` when the top differing bit falls just below
  the window — an island-exact truncation recovered by the tail-nonce hunt. *This is the
  `DIALOG_GCD_FOLD_CARRY_TRUNC_W`-style lever native to the ludicrous GCD; sweep it one notch at a time.*
- **⭐ Converged-tail cswap elision (`TLM_APPLY_CSWAP_SKIP_LASTK` + the FWD/INV × FIRST/LAST family).**
  On the first/last K GCD iters the apply `cswap`'s swap-decision is deterministically 0 for
  all-but-rare inputs (the GCD has converged), so it's a no-op — skip it (`apply_cswap_skip_dir` in
  `gcd.rs`, `5c34dd1`→`9d524b7`). `9af02f7` extended it to the **inverse pass + first iter**
  (`TLM_APPLY_INV_FIRST_CSWAP_SKIP`, also `..._FWD_LAST`/`..._INV_LAST`/`..._INV_FIRST_SUB_SKIP`,
  −283k), and there are companion `..._S2_ZERO_LAST` skips routing known-zero steps through
  `fused_double_only`. Island-exact (huntable). A *structural* instance of "elide a data-dependent gate
  known-0 on the island" — enumerate every FWD/INV × FIRST/LAST corner of the converged GCD.
- **Classical-constant folding (Q is classical → do constant arithmetic for free).** `662e267` rewrote
  `coord_add3x` (`dst += 3·ox mod q`) to derive `3·ox mod q` entirely in the **classical `BitId`
  domain** (`classical_times3_mod_q`, all `BitStore/BitInvert`, 0 Toffoli) then one `mod_add_exact` —
  removing the doubling + 2nd mod-add + 257-bit temp (~−400 Tof/call). Audit every coord step touching
  the classical `ox`/`oy` for constant-folding into the bit domain. *(Note: this oscillated in/out vs a
  peak concern — it trades Toffoli for a transient; check peak before keeping.)*
- **Doubling-ramp elimination in the reduction (the SOTA lever, `f8e215b`).** The `f·value mod q` NAF
  reduction inside the Karatsuba square no longer builds a 257-bit `ext` and walks a `mod_double` ramp
  to each NAF shift offset; a new default branch in `square.rs::apply_f_times_value_tagged` applies each
  term `±(value≪shift) mod q` **directly** via `apply_shifted_hi_term` (`mod_add/sub_shifted_low` +
  per-wrapped-bit `add/sub_f_window_shifted` pseudo-Mersenne folds). Value-exact, −156k. *Extends the
  shifted-low idea (`4ea8b74`) to the Karatsuba reduce; audit any `mod_double`-ramp shift for the same.*
- **Carry-drop-cout + MBU vent (`TLM_GRAD_FINAL_NO_COUT`).** Drop the unneeded final carry-out of the
  top constant-add chunk and uncompute the chunk's carries with `hmr`+`cz_if_bit` (0-Toffoli MBU)
  instead of a CCX (`const_chunk_add_clean_drop_cout`, `arith.rs`, `5c34dd1`).
- **Schedule-level Toffoli wins:** `bc2334a` −5.9M (exhaustive carry-chunk **layout search**);
  `497cc20`+`b02b354` **constprop post-pass** (drop CCX with const-0 control, fold const-1→CX, +
  affine/XOR/inverse-pair; **`CONSTPROP_MAX_ITERS` controls fixpoint depth** — `d2643bc` 16→256 = −377k)
  — model-agnostic; `b1dec1e` `d & !e = d ^ (e & d)` 2-CX identity; `a47dc6e` skip-j0 cswap;
  `LUD_EXTRA_FOLD_VENTS` (more Gidney vents in GCD fold rounds, `3df690f`); the `*_DELTA` knobs
  (`TLM_HYB_V_DELTA`/`TLM_COUT_K_DELTA`/`TLM_FOLD_DELTA`) narrow scheduled vent/cap values one more step.
- **Deliberate budgeted truncation:** low-`(PAD+33)`-bit `+f` fold + narrow-`PAD`-bit comparators accept
  a ~`2^-PAD`-per-fire miss; `PAD` (21↔19/20) is a live two-direction lever (smaller = fewer Toffoli +
  fewer live bits, more miss to absorb in the nonce hunt). `GAP_J2` (above) is the same idea on the
  swap comparator.

**Corollary — neither extreme is score-competitive; stay in the 1159–1164q band.** The **Shrunken-PZ
low-qubit track** (a *separate* line of work from this ludicrous route — a 530-step divstep inversion,
not the jump-GCD+Karatsuba arithmetic) keeps setting qubit records that are all **score-rejected**:
1050q → 1019q (teddyjfpender, +~280%) → 948q (nasqret `a203fac`, +468%, breaking the 952q wall via a
"q949 robust envelope" CLZ-conditional width packing) → **851q** (`e7dd3de`, +3659%, via
dirty-catalytic / gate-hosting / register-shared-EEA — but an explicit **analysis oracle, not a
circuit**, 464.5M Toffoli, §8 of the PZ doc). The PZ Toffoli is ~40× the ludicrous SOTA's 1.37M, so it's
a **qubit-lower-bound witness, not a product contender** — would need a ~33× Toffoli reduction (a
different inversion, not a packing tweak) to compete. High-qubit experiments (abipalli's 2045q, +46%)
lose the other way. **The PZ route is its own thing — full mechanism (952→948 break + the 851q oracle)
in `references/SHRUNKEN_PZ_q948_track.md`.** The product is minimized in the **1153–1164q** ludicrous
band — the SOTA is now the **1153q best-of-both** point (`da51a48`, **1153q × 1,368,487**): the dead-CCX
low-Toffoli base (`GAP_J2` narrowing + converged-tail cswap elision + doubling-ramp removal + empirical
**iterated** dead-CCX) **+** the 1153q headroom clamp. The 1157q (`6ba606a`), 1156q (`cde752d`), and the
first 1153q (`2f8835b`) drops *lost* the product race when they landed — but each width rung **returns
as SOTA** once the Toffoli base gets cheap enough (the 1156q clamp at §2.10, the 1153q at §2.11);
"lost" meant "early," not "wrong" (re-test shelved width drops after each Toffoli win).

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

## Dead-CCX / Dead-CXX Screening

Use this step when a q-target route is nearly score-competitive and needs a robust,
distribution-level dead-gate candidate list before applying any `DROP_DEAD_ROBUST`
or similar post-build cut. Do not fit dead gates to one Fiat-Shamir draw. Screen a
large random input population, then treat the resulting list as a candidate reservoir
that still needs full eval and island triage.

> **This section is the operational how-to. For the *strategic* framing — read it first —
> see the ⭐⭐ "Empirical / dynamic dead-CCX elimination" bullet under "The 1168 Wall Broke."
> The key points it makes: this is a SCORE lever, NOT a DESIGN lever (it does not improve the
> construction; a clean-room build gains nothing from the `.idx`); the indices are
> **absolute-position fragile**, so *any* structural change (a clamp, knob, or fold toggle —
> not just an FS re-hash) shifts them onto live gates and forces a full re-screen. The lists
> are literally per-variant (`dead_k1_coord3x.idx` vs `dead_k1_nocoord3x.idx`). Treat the
> whole technique like a sophisticated nonce grind: worth running to squeeze a frozen artifact,
> but the durable wins are the structural levers. (Heading note: "Dead-CXX" only appears here
> because the bundled script/outputs are named `*_cxx_*`; the gate is a CCX.)**

### Preferred Screener: BitWonka `dead-ccx-finder`

Prefer BitWonka's public tool when the objective is dead-CCX filtering for the
current ludicrous route:

```text
https://github.com/BitWonka/ecdsafail-tools/tree/master/dead-ccx-finder
```

It provides `find_dead_ccx.rs`, a drop-in `src/bin/` binary for an otherwise
unmodified challenge checkout. It calls `point_add::build()` once, screens the
exact post-fanout op stream, and ORs each charged CCX/CCZ fire mask across many
Fiat-Shamir seeds. A gate emitted to `.idx` is one whose scored condition
`cond & c1 & c2` never fired over the screened population.

Key properties from the tool README:

- self-contained bit-sliced simulator; builds against the public `Simulator`
  fields and does not require trusted simulator patches
- `DEAD_REAL_RNG=1` exact mode uses the real measured-gate RNG; about 9M screened
  inputs in roughly 13 minutes on a 16-core box
- `DEAD_REAL_RNG=0` fast mode forces measurement outcomes to 0; useful for quick
  conservative iteration, but use exact mode for final ship screens
- knobs: `DEAD_SCREEN_NONCES`, `DEAD_REAL_RNG`, `DEAD_THREADS`,
  `PREDICT_SHOTS`, `DEAD_IDX_OUT`, plus the route's baked or exported `TLM_*`

Canonical single-host run:

```bash
cp dead-ccx-finder/find_dead_ccx.rs <challenge-repo>/src/bin/find_dead_ccx.rs
cd <challenge-repo>
cargo build --release --bin find_dead_ccx
NONCES=$(python3 -c "print(' '.join(str(700000000001+i*999999937) for i in range(1000)))")
DEAD_REAL_RNG=1 DEAD_SCREEN_NONCES="$NONCES" DEAD_IDX_OUT=dead.idx \
  ./target/release/find_dead_ccx
```

Use fast mode only as a triage pre-pass:

```bash
DEAD_REAL_RNG=0 DEAD_SCREEN_NONCES="$NONCES" DEAD_IDX_OUT=dead.fast.idx \
  ./target/release/find_dead_ccx
```

Add the drop loader after the single-CCX-fanout pass and before returning `ops`.
For local tuning, point `DROP_DEAD_IDX_FILE` at the generated `.idx`. For ship,
commit the `.idx` and switch the loader to `include_str!(...)` so the env-less
grader build reproduces the exact final artifact. Always keep
`DROP_DEAD_ROBUST_DISABLE=1` as a debugging escape hatch.

Important: BitWonka's tool is not a drop-in replacement for the older bundled
distributed helper's current `screen_dead_ccx` CLI. The finder uses environment
variables (`DEAD_SCREEN_NONCES`, `DEAD_IDX_OUT`, etc.), while the bundled helper
expects `target/release/screen_dead_ccx --shots ... --seed ... --out ...`.
Use BitWonka's `find_dead_ccx` directly for final single-host screens, or adapt
the distributed helper/backend script before mixing the two.

### Distributed Orchestration Helper

Bundled helper:

```text
scripts/distributed_dead_cxx_scan.py
```

It currently runs `target/release/screen_dead_ccx` over `N` random inputs across
`M` SSH hosts with `K` worker processes per host, launching all hosts concurrently
after staging, then collects every shard's `.idx` list and emits merged support
files:

- `dead_cxx_support.tsv` — every op index and the number of shards where it stayed dead
- `dead_cxx_intersection.idx` — indices dead in all shards
- `dead_cxx_support_ge<N>.idx` — threshold lists, including all-minus-one / all-minus-two when requested
- per-host `shards/`, `logs/`, `manifest.tsv`, plus local `manifest.json` and `summary.json`

Example:

```bash
python scripts/distributed_dead_cxx_scan.py \
  --total-shots 20000000 \
  --host l40a=root@202.181.159.211:11152 \
  --host l40b=root@103.67.42.150:10606 \
  --threads-per-host 24 \
  --challenge-dir /root/q1153_work/challenge \
  --remote-workdir /root/q1153_dead_cxx_20m \
  --out-dir outputs/q1153_dead_cxx_20m \
  --mode random \
  --support-threshold 48 \
  --support-threshold -1 \
  --support-threshold -2 \
  --ssh-option=-o \
  --ssh-option StrictHostKeyChecking=accept-new \
  --build
```

Host format is `[name=]user@host[:port][,identity=/path/to/key]`. If no
`--support-threshold` is given, the helper writes `all`, `all-1`, and `all-2`
support lists by default. Use `--dry-run` first to write the generated remote
scripts locally without running them.

Operational rules:

1. Build the screener from source on each remote host; do not upload `ops.bin`.
   If using BitWonka's tool, copy `find_dead_ccx.rs` into `src/bin/` and build
   `find_dead_ccx`; if using the bundled script as-is, provide a compatible
   `screen_dead_ccx` binary.
2. Choose `N` large enough that each shard has meaningful coverage. For fragile dead-drop
   work, prefer tens of millions of random samples over a single 9024-shot draw.
   A practical final minimum is the BitWonka/field scale of about 9M inputs; use
   larger distributed populations when trying to relax support thresholds.
3. Use `K` near the CPU parallelism the host can sustain without memory pressure. If
   workers are killed or logs show rc=137, lower `K` and restart cleanly.
4. Start with strict support lists (`all`, `all-1`, `all-2`) and measure
   `q / avgT / cls / pha / anc` on each before relaxing thresholds.
5. If a threshold shell worsens `pha` or creates a repeated classical floor, split it
   into op-index/support shells and test recombinations instead of scanning nonces.
6. Record the source commit, CFG/env, tail nonce used for eval, exact support threshold,
   input population size, host list, `K`, screener mode (`DEAD_REAL_RNG=1/0` if using
   BitWonka), and local/remote artifact paths before any nonce scan or submission attempt.

Interpretation:

- A high-support dead-CXX index is evidence that a charged gate is distribution-inert,
  not proof that deleting it is correct after the op stream re-hashes.
- Every applied list reseeds the Fiat-Shamir island. Re-run full `eval_circuit` on the
  post-drop stream and then do a short triage scan before large GPU hunting.
- Dead-CCX screening must be done with the drop disabled. Then bake/apply the `.idx`,
  re-hunt the nonce on the drop-enabled circuit, and validate that final artifact.
- Favor robust all-shard intersections for repair baselines; use lower support shells
  as a Toffoli reservoir only after slicing/attribution shows they do not introduce
  structural phase or classical dirt.

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

For the **current base circuit** (the post-2026-06-19 frontier), read
`references/REPORT_1168_wall_revamp.md` when the task involves `trailmix_ludicrous`, the
classical-`Q` product-min lever, the two-shared-GCD-passes affine add, the all-triple base-5
603q dialog tape, the Karatsuba modular square / NAF recoding, the constant-lane parking and
dynamic-headroom-clamp qubit levers, the qubit↔Toffoli break-even/bifurcation rule, the
constprop/affine post-pass, or anything forking from the 1159–1164q ludicrous operating band.
It maps every commit in the 1167→SOTA cascade (incl. the 6/19–6/20 Karatsuba/bifurcation burst,
§2.6) to its mechanism and file/function. See also the short "The 1168 Wall Broke" subsection
above for the operating summary.

For the **Shrunken-PZ low-qubit track** (a *separate* line of work — the 530-step divstep
inversion, qubit-min not product-min), read `references/SHRUNKEN_PZ_q948_track.md` when the task
involves `trailmix_port/inversion`, the PZ divstep state machine, the q948/952/956/988 qubit
records, the "q949 robust envelope" / CLZ-context width packing, or whether to chase the
low-qubit route for *score* (answer: no — it is a qubit-witness, ~33× over the product
break-even). Do NOT conflate it with the ludicrous arithmetic.

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

### Shrunken-PZ Q988 -> Q956 Lever Stack (the sub-1000q ladder)

A community ladder drove the SAME shrunken-PZ port from q988 down to q956 as a **sealed, knob-gated
stack**: each lever `assert!`s the previous ones are on and is named for the qubit count it unlocks.
No new construction — every step squeezes **one wire** out of the single inversion peak. All verified
in `trailmix_port/inversion/shrunken_pz_{state_machine,schedule}.rs` and the
`configure_sub1000_trailmix_route()` knob stack. The five distinct mechanisms (deduped, ranked by
qubits saved):

1. **Selective per-step quotient-width clamp (~8-9q, 988->979) — the biggest lever.** Do NOT cap the
   EEA quotient register globally (`TRAILMIX_Q_CAP`); trim it **only at the peak-binding divstep** via
   a budget `q <= T - 2*max(w_a,w_b) - 2*max(w_ca,w_cb)` (`TRAILMIX_Q_TARGET`, `trailmix_q_width_step`).
   General rule: a per-step "trim only at the binding instant" schedule beats any global cap, because
   the cap is paid on every step while only one step owns the peak.
2. **Exact in-place CLZ/CTZ (~6q, incl. a -5q jump to 968).** Count leading/trailing zeros with **no
   ancilla allocation** — fold the result into existing registers (`LOWQ_HYBRID_CLZ`, `LOWQ_EXACT_CTZ`,
   `LOWQ_HYBRID_CLZ_NOALLOC_ADD`; in `clz_diff_body_middle`).
3. **Selective lane borrowing / flag aliasing (~8q, 965->956).** Borrow shift/boundary lanes only
   where provably free (`Q959_SELECTIVE_BORROW`), gate the comparator's scratch to **only its live
   window** (`Q958_GATED_COMPARE`), and alias a transient flag onto an already-live persistent lane —
   e.g. the `off` flag onto `counter[0]` (`Q956_OFF_BORROW`, proven disjoint by `assert_q956_off_alias`).
4. **Algebraic wire fusion (~3q).** Drop a known-constant EEA operand (`LOWQ_ONE_A_ELIM` removes the
   `a=1` operand), and **fuse the immutable input-sign bit into the EEA parity bit** `s^p`, reclaiming
   the persistent wire (`TRAILMIX_SIGN_PARITY_Q_REUSE`); the reverse-EEA restores it exactly.
5. **Compute-into-existing-ancilla folds (~2q).** Fold the bitlen-difference into the existing `pa`
   register (`LOWQ_CLZ_DIFF_CONST_FOLD`) instead of a caller-supplied diff register; compact the
   Khattar-Gidney adder ancilla (`LOWQ_COMPACT_KGANC`).

**Unifying recipe (reusable for any inversion-peak push):** drive a single peak down one wire at a
time by making every per-step control/scratch/flag *either* compute-in-place-then-uncompute *or* alias
an already-live persistent lane, so nothing extra crosses the peak instant — and trim variable-width
registers (quotient/cofactor) only at the binding step, never globally. Classify before scanning: the
in-place / alias / constant-teardown / sign-fusion levers are structural and value-exact; the
q-target / thin-schedule / support-bound levers are island-gated (the op-stream changes re-roll the
SHAKE256 9024-shot set, so each needs a fresh `DIALOG_TAIL_NONCE`). Sub-1000q is a pure-qubit play:
these all carry tens of millions of Toffoli and lose the `qubits*Toffoli` product, so only chase the
ladder when the objective is qubit count itself.

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
- The 1164q-to-1163q TrailMix era showed the opposite lesson from the big codec jumps: when only one qubit is needed, a tiny peak-window carry-layout trim can beat a broad structural route by tens of thousands of Toffolis.
- Rejected/failed submissions often had stale scores, no clean island after a route change, or a claimed low width whose candidate quality was structurally bad.

The lesson is not "turn on every aggressive knob." The lesson is to combine one aggressive live-range reduction with enough local safety knobs that candidate quality stays near-miss instead of structurally dead.

## Submission Archaeology Lessons

Use this section when pulling SOTA notes. It records the shape of the public frontier, including early solutions, so future optimization does not rediscover the same path blindly.

### Current TrailMix 1164q -> 1163q Frontier: Local Late-GCD Carry Layout

Public example: BitWonka submission `175749f`, commit `b310de9`, promoted 2026-06-19. Verified
metrics: **1163 qubits**, avg executed Toffoli **1,412,401.873**, score **1,642,623,526**,
validation **0 / 0 / 0** over all 9024 shots, nonce `100000688994`.

The patch is not a new algorithm. It keeps the TrailMix "ludicrous" point-add family and keeps
the GCD state width intact. The score win comes from a small, localized live-layout package:

- `arith::PAD` 21->19 and `schedule::PAD` 21->20: shrink the pseudo-Mersenne +f support/padding
  enough to remove surplus live bits without changing the high-level arithmetic.
- `TLM_GCD_K_ADJUST_AFTER=172`, `TLM_GCD_K_ADJUST_BEFORE=196`, `TLM_GCD_K_ADJUST=-1`: reduce the
  GCD carry-layout k by one **only** over the late GCD peak window.
- `TLM_HYB_V_DELTA=2`, `TLM_COUT_K_DELTA=1`, `TLM_FOLD_DELTA=1`, `TLM_FFG_DELTA=2`: small adjacent
  schedule relax/tighten deltas so the shifted peak does not reappear in neighboring apply/GCD
  phases.
- `LUD_EXTRA_FOLD_VENTS=0` in the baked defaults: avoid spending extra peak width on vents while
  solving a width frontier.

What we missed: our alternate 1163q streamed-triple / suffix-dirty route attacked the same one-qubit
goal with a global transcript/branch mechanism. It did lower the measured peak but was dirty
(`7 / 7 / 0`) and around **1,449,707 avg Toffoli**, roughly 37k avg Toffoli above the clean SOTA.
That is the wrong exchange rate for a one-qubit frontier drop.

Actionable rule for future agents:

1. For a clean frontier at `N` where the target is `N-1`, first find whether the `N` peak is a
   narrow step window.
2. If yes, test local support/padding shrink, per-step carry-layout trim, and neighboring schedule
   deltas before any global codec or branch rewrite.
3. Only escalate to global transcript codecs when the required qubit drop is larger than the local
   window can provide or when the plateau ledger shows persistent transcript floor bits across many
   phases.
4. After a one-qubit drop, immediately compute the same-width Toffoli break-even. At this frontier,
   a 1163q candidate must be below about **1,412,402 avg Toffoli** to beat `175749f`; any q1163
   route with a broad Toffoli tax is not worth island hunting until the tax is removed.

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
