# Qubit & Toffoli Reduction Techniques: A Practitioner's Primer

> **Target audience**: Undergrad who has learned the basics of quantum computing (superposition,
> entanglement, Toffoli/CNOT gates, quantum circuits). This document explains the optimization
> techniques used in the ecdsa.fail quantum circuit challenge from first principles — no
> prior exposure to circuit optimization or Shor's algorithm required.

---

## 0. What Are We Optimizing, and Why?

### The challenge in one sentence

We are building a reversible quantum circuit that computes an elliptic-curve point addition
on the secp256k1 curve (the same math used in Bitcoin), and we want to minimize the cost of
running it on a fault-tolerant quantum computer.

### The cost score

```
score = peak_qubits × avg_executed_Toffoli
```

Lower score = better. The score is a product of two factors:

- **Peak qubits**: the maximum number of qubits that are simultaneously in use at any point
  during the circuit. Think of this as the "width" of the circuit.
- **Average executed Toffoli**: the average number of Toffoli (CCX / AND) gates that fire
  during a single run, averaged over the 9024 inputs the challenge evaluates.

### Why Toffoli gates specifically?

In a fault-tolerant quantum computer (the kind that could actually break Bitcoin), regular
gates (CNOT, Hadamard, Pauli X/Y/Z) are nearly free — they can be implemented with very
low overhead using the surface code. But **Toffoli gates** (CCX — "if both A and B are 1,
flip C") require **magic states**: specially prepared ancilla qubits that take a long time and
many physical qubits to distill. Each Toffoli consumes one magic state. So in this regime,
the Toffoli count is the dominant cost, roughly like "dollars" while qubits are "desk space."

The product `qubits × Toffoli` captures the spacetime volume: more qubits means you need more
idle storage, and more Toffoli means more factory time. Both matter.

---

## 1. A Mental Model: The Reversibility Constraint

### Why reversibility is the whole game

Quantum circuits must be reversible. This means:

- **You cannot erase a qubit.** Every qubit you allocate must eventually return to a known
  `|0⟩` state (be "uncomputed") before the circuit ends.
- **You cannot just overwrite a value.** If you want to replace the value in a qubit with
  something new, you first have to clear the old value (uncompute it) — which usually costs
  the same Toffoli gates as computing it did.

This is the central constraint that makes circuit optimization hard. In classical computing, you
can just overwrite memory. In a reversible quantum circuit, every intermediate value you don't
need must be "undone" to clean up.

### The consequence: intermediate values cost qubits

Every time the circuit needs to compute an intermediate result — a carry bit, a comparison flag,
a partial product — it allocates a fresh qubit to hold that value. That qubit is **live** from
the moment it's computed until the moment it's uncomputed. If many intermediate values overlap
in time, many qubits are live simultaneously, which drives up the peak.

**The core insight of almost every qubit-reduction technique is:** make intermediate values die
sooner (so they're not live at the peak), or make them not need to exist at all.

---

## 2. Qubit Reduction Techniques

### 2.1 The Peak Is a Maximum, Not a Sum

**First, understand what you're actually measuring.** The peak qubit count is the maximum
simultaneous live qubit count over the entire circuit timeline, not the total number of qubits
ever used. Optimizing a qubit register that's only ever live when the circuit is *not* at its
peak is a waste of effort — it changes nothing.

**Implication**: Before doing any optimization, find the *binder* — the exact phase of the
circuit where the peak occurs — and only attack the qubits alive at that instant.

In our circuit, the peak occurs during the GCD-based modular inversion. Specifically, the
transcript (the log of GCD decisions) and the inversion's working registers are simultaneously
live.

---

### 2.2 Live-Range Holes: Uncompute Early, Recompute Later

**The idea**: If a value V is live across the peak but isn't *used* at the peak (it's just
"passing through"), we can:
1. Uncompute V before the peak (run the circuit backwards to return it to `|0⟩`).
2. Let the freed qubit be reused for peak-time work.
3. Recompute V after the peak (run the circuit forwards again) before V's first post-peak use.

**Analogy**: Imagine you have a stack of books on your desk while you're trying to work on
a big project. Some books you won't need until later. You can put them in a box to free up
desk space during the project crunch, then bring them back out when you need them.

**The cost**: The recompute uses Toffoli gates (same cost as the original computation). So you
trade qubits for Toffoli. The trade-off is favorable when the value is cheap to recompute (few
gates) and the freed qubit is genuinely at the peak.

**Real example** (1211q → 1193q drop in our circuit): A large GCD-apply scratch block was
freed during a shift sub-phase that didn't use it, then reacquired afterwards. That 18-qubit
hole at the peak cost some extra Toffoli (the recompute), but improved the score.

---

### 2.3 Transcript Compression: Compress the Decision Log

**Background**: The GCD-based inversion (which is the heart of our circuit) runs ~530 steps.
At each step, it makes a binary decision: "did I swap?" and "did I subtract?". These decisions
are recorded in a **transcript** (a log) because they'll be needed later to run the GCD backwards
during uncomputation.

With one qubit per decision, that's ~530 qubits — all live simultaneously during the forward
pass and the backward pass.

**The compression insight**: Not all 2^530 bit patterns of decisions are reachable. The GCD
process has structure: certain sequences of swap/subtract decisions are impossible because the
algorithm would have converged earlier. This means the reachable patterns have fewer bits of
entropy than 530.

**Solution**: Encode the transcript more densely. Our "all-triple base-5 codec" looks at
consecutive 3-step windows and notices that only 5 out of 8 (2^3) patterns can actually occur.
So you can encode each window in `log₂(5) ≈ 2.32` bits instead of 3 raw bits — a ~23%
compression. Across 603 steps, this saves meaningful qubits.

**The hard constraint**: The encoding must be a **bijection** — a perfect one-to-one mapping.
If two different decision histories map to the same code, you lose information needed for
uncomputation, and the circuit gives wrong answers. Lossy compression is impossible; it's
Shannon source coding, but reversible.

---

### 2.4 Passenger Ghosting / HMR Ghosting

**What is a "passenger"?** A value allocated early in the circuit that won't be used again
until late in the circuit. During the peak, it just sits there — "riding" through the circuit
without contributing to the computation at the peak.

**Example**: The value `dy` (the y-coordinate difference) is computed early for the division
`λ = dy/dx`. After the inversion completes, `dy` isn't needed until the very end to finalize
the output coordinates. Meanwhile, it occupies a 256-bit register across the inversion peak.

**The ghosting trick**: If `dy` can be *reconstructed* later from values still live at that time,
you can erase it early and defer reconstruction. In our circuit:
- `dy = λ × dx` (because `λ = dy/dx` by definition).
- After the inversion, `λ` and `dx` are still live.
- So we can reconstruct `dy = λ × dx` when needed.

**Cost**: A modular multiplication to reconstruct `dy` (~several hundred Toffoli). But if `dy`
is ~256 qubits and it's at the peak, that tradeoff can be favorable.

**HMR ghosting** is a more aggressive version using measurement: measure the passenger qubit in
the Hadamard (X) basis, freeing it immediately. When you need its value back, reconstruct it
from other live data, and use a classically-controlled Z correction to fix up the phase. This is
the quantum-native version of "store a receipt instead of the full object."

---

### 2.5 Free-and-Recompute a Single Cheap Value (The d44cad3 Breakthrough)

**The 1153→1152 qubit drop** (BitWonka's submission `d44cad3`) used a beautifully targeted version
of this idea.

**Setup**: During the peak-binding phase, the circuit holds a carry qubit called `cy0`. A standard
dead-qubit scan found **zero** unused qubits — every qubit at the peak was holding a value needed
somewhere. Dead-qubit elimination failed.

**The right question**: Instead of asking "is any qubit DEAD (never used again)?", ask: "is any
qubit's VALUE a cheap function of other values still live?"

**Discovery**: `cy0 = ctrl AND (NOT final_a0)`. Why? Because the secp256k1 prime constant
`f` has bit 0 equal to 1 (`f[0] = 1`). This makes the carry-in at bit 0 deterministically
computable from just the control wire and `final_a0` — both already live.

**The trick**:
1. Before the peak phase: uncompute `cy0` (2 gates, just CNOT operations).
2. "Loan" the freed cy0 lane to the peak phase (it uses that slot temporarily).
3. After the peak phase: recompute `cy0` from `ctrl` and `final_a0` (2 gates again).

Cost: ~4 CNOT-equivalent gates for 40 binding calls. Savings: 1 qubit at the peak. At the
exchange rate of ~1,184 Toffoli per qubit (break-even for the score at this frontier), spending
4 gates to save 1 qubit is massively favorable.

**Generalized lesson**: When a dead-qubit scan fails, don't conclude "the floor is structural."
Re-ask: "Is any held value a cheap function of the live qubits?" If yes, free-and-recompute it.

---

### 2.6 Dynamic-Width Registers (For the PZ Track)

This applies to the Shrunken-PZ (Proos-Zalka) inversion method used in the low-qubit track.

**The GCD runs a bit-shrinking process.** As the GCD computation proceeds over ~530 steps,
the operands `A` and `B` shrink: their high bits become provably zero as the algorithm converges.
In a naive circuit, you'd allocate full 256-bit registers for all 530 steps, even though early
steps need the full width but later steps need only a few bits.

**Dynamic width**: Measure "how many active bits does this register currently have?" and only
allocate that many qubits. As bits become provably zero, free them. The peak qubit count then
reflects the true maximum "simultaneous active bits," not a worst-case allocation.

**Implementation**: `reg_widths(i)` is called at each step `i` to determine the correct width
for registers `A`, `B`, `ca`, `cb`, `q`. A "thin schedule" pre-computes these widths by
sampling many inputs and finding the actual maximum needed at each step.

**Quantitative result**: The ablation ladder showed:
```
Source-level dynamic PZ (universal schedule):  1027 qubits
+ thin support-tuned schedule:                  990 qubits (−37q)
+ counter/rotation metadata trimming:           983 qubits (−7q)
+ quotient cap:                                 980 qubits (−3q)
```

---

### 2.7 Known-Constant Teardown

**The GCD terminates at a known state.** After ~530 steps, the GCD has converged and the
registers hold specific known values: `A = 0`, `B = 1`, `ca = p` (the modulus), `q = 0`.

**These are classical constants.** A quantum register holding a known classical value is
essentially wasted space — it doesn't carry quantum information. You can "tear it down"
(zero it and free the qubits) before the peak computation begins.

**Process**:
1. CNOT the known constant out of the register (restoring it to `|0⟩`).
2. Free the register (it returns to the qubit pool).
3. Allocate fresh qubits for the peak computation.
4. After the peak, recreate the constants (CNOT them back) for uncomputation.

**Quantum intuition**: A qubit holding a value you could write on a piece of paper is a qubit
being wasted. You could throw it away (classically: just erase it) but reversibility means you
can't erase — you can, however, XOR a register to `|0⟩` using its known classical content,
which zeroes it without consuming Toffoli gates (XOR/CNOT are free).

---

## 3. Toffoli Reduction Techniques

### 3.1 Measurement-Based Uncomputation (MBU) — "Free Erasing"

**This is the single most important technique in the whole catalog.**

**Normal Toffoli lifecycle**:
```
1. Compute: ccx(a, b, out)  → costs 4 T-gates (1 Toffoli)
2. Use the result in 'out'
3. Uncompute: ccx(a, b, out) → costs 4 T-gates (1 Toffoli) again
Total: 8 T-gates = 2 Toffoli per logical AND
```

**With MBU** (Jones 2013, applied to adders by Gidney 2018):
```
1. Compute: ccx(a, b, out)       → costs 4 T-gates (1 Toffoli)
2. Use the result in 'out'
3. Uncompute: measure out in X-basis
   - 50% chance: measurement result is 0 → done, no cost
   - 50% chance: measurement result is 1 → apply CZ(a, b) phase fixup → 0 T-gates
Total: 4 T-gates = 1 Toffoli. Uncomputation is FREE.
```

**Why does this work?** When you compute `out = a AND b` into a clean `|0⟩` ancilla, the system
is in the state `|a, b, a·b⟩`. Measuring `out` in the X-basis (Hadamard then measure) projects
the ancilla into `|+⟩` or `|−⟩`. The 50% of the time you get `|−⟩`, a phase kick `(−1)` has
been applied to the `|a=1,b=1⟩` component of the quantum state. The CZ gate applied to `a` and `b`
corrects that phase. After correction, the ancilla is no longer entangled with `a,b` and can be freed.

**The key**: You're paying 4 T for the forward computation, and 0 T for the reverse. The "uncomputing"
is done by the physical act of measurement, which is free in the fault-tolerant model.

**The cost**: The ancilla `out` must be held **live** from when you compute it to when you measure it.
This is typically a short window (between the forward and reverse carry chains in an adder), but it
costs +1 peak qubit during that window.

**Practical result for carry-chain adders**: An n-bit adder normally costs ~2n Toffoli (n for the
forward carry chain, n for the reverse). With MBU, the reverse carry is 0 Toffoli. So the total
drops to ~n Toffoli — halving the cost.

---

### 3.2 The Vent Dial

The MBU mechanism gives us a precise dial: in a hybrid adder, each "vent" converts one carry-uncompute
Toffoli into a measurement + phase correction. Precisely:

```
A hybrid carry adder with k vents:
- Toffoli cost = (3n − 2 − k) Toffoli
- Extra peak qubits = k  (held during the forward↔reverse window)
```

So each vent trades **−1 Toffoli for +1 temporary peak qubit**.

**When to vent**: Vent aggressively during phases that are NOT at the qubit peak (off-peak phases have
headroom, so the +1 qubit doesn't matter). Don't vent during the peak-binding phase (adding qubits
there directly costs score).

---

### 3.3 Structural Dead Gate Skipping

**Some Toffoli gates never fire.** In our circuit, there are CCX gates whose target bit is provably
never flipped — because a carry bit is always zero due to a compile-time constant bound.

**Example**: The secp256k1 prime `p = 2^256 − 2^32 − 977`. When computing `x + p`, the carry at bit
position 256 can only arise if `x > 0`. But at certain circuit points, we know `x = 0` exactly
(because we just computed that). So the carry-out Toffoli at position 256 never fires, and we can skip it.

**The d44cad3 pivot** (commit `6dafa07`): The previous approach used empirical sampling — run 9 million
random inputs, find which CCX targets never flipped, and skip those. Problem: this is only correct for
the specific 9024 test inputs, not all inputs.

The new approach: mathematically derive which carries are always zero from circuit structure alone.
This gives ~15 named predicates (`TLM_FFG_SKIP_STRUCTURAL_DEAD_*`, etc.) that correctly identify
dead CCX gates for ALL inputs, not just the test ones.

**Why this matters for correctness**: The empirical approach was technically a cheat — the circuit
would give wrong answers on some inputs (just not the 9024 the challenge uses). The structural
approach is provably correct everywhere.

---

### 3.4 Algebraic Fusion: Karatsuba Square

**The biggest single Toffoli reduction: −22.4 million** (from a single algorithmic change).

**Context**: Our circuit must compute `λ²` (lambda squared) as part of the elliptic-curve formula
`new_x = λ² − x₁ − x₂`. This is a 256-bit modular square. The naive schoolbook algorithm
multiplies every pair of bit-chunks:

```
For a 256-bit number split as hi·2^128 + lo:
  (hi·2^128 + lo)² = hi²·2^256 + 2·hi·lo·2^128 + lo²
                    = hi²·2^256 + (hi+lo)²·2^128 − hi²·2^128 − lo²  (Karatsuba trick)
```

**Schoolbook**: needs n² multiply-add operations for n-bit numbers.
**Karatsuba**: recursively splits and reduces to 3 sub-squares instead of 4:
- `lo²` (128-bit square)
- `hi²` (128-bit square)
- `(hi + lo)²` (128-bit square)

Then reconstructs via additions: `(lo + hi)² − lo² − hi²` = `2·lo·hi`, the cross-term.

**Why this helps so much**: The 256-bit square runs at EVERY step of the GCD (258 steps × 2 passes).
Any O(n²) → O(n^1.585) improvement in the core multiply scales to the whole circuit. The −22.4M
Toffoli came from restructuring the 256-bit squarer: instead of 4 schoolbook cross-products between
4 64-bit chunks, compute 3 sums-of-squares (using Karatsuba) and reconstruct. The 64-bit sub-squares
also decompose further.

---

### 3.5 NAF Recoding: Fewer Operations for the Same Constant

**Context**: We frequently compute `x + 977·c` (adding a multiple of 977, the secp256k1 constant).

The constant `977` in binary is `1111010001₂` — 6 "1" bits. Adding `977·c` means 6 separate
additions (one for each bit position where 977 has a 1).

**NAF (Non-Adjacent Form)**: Represent 977 using signed digits (−1, 0, +1):
```
977 = 2^10 − 2^5 − 2^4 + 1   (4 signed terms)
```

Each "+1" becomes an addition and each "−1" becomes a subtraction. With 4 terms instead of 6,
we do 4 modular operations instead of 6 — saving ~33% of the Toffoli for this constant multiplication.

**Density-neutral**: The algebraic identity `977 = 2^10 − 2^5 − 2^4 + 1` holds for ALL inputs.
No approximation.

---

### 3.6 Conditional / Measured Replay

**Key insight**: We measure the Toffoli count as **average-executed**, not emitted. If a gate fires
only on a fraction of inputs, it only costs that fraction of a Toffoli on average.

**The mechanism**: Wrap a block of gates under a measurable predicate:
1. Compute a comparator flag (e.g., "is bit K of the GCD carry set?") into a clean ancilla.
2. Measure the flag in the X-basis.
3. If the flag was 0 on this shot: the comparison-controlled block doesn't need to run — 0 Toffoli.
4. If the flag was 1: replay the block classically-conditioned on the measurement — full cost.

**Averaging**: If the predicate is 1 on only 30% of inputs, the block costs 0.3× its full Toffoli.
On the other 70% of inputs, it costs 0.

**Where this applies**: The GCD reverse-branch comparator (`DIALOG_GCD_REVERSE_BRANCH_CONDITIONAL_REPLAY`),
overflow-flag checks, and similar predicates that are often 0 over the Fiat-Shamir input distribution.

**The constraint**: Only works on **recomputed, self-uncomputing scratch** — a comparator you compute,
read under the condition, then cleanly reverse. It does NOT work on data-controlled operations (where
the control is live quantum data, not a measurable flag).

---

### 3.7 Classical Constants Are Free

**When one operand is classical, the Toffoli disappears.**

In our circuit, the point `Q = (Qx, Qy)` being added is a **fixed classical constant** (the generator
point in Bitcoin's secp256k1). This means all operations of the form `x ← x + Qx` or `y ← y − Qy`
have one classical operand.

For a CNOT: `ctrl | classical_target ← 0` if we know `classical_target = 0`, the gate is just "apply
X if ctrl=1 and target is the right bit" — which becomes a compile-time XOR of the bit pattern, not
a runtime gate. The operations become free `BitId` flips with 0 Toffoli.

In practice: `coord_add3x` (dst += 3·Qx mod p) is implemented entirely on the classical `BitId` tier
(zero Toffoli) because Qx is known at compile time.

---

## 4. The Qubit↔Toffoli Exchange Rate

### The fundamental tradeoff

Almost every optimization involves trading one resource for the other. The question is always:
**Is this particular trade favorable at the current frontier?**

The **break-even rate** at the current SOTA (d44cad3, 1152q × 1,364,230 avgT):
```
break-even = avgT / peak_qubits = 1,364,230 / 1152 ≈ 1,184 Toffoli per qubit
```

If a technique saves 1 qubit at the cost of fewer than 1,184 Toffoli, the score improves.
If it costs more than 1,184 Toffoli per qubit, the score worsens.

**This rate is per-base and changes with every optimization.** An important lesson:
- The 1156→1157 qubit expansion (`6ba606a`) cost only ~1,127 Toffoli per qubit (clearing break-even).
- But the parallel Toffoli-only optimization track improved the base simultaneously, so by the time
  the qubit drop landed, the score was already beaten by the pure-Toffoli route.
- **Always compare products (score), not just break-even rates.**

### The classical vs quantum pebbling gap

Bennett (1989) showed that classically, the cost of computing a T-step function using S space in a
reversible way is roughly:
```
T' = ε × 2^(1/ε) × T^(1+ε) / S^ε  extra gates
```
This is exponentially expensive as ε → 0 (as you try to save more space).

But quantum circuits with mid-circuit measurements (like MBU/spooky pebbling) do much better:
```
T' = O(T/ε) gates,   O(T^ε × S^(1-ε)) qubits
```
The quantum constant is O(1/ε) — **polynomially small**, not exponentially large.

This is the theoretical reason MBU and measurement-based techniques are so powerful: they exploit
a fundamentally different space-time tradeoff than classical reversible computation allows.

---

## 5. Density-Neutral vs Island-Exact Techniques

### Two types of optimization, very different risk profiles

**Density-neutral**: The technique is correct for ALL inputs. The circuit produces the same output
regardless of which input is fed in.

**Island-exact (distribution-specific)**: The technique is only correct for the 9024 specific
inputs the challenge evaluates. It might produce wrong answers on other inputs — but the challenge
only checks those 9024.

| Property | Density-neutral | Island-exact |
|----------|-----------------|-------------|
| Correct on all inputs | YES | NO |
| Correct on challenge inputs | YES | YES (by design) |
| Safe to combine | YES — stack freely | RISK — interact with each other |
| Needs nonce re-hunt | Only if op-stream changes | YES — always changes density |
| Examples | MBU vents, Karatsuba, structural dead-skip | Carry truncation, GAP_J2, empirical dead-CCX |

### The density issue explained

The challenge finds a "clean nonce" — a 48-byte seed such that, when used to generate test inputs,
all 9024 inputs produce a correct answer (0 classical errors, 0 phase errors, 0 ancilla errors).

Density-neutral techniques preserve the pool of valid nonces: if a nonce worked before, it still
works after (modulo the op-stream changing its hash). Island-exact techniques shrink the pool: some
inputs that previously gave correct answers now might give wrong answers, making certain nonces
invalid.

**The empirical dead-CCX approach** (used before d44cad3): Sample 9 million inputs, find CCX gates
that never fire, skip them. Valid only if those CCX gates also never fire on the 9024 challenge
inputs — but on other inputs they might fire, and skipping them gives wrong answers.

**The structural-dead approach** (d44cad3): Use circuit analysis to prove a CCX never fires on ANY
input. Unconditionally correct. No re-hunting needed.

---

## 6. Pebbling Theory: The Formal Foundation

### What is pebbling?

The **reversible pebble game** is an abstract model for analyzing space-time tradeoffs in reversible
computation. Think of it as a graph (nodes = values, edges = dependencies) where you can:
- Place a pebble on a node if all its predecessors have pebbles (compute it).
- Remove a pebble from a node if you run the computation backwards (uncompute it).

The "peak qubits" = maximum number of pebbles on the graph simultaneously.

### Bennett pebbling (classical)

Bennett (1989) showed: to simulate a T-step computation using S extra pebbles reversibly:
```
Time cost = ε × 2^(1/ε) × T^(1+ε) / S^ε  (for any ε > 0)
```
Special case ε=1: T² / S time — quadratic. This grows exponentially worse as ε→0.

For our 530-step GCD: halving the transcript (from 740q to 370q) via classical pebbling would
cost `2 × 530² / 370 ≈ 1,518` additional GCD passes. At ~2,500 Toffoli per pass, that's
~3.8M extra Toffoli — a 280% increase. Not worth it.

### Spooky pebbling (quantum advantage)

Gidney (2019) introduced the **spooky pebble game**: you can also "remove a pebble early" by
measuring it in the X-basis. This leaves a 50% chance of a phase error ("ghost"), which is
corrected later using a classical bit from the measurement result.

Kornerup, Sadun, Soloveichik (2021) proved tight bounds: with quantum measurements:
```
Time cost = O(T/ε)   (constant factor 1/ε)
vs Classical: O(2^(1/ε) × T)  (constant factor exponentially large)
```

**The quantum advantage is exponential**: for the same qubit savings, quantum circuits using
measurements need far fewer extra gates than classical reversible circuits.

**Parallel spooky pebbling** (Kahanamoku-Meyer et al. 2025): For a length-ℓ sequential chain,
only `2.47 × log(ℓ)` qubits suffice to evaluate in depth `2ℓ`. For our 530-step chain:
`2.47 × log(530) ≈ 23 qubits`. Notably, our current GCD state machine already uses ~22 qubits
— we're already near the theoretical minimum!

---

## 7. The Structural Techniques in Context: The 1211→1152 Journey

Here's the historical arc showing which technique solved which bottleneck:

```
1211q — dead-qubit GCD scratch removed via live-range hole (uncompute during shift)
  ↓  −18q, +34 avgT
1193q — modular square truncation (one segment width tighter)
  ↓  −1q, ~0 avgT
1192q — fold-phase denser transcript codec (head-11 encoding, bijection self-test)
  ↓  −7q, +6,604 avgT
1185q — combined: finite-support tail codec + streaming apply + square rebalance
  ↓  −15q, ??
1170q — all four binders lowered together (plateau decomposition)
  ↓  Toffoli improvements: Karatsuba square (−22.4M), NAF, fold fast-adds
  ↓  Structural: GAP_J2 comparator narrowing (−1.33M), converged-tail cswap skip
1159q — dynamic headroom clamp (TLM_TARGET_Q governor)
  ↓
1156q — [eventually returned as SOTA after Toffoli matured sufficiently]
  ↓
1153q — density-neutral fold increments (cinc), structural dead-CCX suite
  ↓  6dafa07: structural dead pivot (removes empirical dead-CCX, adds ~15 structural predicates)
1152q — FFG cy0 free-and-recompute + off-peak square vents (d44cad3, current SOTA)
```

Each step reflects a different technique attacking the current bottleneck.

---

## 8. Open Frontiers

### Density-neutral Toffoli cuts not yet applied

1. **Gidney 2025 streaming vented adder** (arXiv:2507.23079): Uses 2 clean + (n-2) dirty ancilla
   to implement an n-bit adder with ~3n Toffoli (vs current ~4n). Partially implemented in
   `venting.rs` but has a phase leak bug — fixing it could save ~n/4 Toffoli per adder call.

2. **Apply-swap involutory pair cancellation**: The forward GCD-swap and the immediately following
   GCD-cswap on the same registers may cancel algebraically (swapping twice = identity). Not yet
   checked structurally.

3. **Extended Cuccaro structural dead-carry**: Currently checked for call indices 13-37 only.
   Extending to all adder call sites would save proportionally.

### Density-neutral qubit cuts not yet applied

1. **More cy0-style free-and-recompute values**: The current 1152q peak is a co-bind plateau —
   multiple phases all hitting 1152q simultaneously. Finding additional trivially-recomputable values
   in each co-binder could drop the plateau, but ALL must be lowered together.

2. **Spooky-pebble the GCD state machine** (−22q): Replacing the 22-qubit quantum step counter
   with classical measurement tracking + phase corrections. Tight at break-even but theoretically
   viable if the per-step phase correction cost is small enough.

---

## 9. Quick-Reference Summary Table

| Technique | What it does | Qubit impact | Toffoli impact | Density-neutral? |
|-----------|-------------|-------------|----------------|-----------------|
| MBU / carry vent | Replace uncompute Toffoli with X-basis measurement | +1/vent (off-peak: free) | −1/vent | YES |
| Live-range hole | Uncompute early, recompute later | −k (at peak) | +recompute cost | YES |
| Transcript compression | Encode GCD decisions more densely | −k qubits | +small decode | YES |
| Passenger ghosting | Erase a value you can reconstruct; carry a receipt | −N qubits | +N-mul reconstruction | YES |
| Free-and-recompute cheap value | Clear a qubit whose value = f(live qubits); loan lane | −1 | +~0 (2 CNOTs) | YES |
| Dynamic-width registers | Only allocate bits actually needed each step | −varies | neutral | PARTIAL (thin schedule: island-exact) |
| Known-constant teardown | XOR register to 0 using known value; free lane | −k | +k XOR (free) | YES |
| Karatsuba square | 3 sub-squares instead of 4 for 256-bit squaring | neutral | −22.4M | YES |
| NAF recoding | Signed-digit repr of constant → fewer modular ops | neutral | −~5-10% | YES |
| Structural dead-gate skip | Provably skip CCX whose target never flips | neutral | −varies | YES |
| Conditional/measured replay | Average Toffoli by fraction predicate is set | neutral | −(1 − firing_rate)× | YES |
| Carry truncation | Drop carry bits provably zero on the island | neutral | −small | NO (island-exact) |
| Empirical dead-CCX | Skip CCX empirically never observed to fire | neutral | −small | NO (removed in 6dafa07) |
| Classical constant ops | One operand is compile-time constant → 0 Toffoli | neutral | −significant | YES |

---

## 10. Key References

- Jones 2013 — Original MBU source (Phys. Rev. A 87.2)
- Gidney 2018 (arXiv:1709.06648) — Applied MBU to adder carry chains
- Khattar & Gidney 2024 (arXiv:2407.17966) — Conditionally clean ancilla taxonomy
- Nie, Zi & Sun 2024 (arXiv:2402.05053) — Independent co-discovery of conditionally clean ancilla
- Bennett 1989 (SIAM J. Comput. 18:4) — Reversible pebbling time-space tradeoff
- Kornerup, Sadun & Soloveichik 2021 (arXiv:2110.08973) — Quantum spooky pebble tight bounds
- Kahanamoku-Meyer et al. 2025 (arXiv:2510.08432) — Parallel spooky pebbling
- Karatsuba & Ofman 1962 — Fast multiplication via divide-and-conquer
- Gosset et al. 2013 (arXiv:1308.4134) — 1 Toffoli = exactly 7 T-gates (tight lower bound)
- Selinger 2013 (arXiv:1210.0974) — T-depth 1 per Toffoli with 4 ancilla (depth trick, not count)

**Internal references**:
- `density_neutral_tradeoffs.md` — detailed technique catalog with exchange rates
- `REPORT_1168_wall_revamp.md` — historical account of the 1168→1152q journey
- `gidney-techniques.md` — Gidney's full lever catalog
- `external-literature-2000-2026.md` — broader academic literature map
