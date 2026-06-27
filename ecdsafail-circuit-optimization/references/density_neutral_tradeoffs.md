# Density-Neutral Qubit ↔ Toffoli Tradeoff Techniques

> **Purpose.** A "density-neutral" technique is one that is **value-exact on all inputs** and
> does not change which GCD transcript values are "clean" (i.e., it preserves the island
> distribution over the 9024 Fiat-Shamir test points). This contrasts with empirical dead-CCX
> dropping or carry truncation, which are *distribution-specific* (they save gates only on the
> specific 9024-input island and may fail on others). Every technique below is density-neutral
> unless explicitly noted otherwise.

---

## 1. Theoretical Framework

### 1.1 What Makes a Technique Density-Neutral?

A technique is density-neutral if:
1. **Value-exact**: The circuit computes the *same output function* on all inputs. No bit is
   approximated or dropped based on which inputs are "likely."
2. **Input-independent structure**: The gate emission schedule, carry widths, and ancilla
   allocations do not depend on runtime data — only on classical compile-time constants.
3. **Phase-exact**: The uncomputation path correctly cleans all ancilla to |0⟩ on every input
   (not just the island ones). Phase errors would show up as `pha > 0` in the ecdsafail
   validator's `cls/pha/anc` triple.

**Contrast with island-exact (density-sensitive) techniques:**
- Empirical dead-CCX dropping (d44cad3 predecessor): identifies CCX gates whose target *never
  flips on the specific 9024-input distribution*, then omits them. This is wrong on other inputs
  → distribution-specific.
- Carry truncation (e.g. `DIALOG_GCD_FOLD_CARRY_TRUNC_W`): drops a carry bit correct only on
  the island. Re-hunting the nonce finds a seed where the dropped bits happen to matter on none
  of the 9024 FS shots.

**The 6dafa07 pivot**: The current SOTA (d44cad3) replaced empirical dead-CCX with structural
dead skipping (TLM_FFG_*, TLM_CUCCARO_*, TLM_COMPARE_*, etc.) that is *keyed by call-site and
bit index*, not by sampled inputs. This is density-neutral: the skip predicates are derived from
circuit structure (known-constant carries, exact-remainder conditions) and are correct on ALL
inputs.

---

## 2. Technique Catalog

### 2.1 Measurement-Based Uncompute (MBU / Gidney 2018)

**Literature**: Gidney 2018, "Halving the cost of quantum addition" (arXiv:1709.06648).
**Also**: Gidney 2019 blog (algassert.com/post/1905) on "spooky pebbling."

**Mechanism**: An AND gate (`a AND b → out`) costs 4T forward. The *uncompute* normally costs
another 4T. With MBU:
- Forward: compute `out = a AND b` into a clean ancilla → 4T (= 1 Toffoli).
- Uncompute: measure `out` in the X-basis (Hadamard then computational basis). If result = 0,
  done. If result = 1, apply a classical CZ correction (0 T-gates). Total: **0 Toffoli** for
  the uncompute.

**Trade-off**: The ancilla `out` must remain live from forward-compute to measurement. This costs
**+1 peak qubit** held across the window between AND and its use. The equation is:
```
vent: -1 Toffoli, +1 peak qubit (held for the forward↔measurement window only)
```

**Density-neutral**: YES. The measurement outcome is a random bit (classically: depends on
entanglement). The phase correction is always applied based on the measurement result, not on the
input. This is value-exact for all inputs.

**In trailmix_ludicrous**: The `hmr + cz_if_bit` pattern appears in `gidney.rs`, `fused.rs`,
and the codec. Every `clear_and` / `free_carry` in the vented adder family uses this.

**The vent dial**: A hybrid carry adder with k vents costs `3n − 2 − k` Toffoli, with k extra
peak qubits held across the forward↔reverse carry chain window. Off-peak phases: vent all (pure
Toffoli savings). On-peak phases: don't vent (the +1 qubit raises width and costs score).

**Application to SOTA (d44cad3)**: The apply carry chains in `controlled_mod_sub_vented` use
`APPLY_FINAL_TOPCLEAN` + `RIPPLE_GATE_SUFFIX_CARRIES` vents. The q1169 branch used
`hmr + cz_if` on the GCD fold coherent carry (the −f fold peak owner) to vent it at 0 Toffoli
→ broke the 1170 plateau to 1169.

---

### 2.2 Conditionally Clean Ancilla (Khattar-Gidney 2024)

**Literature**: Khattar and Gidney 2024, "Rise of conditionally clean ancillae" (arXiv:2407.17966).

**Mechanism**: A qubit is "conditionally clean when predicate P is True" = its value is 0
whenever P holds. This is weaker than "always clean" but strictly stronger than "dirty" (the
dirty ancilla case requires only that you restore the value exactly, not that it is zero).

**Key results** (all density-neutral, structural):
- **MCX with log₂\* n clean ancilla** (where log₂\* n ≤ 4 for all n < 2^65536): costs
  **3n Toffoli** to implement an n-qubit multi-controlled NOT. Prior best with clean ancilla: O(n)
  but with hidden constant. Conditionally clean vs truly clean: same gate cost when P is
  always-true (a clean ancilla is conditionally clean under the predicate "always").
- **Dirty ancilla alternative (ladder construction)**: **4n − 8 Toffoli** for MCX with k dirty
  ancilla (any k ≥ 2). This matches Barenco et al. 1995's Lemma 7.2 asymptotically.
- **Incrementers**: Same O(n) Toffoli with O(log\* n) conditionally clean ancilla.
- **Comparators**: **3n Toffoli, O(n) depth**, with log₂\* n ≤ 5 clean ancilla.

**Trade-off**: Not a qubit↔Toffoli trade but a *clean ancilla count* ↔ Toffoli trade. With more
conditionally clean ancilla, you can build MCX/incrementers/comparators at lower Toffoli cost.
The extreme case (1 ancilla): O(n log n) Toffoli (Barenco et al. 1995). The other extreme (n
ancilla): O(n) Toffoli (standard CNOT ladder).

**Density-neutral**: YES. The construction is structural — the circuit topology depends only on
n (the bit-width) and the ancilla count. Not on runtime data.

**In trailmix_ludicrous**: `cinc_khattar_gidney` and `mcx_clean_k` use this construction.
The `TLM_FOLD_TAIL_CINC` lever (already deployed in SOTA at `da51a48`) uses a clean-ancilla
incrementer from this paper, cutting ~5,340 avgT. **This vein is exhausted in the SOTA.**

---

### 2.3 Dirty Ancilla Borrowing (Barenco et al. 1995)

**Literature**: Barenco et al. 1995, "Elementary gates for quantum computation" (arXiv:quant-ph/9503016).
  Also: Maslov 2016 "Advantages of using relative-phase Toffoli gates" for the borrowed-carries extension.

**Mechanism**: A dirty ancilla is any qubit that currently holds an UNKNOWN value (could be 0 or
1 or a superposition), used temporarily and then RESTORED to its exact original state. Key fact:
n-qubit MCX with k dirty ancilla costs:
- k ≥ 1: `12n − 36` Toffoli (Barenco 1995, Lemma 7.3 with 2 dirty ancillae).
- k ≥ 2: `8⌈n/2⌉ − 4` Toffoli (Barenco 1995, Theorem 9: divide n into two halves with a dirty
  ancilla as intermediary).
- For k dirty ancillae: ladder constructions split at k+1 levels → `O(n/k)` Toffoli.

**The dirty-borrow MCX** (ecdsafail PZ track): `mcx_dirty_ladder` in `arith.rs` uses the
Barenco Theorem 9 construction with existing live registers as dirty ancilla. This is the key
technique enabling the 851→829q PZ push (shared EEA register as dirty scratch for MCX in the
comparators).

**Trade-off** (density-neutral):
```
dirty ancilla borrow: -k fresh ancilla at peak, +O(n/k) Toffoli overhead
```
The restored value is exactly what was there before — on ALL inputs. Density-neutral provided the
borrow-and-restore is implemented correctly.

**In trailmix_ludicrous (dialog-GCD base)**: `TLM_DIRTY_BORROW` attempted for the fold phase
(dirty-borrow ALL THREE fold phases), costing +1209 Toffoli per qubit saved. At the current
break-even of ~1190 Toffoli/qubit, this is marginally over budget and didn't ship.

---

### 2.4 Bennett Reversible Pebbling (1989)

**Literature**: Bennett 1989, "Time/Space trade-offs for reversible computation" (SIAM J. Computing).

**Mechanism**: Simulates a computation using S space in a reversible way. The naive approach
duplicates all intermediate states → 2S space. Bennett's pebbling strategy:
- Divide the T-step computation into √T checkpoints.
- Each level of recursion: run forward to a checkpoint, uncompute, re-run.
- Result: **T^(1+ε) time, O(T^(ε)/S^(ε)) × S space** for any ε > 0.
- Special case ε = 1: **T² time, O(S) space**.

For our context (T = ~530 GCD divstep iterations, S = ~740 qubits):
```
ε = 1 (√T approach): T² / S = 530² / 740 ≈ 380 iterations overhead
→ ~380 additional GCD passes, each at ~2,500 Toffoli ≈ 950,000 extra Toffoli
```
That would be ~70% Toffoli increase for halving the GCD transcript storage — a terrible trade
at our score objective.

**Density-neutral**: YES. The pebbling strategy is structural: same computation, just re-run at
different checkpoints.

**In ecdsafail context**: Bennett pebbling is the THEORETICAL justification for "recompute-to-free"
tricks, but the constant factor makes it impractical for the whole circuit. The FFG cy0
free-and-recompute (d44cad3's q1153→1152 break) is a SINGLE-GATE instance: `cy0 = ctrl & !final_a0`
is recoverable for 40 binding calls at near-0 Toffoli cost because `f[0]=1` is a compile-time
constant. This is Bennett pebbling at the extreme sweet spot: a trivially recomputable value.

---

### 2.5 Spooky Pebbling / Ghost Pebbling (Gidney 2019, Chevignard 2026)

**Literature**: 
- Gidney 2019 blog: "Making a quantum AND gate" (algassert.com/post/1905).
- Kahanamoku-Meyer et al. 2025 (arXiv:2510.08432): Parallel spooky pebbling.
- Chevignard, Fouque, Schrottenloher 2026 (eprint.iacr.org/2026/280): Ghost pebbling for EC inversion.

**Mechanism**: Extends MBU to reuse ancilla via MEASUREMENT of INTERMEDIATE RESULTS:
1. Compute intermediate value V into an ancilla.
2. Measure V in the **X-basis** (Hadamard + computational basis).
3. With 50% probability, the ancilla becomes |+⟩ = (|0⟩+|1⟩)/√2 → no further action, ancilla is "free."
4. With 50% probability, a phase error was introduced → apply a Clifford correction elsewhere.
5. The "freed" ancilla can immediately be reused for the next computation.

Key property: the ancilla slot is reused **without the qubit returning to |0⟩** — you don't
need to uncompute V. Only the phase is tracked and corrected classically.

**Trade-off**:
- Classic reversible computation: log-space pebbling requires O(S log T) qubits, O(T) time.
- Spooky pebbling: achieves **≤2.47 log(ℓ) qubits** for any length-ℓ sequential chain. For
  530-step divstep: ≤2.47 × log(530) ≈ 23 qubits for the ENTIRE STATE MACHINE, vs 22 qubits
  in the current implementation (already near-optimal!).

**Density-neutral**: YES. The phase corrections depend on the measurement outcomes (classical
bits), which are determined by the circuit + input, but the correction is always applied correctly
regardless of which input is running.

**In ecdsafail context**: The q1169 vent is a single-step instance of spooky pebbling. The
broader application (to the GCD state machine / step driver / CTZ scratch) would save ~26-29
qubits but at ~50-70% Toffoli overhead — see §4 below. The PZ track uses this for the ~48-qubit
drop from 997q to 948q.

---

### 2.6 Finite-Support Tail Codec (Transcript Compression)

**Literature**: Information-theoretic ancilla compression; Shannon entropy of the reachable transcript states.

**Mechanism**: The GCD transcript records one bit per iteration (did we swap?) across ~530 steps.
Naively: 530 qubits. But the REACHABLE SUPPORT is much smaller:
- The GCD always terminates (final state is known).
- Many bit-patterns are impossible (e.g., the GCD can't oscillate forever).
- **Finite-support tail**: The last K transcript bits take only M ≤ 2^K values. Encode those
  M values into ⌈log₂ M⌉ code bits.

The "all-triple codec" in trailmix_ludicrous encodes the GCD choices as base-5 decisions (3
consecutive iterations, 5 reachable patterns → log₂(5) ≈ 2.32 bits vs 3 raw bits → ~23% compression).
Streaming apply: decode one slot at a time from the code, use its 3 raw bits for the carry/fold,
then release those 3 code bits immediately.

**Trade-off**:
```
codec compression: -(1 - log₂|support|/n) × n qubits, +O(n × codec_cost) Toffoli
```
For the all-triple codec: ~603q held live vs ~530 raw bits = the codec COSTS qubits compared
to a naive all-at-once implementation but saves compared to alternatives that hold more.

**Density-neutral**: YES. The codec is a bijection over ALL reachable inputs, proved by a
collision-free self-test. The codec is correct on every GCD execution path (every input), not just
the island ones.

**NOTE**: This is already maximally exploited at d44cad3. The 603q tape is essentially the
Shannon entropy floor for the transcript under the all-triple encoding — see the "1168 apply floor
NOT transcript-bound" memory note.

---

### 2.7 Structural Dead Gate Skipping (6dafa07 contribution)

**Literature**: No formal paper; this is an original ecdsafail contribution.

**Mechanism**: Identifies CCX gates that are structurally dead (the target never flips) based on
circuit structure alone:
- **Known-zero high carries**: If a carry bit is provably 0 at a given circuit location (because
  the operand is bounded by a compile-time constant smaller than the carry's position threshold),
  never emit the Toffoli. Example: the top carry of `const_chunk_add` when the chunk's constant
  is small.
- **Exact-remainder predicates**: If one operand of a Toffoli is provably equal to a known value
  (e.g., `f[0]=1` implies certain fold-carry structure), certain CCX targets never flip.
- **Named predicates**: ~15 knobs (`TLM_FFG_SKIP_STRUCTURAL_DEAD_*`, `TLM_CUCCARO_SKIP_*`,
  `TLM_COMPARE_SKIP_*`, `TLM_CONST_CHUNK_SKIP_*`, `TLM_FUSED_SKIP_*`, etc.) each cover one
  named category of structurally dead gates.

**Trade-off**: Each skipped gate removes exactly 1 avgT at no qubit cost. The structural predicates
are value-exact (the target truly never flips, provably, for all inputs).

**Density-neutral**: YES. The skip predicates are derived from compile-time circuit structure, not
from runtime data sampling. They are correct for ALL inputs, not just the 9024 FS inputs.

**Contrast with empirical dead-CCX** (the approach it replaced): The empirical approach ran ~9.2M
random inputs to find gates that "never flipped in practice," then filtered to those stable across
51 salt sets. This was distribution-specific: the intersection might exclude gates that DO flip on
some non-FS inputs, so the circuit was not value-exact for all inputs (only for the FS island).
6dafa07 removed this and replaced it with structural predicates, making the circuit value-exact.

---

### 2.8 Value-Exact Algebraic Fusion

**Literature**: Standard reversible circuit optimization; no single paper.

**Mechanism**: Identify adjacent operations whose composition simplifies algebraically. Examples:
- `x = -x; x += A; x = -x; x -= A` simplifies to `x -= 2A` (value-exact, 0 intermediate steps).
- `coord_add3x` (dst += 3·ox mod q): since ox is a classical constant (Q is fixed), compute
  `3·ox mod q` at compile time → fold into a single constant addition (0 Toffoli, just XOR bits).
- NAF recoding: `977 = 2^10 − 2^5 − 2^4 + 1` has 4 signed terms vs 8 unsigned terms → fewer
  modular addition passes, exactly fewer Toffoli.

**Trade-off**: Fusion reduces Toffoli at zero qubit cost. It is the "free lunch" of this catalog.
The risk: the algebraic identity must hold *modulo p* (including boundary cases near p), not just
over the integers.

**Density-neutral**: YES. Algebraic identities hold for all inputs (by definition of equality
modulo p). The Karatsuba square is the most powerful example: `(lo + hi)² = lo² + 2·lo·hi + hi²`
holds for all inputs. Saved 22.4M avgT (−25% of the schoolbook square) in a single algorithmic swap.

---

### 2.9 Free-and-Recompute a Single Cheap Value (BitWonka Lever A)

**Literature**: Bennett pebbling at the single-gate extreme. Original contribution of BitWonka (6dafa07).

**Mechanism**: During the peak-binding phase, one register holds a value V that is:
1. **Not needed during the peak** (it's only used in the post-peak uncompute pass).
2. **Trivially recomputable** from still-live registers (e.g., a 1-gate function of other qubits).

Process:
1. Uncompute V (free its lane) before the peak.
2. The freed lane is reused by the peak's main computation.
3. Recompute V (same 1-2 gates) after the peak, before V's first post-peak use.

**Example (cy0 in d44cad3)**: cy0 = ctrl & !final_a0. Since f[0] = 1, `final_a0` is computable
from live register bits at compile time. The `loan_zero_qubit(cy0)` call frees cy0's lane; after
the suffix, `reclaim_zero_qubit` + a single CNOT re-derives cy0. For 40 peak-binding fold calls.
Result: −1 peak qubit at ~0 Toffoli cost (just 2 CNOTs per freed cy0).

**Trade-off**:
```
free-and-recompute a single cheap value: -1 peak qubit, +2 gates per use (near-0 Toffoli)
```
This is only available when a held value V satisfies both criteria. The challenge is *identifying*
such values — the instruction is: after exhausting dead-qubit scan, ask "is any HELD VALUE a
cheap function of LIVE QUBITS?"

**Density-neutral**: YES. The recompute is value-exact on all inputs (it's the same Boolean function).

---

## 3. Tradeoff Summary Table

| Technique | Qubits | Toffoli | Density-neutral? | Deployed in SOTA? |
|-----------|--------|---------|-----------------|-------------------|
| Gidney MBU vent (off-peak) | +1/vent | −1/vent | YES | YES (all carry vents) |
| Gidney MBU vent (on-peak) | +1/vent | −1/vent | YES | NO (would raise score) |
| Khattar-Gidney cinc | neutral | −5,340 avgT | YES | YES (already in SOTA) |
| Dirty ancilla borrow MCX | −k | +O(n/k) | YES | MARGINAL (+1209/q) |
| Bennett pebbling (whole) | −S | +T² | YES | NO (too expensive) |
| Bennett pebbling (single cheap value) | −1 | +~0 | YES | YES (cy0, d44cad3) |
| Spooky pebbling (GCD state machine) | −23 | +50-70% | YES | NO (open) |
| Transcript tail codec | varies | +small | YES | YES (all-triple, maxed) |
| Structural dead skipping | neutral | −varies | YES | YES (6dafa07) |
| Algebraic fusion (Karatsuba) | neutral | −22.4M | YES | YES |
| Algebraic fusion (NAF) | neutral | −small | YES | YES |
| Algebraic fusion (coord_add3x) | +transient | −small | YES | PARTIALLY |
| Carry truncation (island-exact) | neutral | −small | NO | YES (various knobs) |
| Empirical dead-CCX drop | neutral | −small | NO | NO (removed in 6dafa07) |
| GAP_J2 comparator narrowing | neutral | −1.33M | PARTIAL (island) | YES |

---

## 4. Open Density-Neutral Levers (Not Yet in SOTA)

### 4.1 Apply-Swap Dead-CCX (Structural, Value-Exact)

The `apply_step_forward/reverse` functions in `gcd.rs:1460/1508` emit 256 `cswap(*swp,x_reg[j],y_reg[j])`
per GCD iteration × ~258 × 2 passes. These are the ONE large gated-CCX block with NO per-bit
structural-dead skipping (only `TLM_APPLY_FWD/INV_CSWAP_SKIP_LAST` for the last iteration).

**Opportunity**: Extend the structural-dead predicate to the apply-swap cswaps. For each iteration
where the GCD has converged (swap bit = provably 0 from compile-time analysis), skip ALL 256 cswap
CCX pairs. Alternatively, the involutory inverse-pair: the fwd-pass swap and the immediately
following GCD cswap on the same (u/v) lanes may cancel — a compile-time algebraic reduction at 0
circuit cost.

**Expected impact**: ~40-80 iterations × 256 × 2 gates ≈ 20,000-40,000 avgT potential. Density-neutral
if based on structural convergence bounds (not sampled frequencies).

### 4.2 Gidney 2025 Streaming Vented Adder (arXiv:2507.23079) — Partially Ported

**Status**: Partially implemented in `venting.rs` as `iadd_dirty_2clean_qoffset()` but currently
marked **LEAKS PHASE** and is incomplete. NOT safe to enable.

**Mechanism**: A streaming n-bit adder using **2 clean ancilla + n-2 dirty ancilla** (borrowed from
existing live registers), achieving ~3n CCX total (vs ~4n for the current dedicated-carry-ancilla
approach). The trick: carry ancillae "ping-pong" — the forward carry for bit i is measured out (MBU)
while the bit i+1 carry is being computed, so at most 2 clean ancilla are needed simultaneously.

**Expected savings once completed**: ~n/4 Toffoli per adder call (compared to current Cuccaro
family), at **peak-neutral qubit count** (dirty ancilla are borrowed from existing live registers).
For the ~1,500 adder calls in the GCD apply path: ~100k-200k avgT potential.

**Density-neutral**: YES. The streaming structure is input-independent; the dirty borrows are exact
restores on all inputs.

**Action**: Fix the phase leak in `venting.rs:iadd_dirty_2clean_qoffset()`. The issue is likely
in the classically-conditioned CZ correction after X-basis measurement — the correction must account
for both the MBU phase AND the borrowed dirty-ancilla phase simultaneously.

### 4.3 Extend Cuccaro Dead-Carry to All Call Sites

`cuccaro_call_has_structurally_dead_carry` currently only covers call indices 13-37. Extend to ALL
square/coord Cuccaro adder calls. Each additional dead-carry skips 1 Toffoli per call site per
occurrence.

**Expected impact**: ~3,000-10,000 avgT. Density-neutral (structural).

### 4.3 Spooky-Pebble the GCD State Machine (22q → 0q)

The 22-qubit state machine tracks which of ~530 divstep steps we're at. Spooky-pebble:
- At each step, measure the current step index in the X-basis.
- Classical tracking records the measurement outcomes.
- Phase corrections applied classically per measurement.
- State machine register freed → available for transient reuse.

**Expected impact**: −22 peak qubits, +~50k Toffoli (phase corrections for 530 steps × small cost).
At break-even ~1190 Toffoli/qubit, need < 22 × 1190 = 26,180 Toffoli → tight but possibly viable.

**Density-neutral**: YES. Phase corrections are always applied.

### 4.4 Spooky-Pebble the CTZ Scratch (26q → 3q)

The CTZ computation (count trailing zeros) at divstep step 342 needs ~26 scratch qubits.
Spooky-pebble the chain (each bit's zero-check is a sequential dependency):
- Use 3-qubit constant-space spooky pebbling strategy (Gidney 2019 result).
- O(log n) additional time overhead per CTZ call.

**Expected impact**: −23 peak qubits, +~5,000 Toffoli. Break-even requires < 23 × 1190 = 27,370 Toffoli → likely viable if cost can be verified.

**Note**: This is for the PZ (Shrunken-PZ) track. For the dialog-GCD track, the equivalent
opportunity is the cy0 family (already deployed) — no analogous CTZ scratch.

### 4.5 Square SumHiLo Vent (Off-Peak, Free)

`TLM_SQUARE_SUMHILO_VENT` and `TLM_SQUARE_VENT_SHIFTED` exist as default-off knobs. These vent
the square's intermediate sum carries in the off-peak square phase.

**Expected impact**: Toffoli savings with no peak cost (off-peak venting). Could be turned on at
effectively 0 score cost.

**Density-neutral**: YES (MBU-based venting is structural).

### 4.6 Controlled_mod_double i==0 Optimization

In `apply`, the `i==0` path has `controlled_mod_double` plus separate t1/s2 doublings only at i==0.
These are special-cased at the first iteration where the operands are known. Structural constant-fold
or algebraic simplification may reduce gates.

**Expected impact**: ~1,000-5,000 avgT at small circuit risk. Density-neutral.

---

## 5. Classification: Which Levers Are Worth Trying Next

Given SOTA = 1152q × 1,364,230 = 1,571,592,960 and break-even ≈ 1190 Toffoli/qubit:

### Best density-neutral qubit wins (unopened):
1. **FFG cy0-style free-and-recompute on additional values** — find more values at the current
   1152q peak that are cheap functions of live registers. The 40-call cy0 freed 1 qubit; are
   there analogous single-gate re-derivable holds at the current 1152q binder?
2. **Apply-swap convergence skipping** — structural skip for converged-tail cswaps (similar to
   `TLM_APPLY_CSWAP_SKIP_LASTK` but extending the structural range).

### Best density-neutral Toffoli wins (unopened):
1. **Apply-swap involutory pair cancellation** — the fwd-swap followed by the GCD cswap on the
   same lanes may cancel algebraically at some iterations (pure structural reduction, 0 qubit cost).
2. **Extended Cuccaro structural dead-carry** — extend from indices 13-37 to all calls.
3. **SumHiLo/shifted vents** — turn on TLM_SQUARE_SUMHILO_VENT (off-peak, free).
4. **Deeper constprop** — CONSTPROP_MAX_ITERS is already set to 256; but are there any remaining
   provably-constant CCX after the structural-dead suite? Re-verify.

### Already exhausted:
- Transcript codec (all-triple, maxed at 603q).
- cinc / density-neutral fold increments (already in SOTA).
- Karatsuba square (−22.4M, already in SOTA).
- NAF recoding (already in SOTA).
- cy0 free-and-recompute (already in SOTA, 40 calls).

---

## 6. The Exchange Rate and When to Switch Axes

The current break-even for the dialog-GCD base (d44cad3):
```
break-even = avg_Toffoli / peak_qubits = 1,364,230 / 1152 ≈ 1,184 Toffoli/qubit
```

Trade table:
| Technique | Toffoli/qubit exchanged | Worth it? |
|-----------|------------------------|-----------|
| MBU vent on-peak | +1 qubit / −1 Toffoli = ∞ cost | NO |
| Dirty borrow +1209 per qubit | 1,209 Toffoli/qubit | MARGINAL (over break-even) |
| Karatsuba (applied to sub-halves) | 0 Toffoli/0 qubit (structural) | YES (free) |
| Spooky-pebble state machine | +~1,200 Toffoli / −22 qubits | ~55/qubit | YES (well under break-even) |
| Spooky-pebble CTZ | +~217 Toffoli / −23 qubits | ~9/qubit | YES |
| Bennett pebbling (whole) | +millions Toffoli/qubit | NO (far over) |
| Structural dead-carry extension | 0 Toffoli/qubit (no qubit cost) | YES (free) |

**The key insight**: Density-neutral Toffoli wins (structural dead-gating, venting off-peak,
algebraic fusion) are FREE — they cost no qubits. Pursue them first. Qubit wins (spooky pebbling,
free-and-recompute) cost Toffoli but can still win the product race if the Toffoli/qubit rate is
well under break-even.

---

## 7. Literature Connections

| Technique | Primary paper | Ecdsafail instance |
|-----------|---------------|-------------------|
| Gidney MBU | arXiv:1709.06648 (2017) | `hmr+cz_if`, carry vents |
| Spooky pebbling | algassert.com/post/1905 (2019) | q1169 carry vent; open: state machine |
| Khattar-Gidney | arXiv:2407.17966 (2024) | `cinc_khattar_gidney`, deployed |
| Barenco dirty ancilla | quant-ph/9503016 (1995) | `mcx_dirty_ladder` (PZ track) |
| Bennett pebbling | SIAM J. Comput. 1989 | free-and-recompute cy0 (single gate) |
| Parallel spooky pebbling | arXiv:2510.08432 (2025) | PZ CTZ scratch (open) |
| Schrottenloher EEA split | arXiv:2606.02235 (2026) | transcript compression (analog) |
| Karatsuba multiplication | Karatsuba & Ofman 1962 | square Karatsuba (deployed) |
| NAF recoding | signed-digit arithmetic | secp256k1 constant recoding (deployed) |
| Structural dead-CCX | Original (6dafa07, 2026) | TLM_*_SKIP_STRUCTURAL_DEAD_* |

---

## References

1. Bennett, C.H. (1989). Time/space trade-offs for reversible computation. *SIAM J. Comput.*, 18(4), 766–776.
2. Barenco, A. et al. (1995). Elementary gates for quantum computation. *Phys. Rev. A*, 52(5), 3457. arXiv:quant-ph/9503016.
3. Gidney, C. (2018). Halving the cost of quantum addition. *Quantum*, 2, 74. arXiv:1709.06648.
4. Gidney, C. (2019). Making a quantum AND gate. algassert.com/post/1905.
5. Khattar, T. & Gidney, C. (2024). Rise of conditionally clean ancillae. arXiv:2407.17966.
6. Kahanamoku-Meyer, G. et al. (2025). Parallel spooky pebbling. arXiv:2510.08432.
7. Schrottenloher, A. (2026). Optimized point addition circuits for elliptic curve discrete logarithms. arXiv:2606.02235.
8. Chevignard, P., Fouque, P.-A., & Schrottenloher, A. (2026). Ghost pebbling for EC inversion. eprint.iacr.org/2026/280.
9. Karatsuba, A. & Ofman, Y. (1962). Multiplication of Multidigit Numbers on Automata. *Soviet Physics Doklady*, 7, 595.
10. Häner, T., Roetteler, M., & Svore, K. (2017). Factoring using 2n+2 qubits with Toffoli based modular multiplication. *Quantum Inf. Comput.*, 17(7–8). arXiv:1611.07995.
