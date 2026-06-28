# Qubit & Toffoli Reduction Techniques: A Comprehensive Primer

*ecdsa.fail quantum circuit benchmark*

**Contributors:** The optimization techniques described here were collectively contributed by **all
participants and leaderboard contributors of the [ecdsa.fail](https://ecdsa.fail) challenge**.
Summarized and compiled by **Jieyi Long**, with Claude Code.

> **Audience**: This primer is written for undergraduate students who have just learned the basics of
> quantum computing — superposition, entanglement, Toffoli/CNOT/Hadamard gates, quantum circuits, and
> reversible computation. It explains every optimization technique used in the ecdsa.fail quantum
> circuit challenge from circuit-level first principles, with concrete examples from the actual
> research.

---

## Table of Contents

1. [Introduction: What Is the ecdsa.fail Challenge?](#1-introduction-what-is-the-ecdsafail-challenge)
2. [What We Are Optimizing — The Score and Why Toffoli Gates Are Expensive](#2-what-we-are-optimizing--the-score-and-why-toffoli-gates-are-expensive)
3. [The Reversibility Constraint — Why Quantum Circuits Are Hard to Optimize](#3-the-reversibility-constraint--why-quantum-circuits-are-hard-to-optimize)
4. [The Challenge Circuit — Elliptic Curve Point Addition](#4-the-challenge-circuit--elliptic-curve-point-addition)
5. [Measuring Progress — The Peak Qubit Profile and Hot Spots](#5-measuring-progress--the-peak-qubit-profile-and-hot-spots)
6. [Qubit Reduction: The Core Loop](#6-qubit-reduction-the-core-loop)
7. [Qubit Reduction Techniques (1–19)](#7-qubit-reduction-techniques-119)
8. [Toffoli Reduction: The Core Loop](#8-toffoli-reduction-the-core-loop)
9. [Toffoli Reduction Techniques (1–19)](#9-toffoli-reduction-techniques-119)
10. [The Qubit ↔ Toffoli Exchange Rate and the Product Race](#10-the-qubit-↔-toffoli-exchange-rate-and-the-product-race)
11. [Density-Neutral vs Island-Exact — Correctness Regimes](#11-density-neutral-vs-island-exact--correctness-regimes)
12. [Pebbling Theory — The Formal Foundation](#12-pebbling-theory--the-formal-foundation)
13. [The SOTA Circuit: How trailmix_ludicrous Works](#13-the-sota-circuit-how-trailmix_ludicrous-works)
14. [The Three Tracks: Score, Low-Qubit, and Pareto Frontier](#14-the-three-tracks-score-low-qubit-and-pareto-frontier)
15. [Open Frontiers](#15-open-frontiers)
16. [Quick-Reference Summary Tables](#16-quick-reference-summary-tables)

---

## 1. Introduction: What Is the ecdsa.fail Challenge?

Elliptic-curve cryptography (ECC) secures essentially all of today's digital signatures — including
the keys that control Bitcoin and Ethereum funds. A large enough quantum computer would break it:
**Shor's algorithm** can recover a private key from a public key by solving the elliptic-curve
discrete logarithm problem in time polynomial in the key size. The overwhelming majority of that
quantum computation is spent running **one tiny primitive over and over** — *elliptic-curve point
addition* on the curve `secp256k1` (Bitcoin's curve). Make that inner circuit cheaper and the entire
attack gets cheaper. [**ecdsa.fail**](https://github.com/ecdsafail/ecdsafail-challenge) is an open,
collaborative competition to build the **leanest possible reversible quantum circuit for that single
point addition** — a public, reproducible race to map exactly how expensive (or cheap) breaking ECC
really is.

A submission is a circuit that computes one in-place affine point addition `P += Q` on secp256k1,
and it is scored by its **spacetime cost: `peak_qubits × average_executed_Toffoli`** (lower is
better) — the two resources that dominate cost on a fault-tolerant quantum computer (§2). Every
submission must be *exactly correct and physically valid*: it is checked against 9,024 random test
cases for classical-value correctness, for reversibility (all scratch qubits returned to `|0⟩`), and
for phase cleanliness, and contributors may only edit the point-addition circuit itself — the
evaluation harness, validator, and toolchain are locked. The headline goalpost is **Google Quantum
AI's published resource estimate** for the same task (≈1,425 qubits × ≈2.1M Toffoli ≈ 2.99 × 10⁹
qubit-Toffoli, March 2026). The challenge's starting baseline scored ~1.07 × 10¹⁰; as of late June
2026 the community-driven state of the art sits near **1,152 qubits × ~1.36M Toffoli ≈ 1.57 × 10⁹**
— roughly **47% below** Google's number, with the bar still dropping.

What makes the effort unusual is *how* the records are won. Participants — ranging from academic
researchers to programmers with no quantum-computing background — increasingly drive the work with
**AI agent pipelines**: the circuit harness is fed directly into large-language-model loops that
propose, test, and validate optimizations around the clock, preserving their findings as versioned
research notes. The result is a fast-moving catalogue of genuinely clever, circuit-level tricks for
shaving qubits and Toffoli gates. **This primer is a guided tour of those techniques**, explained
from quantum-circuit first principles for a reader who has just learned the basics — covering all
three of the challenge's objectives (minimize the spacetime product, minimize qubits alone, and map
the clean (qubit, Toffoli) Pareto frontier; see §2).

---

## 2. What We Are Optimizing — The Score and Why Toffoli Gates Are Expensive

### The score

```
score = peak_qubits × avg_executed_Toffoli
```

Lower score is better. This is the ecdsa.fail benchmark's cost function for a quantum circuit
that computes an affine elliptic-curve point addition on secp256k1 (Bitcoin's curve). The two
factors penalize two different resources:

- **Peak qubits**: the maximum number of qubits simultaneously in use at any instant. This is
  the "width" of the circuit, not the total number ever allocated. On real hardware, idle qubits
  still occupy physical space on the quantum processor.

- **Average executed Toffoli**: the Toffoli (CCX) gate count, *weighted by how often each gate
  fires*, averaged over the 9024 test inputs the challenge uses. Not just the count of gates in
  the circuit, but gates × firing_rate.

### Why Toffoli gates specifically?

On a **fault-tolerant** quantum computer (the kind needed to break Bitcoin-scale cryptography),
gates fall into two classes:

- **Clifford gates** (CNOT, Hadamard H, Phase S, Pauli X/Y/Z): these can be implemented
  efficiently using the surface error-correcting code at very low physical-qubit overhead.
- **Non-Clifford gates** (Toffoli / T-gate): these require **magic states** — specially prepared
  ancilla qubits that take a long time and many physical qubits to distill via "magic state
  distillation." Each Toffoli gate consumes one distilled magic state.

The rough conversion: 1 Toffoli = exactly 7 T-gates (Gosset et al. 2013, tight lower bound).

So in this regime, **Toffoli gates are like currency**: each one costs approximately the same
fixed price (one magic state), regardless of context. The peak qubit count is like "desk space"
— idle qubits still occupy factory floor. The product `peak_qubits × Toffoli` captures the
spacetime volume of running the circuit.

> **Common confusion**: This challenge uses `avg_executed_Toffoli`, NOT:
> - T-count (= 7× Toffoli, a different metric)
> - T-depth (Selinger 2013 — a depth trick with 4 ancilla per Toffoli; irrelevant here)
> The distinction matters: average-executed rewards conditional execution (replay), emitted
> T-count does not.

### The current SOTA

The best known result as of 2026-06-27 (BitWonka, commit `d44cad3`, trailmix_ludicrous family):
```
1152 qubits × 1,364,230 avg Toffoli = 1,571,592,960 score
```

### Three objectives, not one

This is important context for the whole document. The ecdsa.fail challenge is really **three
optimization tracks**, and a technique that is optimal for one can be irrelevant — or even
counterproductive — for another:

1. **Minimize the spacetime volume (the Q×T score competition)** — the main subject of this primer.
   Minimize the *product* `peak_qubits × avg_executed_Toffoli`. Both resources matter, and every
   move is judged by the exchange rate (§10). The SOTA above (1152q × 1.36M) lives in this track.

2. **Minimize qubits regardless of Toffoli (the low-qubit competition)** — a question of academic
   curiosity: *how few qubits can a correct point-add possibly use?* Toffoli count is
   *unconstrained* — you may spend as many gates as you like. This track maps the qubit **floor**;
   the deepest technique here is EEA register sharing (§7.15), which reaches 851q → 829q (far below
   anything score-competitive). Under this objective, spending 8× more Toffoli to save 10% of qubits
   is *free*, because Toffoli never enters the scoring.

3. **Explore the (Q, T) Pareto frontier** — especially the *useful corner* where **both** Q and T
   are lower than the published resource estimates for a **single secp256k1 point addition**:
   **≤1175 qubits / ~2.69M Toffoli** (= 2²¹·³⁶), the Babbush et al. (Google Quantum AI)
   space-optimized figure tabulated in Schrottenloher 2026 (arXiv:2606.02235, Table 1; original
   arXiv:2603.28846). *(Watch the units: the often-quoted ≤1200q / ≤90M Toffoli is the **full**
   ECDLP/Shor run — ~28 windowed point additions plus overhead — whereas the scored circuit here is
   **one** point addition, so the per-point-addition figure is the correct reference.)* A point is
   Pareto-optimal if you cannot lower one of Q or T without raising the other. The goal here is not a
   single score but a *clean, forkable basis curve* at each qubit count (see the 1153q→1133q Pareto
   bases, §14.3). To stay reusable, these circuits **deliberately disable the most overfit lever —
   dead-CCX deletion** (§11), whose hard-coded gate-index lists are tied to one exact op stream. They
   are *not* fully value-exact, though: they still use the route's calibrated **approximations**
   (comparator-width narrowing, carry truncation, and at the lowest rungs active-width trimming — all
   island-exact, §11), so each still needs its own nonce hunt. The point is a *cleaner, more forkable*
   reference than a dead-CCX-stacked SOTA — not an all-inputs-provable one.

These are genuinely different games. Most of this primer optimizes track 1, but several techniques
(register sharing, the clean Pareto bases) only make sense under tracks 2 and 3. Keep the three
objectives separate in your head: many "is this worth it?" questions only have an answer once you
know *which* track you are on.

---

## 3. The Reversibility Constraint — Why Quantum Circuits Are Hard to Optimize

### You cannot delete information

Quantum circuits must be reversible. This is not a convention — it is required by quantum
mechanics. Every gate in a quantum circuit must have an inverse (you can always "run it
backwards"). This means:

- **You cannot overwrite a qubit.** If qubit A holds value `x` and you want to compute
  `f(x)` into A, you cannot just replace it. You'd lose `x` forever, which breaks reversibility.
- **You cannot erase a qubit.** If a qubit is entangled with the rest of the system (as
  intermediate results in a quantum computation always are), setting it to `|0⟩` forcibly
  would violate unitarity.

The only way to "free" a qubit is to **uncompute** it — run the computation that created its
value in reverse, returning it exactly to `|0⟩`. Once it's `|0⟩`, it can be freed from the
live set.

### Consequence: intermediate values cost qubits until uncomputed

Every time your circuit computes an intermediate result (a carry bit, a partial product, a
comparison flag), it must allocate a fresh qubit. That qubit remains **live** — occupying a
slot in the peak count — from the moment it's computed until the moment it's uncomputed.

**Example**: An n-bit addition `a + b` computes n carry bits, one per bit position. Each
carry qubit is live from when it's computed until the carry chain is reversed. If you compute
the addition at step 100 and uncompute it at step 200, those n carry qubits are live across
the entire steps 100–200, contributing to the peak at any instant in that range.

This is why almost every qubit-reduction technique boils down to: **make intermediate values
die sooner** (so they aren't live at the peak) **or don't materialize them at all**.

### Reversibility also doubles Toffoli counts

In a classical circuit, you compute X, use X, then discard X. In a reversible circuit, you
compute X (costs Toffoli), use X, then *uncompute* X (costs the same Toffoli again). So every
logical AND operation normally costs 2× — once forward, once backward.

This is the central pain point that Measurement-Based Uncomputation (§9.1) solves.

---

## 4. The Challenge Circuit — Elliptic Curve Point Addition

### What it computes

The circuit computes one **affine elliptic curve point addition**: given quantum register
`P = (Px, Py)` and classical constant `Q = (Qx, Qy)`, compute `P + Q = R` in place, where
the arithmetic is modulo the secp256k1 prime `p = 2^256 − 2^32 − 977`.

The mathematical operations, in order:
```
dx = Px − Qx              (mod p subtraction)
dy = Py − Qy
λ = dy / dx               (modular inverse + multiply: the expensive GCD-based step)
new_Px = λ² − Px − Qx    (modular square + subtracts)
new_Py = λ(Px − new_Px) − Py
```

### Why modular inverse is the bottleneck

Computing `dy/dx mod p` requires computing `dx⁻¹ mod p`, the modular inverse of `dx`. There
is no simple formula — it requires running the **Extended Euclidean Algorithm (EEA)** or
equivalent, which takes ~530 steps of binary GCD (divstep) operations. Each step involves:
- A comparison (swap decision: is |u| > |v|?)
- A conditional swap of two 256-bit registers
- A conditional subtraction of two 256-bit registers

This accounts for roughly 90% of the circuit's Toffoli count.

### How an in-place modular inverse actually works: the dialog transcript

A classical EEA tracks two "Bézout coefficient" registers alongside the operands to build the
inverse. Doing that reversibly would carry several extra 256-bit registers through all ~530 steps —
very expensive in qubits. The trick that makes the circuit affordable (Schrottenloher Algs 2–4,
descended from the Khattar–Gidney "Dialog") is to **split the algorithm into a cheap construction
pass and a cheap reconstruction pass that share a small recorded tape**:

- **Pass 1 — GCD construction (records the tape).** Drive the binary-GCD pair `(u, v)` from
  `(p, dx)` toward `(1, 0)`. At each step, the only data-dependent information is the small
  **decision symbol** `(subtracted?, swapped?, shift)` — a few bits. Record those bits onto a
  **transcript tape** and throw away nothing else. This pass uses *non-modular* arithmetic and has
  ~n free ancilla, so it is cheap. It *consumes* `dx` into the tape.
- **Pass 2 — Bézout reconstruction (replays the tape).** Read the tape **in reverse**, maintaining
  one *modular* pair `(r, s)` and applying, at each step, only linear updates **controlled solely by
  the recorded bits**: `s = 2s mod p; if subtracted: s += r; if swapped: swap(r, s)`. No
  comparisons, no operand-dependent branching — just replay.

**The elegant part (why no explicit inverse is ever built).** Because the replay updates are
*linear*, the seed you feed into pass 2 comes straight out. Seeding `(r, s) = (1, 0)` reconstructs
`dx⁻¹`. But seeding `(r, s) = (y, 0)` instead yields `(0, y · dx⁻¹ mod p)` **directly** — the
inversion *and* the multiply-by-`y` happen together, with the inverse never materialized as its own
register. And reading the tape **forward vs reversed flips between `y·dx` and `y·dx⁻¹`** — the same
machinery does a modular multiply or a modular divide just by replay direction. This is exactly how
the SOTA does both EC slope steps (`λ = dy·dx⁻¹` and later `λ·(…)`) with **one inversion engine and
one tape** (§13).

**Where the peak lives — and the one knob that sets the Pareto split.** The qubit peak is *not*
during construction (operands shrink, freeing room for the tape); it is during **reconstruction**,
where the compressed transcript (~2.355n) and the two n-bit modular registers `r, s` co-reside:

```
peak ≈ compressed_transcript + 2 modular registers + O(√n) ≈ 4.355n
```

So *both* score factors are set by the reconstruction step — that is where every later technique
(transcript compression §7.8, vented adders §9.1) is aimed. And there is a single clean knob behind
the whole (Q, T) Pareto curve: spending **n extra ancilla during reconstruction** lets you use a
cheap Gidney adder (2n Toffoli) instead of a CDKM adder (3n) — that one choice *is* the
space-optimized-vs-gate-optimized split in both Babbush and Schrottenloher.

**Jump-GCD (fewer steps).** A plain binary GCD does one reduction per trailing-zero bit. A
**jump (Stein-style) divstep** strips up to `jump=2` trailing zeros at once, so the algorithm
finishes in fewer steps — directly fewer adder/comparator firings, hence fewer Toffoli. The cost is
a slightly larger symbol alphabet to record (5 symbols instead of 3), which the codec absorbs. The
SOTA runs `jump=2` (258 steps).

### The key design choice: Q is classical

The second point `Q` is a **fixed constant** (the secp256k1 generator point, known at circuit
compile time). The current SOTA keeps `Q` as classical bit-patterns (`BitId`s) rather than
quantum registers, eliminating 512 qubits from the peak — the single largest qubit reduction
in the circuit's history.

### Why secp256k1's prime is cheap: pseudo-Mersenne reduction (the math background)

Every arithmetic step works **modulo** `p = 2^256 − 2^32 − 977`. Doing `mod p` naively means
dividing by a 256-bit number — a full multiprecision division, expensive in any circuit. The whole
reason this challenge is even approachable is that `p` is a **pseudo-Mersenne (Solinas) prime**:
it sits just below a power of two. Write

```
p = 2^256 − c,   where   c = 2^32 + 977   (only 33 bits wide)
```

**A quick word on the names** (they describe a family of "reduction-friendly" primes):
- **Mersenne prime** — `p = 2^k − 1`. Reduction mod a Mersenne prime is *trivial*: `2^k ≡ 1`, so you
  just fold the high bits straight onto the low bits with one add. (These are too rare to land on a
  secure 256-bit curve, but they're the ideal everything else approximates.)
- **Pseudo-Mersenne prime** — `p = 2^k − c` with `c` *small* (here 33 bits). Now `2^k ≡ c`, so the
  fold is "high bits **× c**, then add." The word *pseudo-Mersenne* emphasizes that **`c` is small**,
  which is what keeps the `H·c` multiply cheap.
- **Solinas prime** (a.k.a. *generalized Mersenne*, Jerome Solinas, 1999) — `c` is not just small but
  a **sparse signed sum of a few powers of two**. For secp256k1, `c = 2^32 + 977 = 2^32 + 2^10 − 2^5
  − 2^4 + 1` (see NAF, §9.7) — only ~5 signed terms. The word *Solinas* emphasizes that **`c` is
  sparse**, so the `H·c` "multiply" is really just a handful of *shifted adds/subtracts*, not a
  general multiplication.

secp256k1's prime is **both at once**, and the two properties cut different costs: being
pseudo-Mersenne (small `c`) means *one* fold suffices; being Solinas (sparse `c`) means that fold is
a few shift-and-adds. Throughout this primer "the Solinas fold" and "pseudo-Mersenne reduction" refer
to the same operation — folding the top bits down by `+c` — and "Solinas constant" / "the fold
constant" both mean `c` (called `f` in the code).

The one identity that everything rests on:

```
2^256 ≡ c   (mod p)
```

(because `2^256 − c = p ≡ 0`). In words: **anything that lands at bit position 256 or higher is
congruent, mod p, to the same thing multiplied by the tiny constant `c` and dropped back into the
low bits.** So to reduce a wide value `H·2^256 + L` (a high part `H` above bit 256, a low part `L`
below it):

```
H·2^256 + L  ≡  L + H·c   (mod p)
```

You never divide by `p`. You **"fold" the overflow `H` back down** by multiplying it by the 33-bit
`c` and adding — a couple of short operations instead of a full division. This single fact is the
source of the entire secp256k1-vs-generic-prime cost gap: in Schrottenloher's accounting the
constant-adder is **15% of all Toffoli for secp256k1 but 34% for a generic prime**, and modular
doubling **8% vs 24%** (paper Table 3; secp space-opt 2²¹·¹⁹ vs generic 2²¹·⁷⁸).

The intuition to carry forward: a modular reduction is normally "subtract `p` until you're back in
range," but for a pseudo-Mersenne prime it becomes **"fold the top bits into the bottom bits,"**
and the fold is cheap precisely because `c` is small. §9.18 turns this identity into the actual
reversible-circuit gadgets (mod-double, mod-add, the `+f` fold), and §9.7 (NAF) makes the fold
constant itself cheaper.

---

## 5. Measuring Progress — The Peak Qubit Profile and Hot Spots

### The live-qubit-vs-time profile

To reduce the peak, you first need to know **where** the peak occurs. Plot how many qubits
are live at each moment in the circuit timeline:

```
qubits  |
live    |         ████████████
        |    ████████████████████
        |  █████████████████████████
        |████████████████████████████████
        +--+----+--+------+--+----+--+----> time
                    ^
                    peak = 1152 here (the "binder")
```

The highest point is the **peak**, and the phase executing at that height is the **binder**.
Only operations alive at the binder instant matter for qubit reduction. Optimizing anything
else changes nothing about the peak.

**Key tool**: `TRACE_PEAK=1 TRACE_PHASE_ACTIVE=1` in the build flags. This instruments every
`alloc_qubit` / `free_qubit` call and prints the name of the phase executing when the maximum
is hit.

### The plateau problem

After shaving the single tallest binder, you often discover the peak hasn't moved — because
several *independent* phases all reach the same height. This is a **co-binder plateau**:

```
qubits  |
live    |    █████   █████     ████
        |  █████████████████████████
        |  █████████████████████████    ← plateau at 1152 (Phase A, B, C all tie here)
        +----+--+----+---+--+---+-----> time
```

The reported peak doesn't drop until **every** plateau member is individually pushed below the
current height. This changes the strategy fundamentally: you must work in "plateau mode" —
find a local qubit reduction for each co-binder, then combine them.

### Emitted vs average-executed Toffoli

**Emitted**: the raw count of CCX gates in the circuit, regardless of whether they fire.

**Average-executed**: each CCX gate's contribution weighted by `Pr[control fires]`, averaged
over all 9024 test inputs. A CCX gate that only fires 5% of the time contributes only 0.05.

This distinction is critical because **conditional replay** (§9.3) can dramatically reduce
average-executed without changing emitted at all.

---

## 6. Qubit Reduction: The Core Loop

Before diving into individual techniques, understand the general loop:

1. **Measure** — get the live-qubit-vs-time trace; find the peak height and the binder phase.
2. **Inventory** — list every qubit alive at the binder instant.
3. **Classify** — label each qubit by category (below).
4. **Brainstorm** — for each non-essential qubit at the binder, propose a shave.
5. **Cost** — compute how many Toffoli gates the proposed shave adds vs how many qubits it
   saves. Compare to the break-even exchange rate (§10).
6. **Re-measure** — apply the cheapest safe shave. The peak moves to a new binder. Repeat.

### Qubit classification at the binder

| Class | What it holds | Shrinkable? |
|-------|---------------|-------------|
| **Essential data** | Inputs/outputs the binder reads or writes | Rarely |
| **Scratch** | Temporary arithmetic results (carries, partial products) | Often |
| **Transcript / log** | GCD branch decisions recorded for reversibility | Often — compress the log |
| **Passenger** | Allocated before the peak, consumed after, *idle at binder* | Yes — relocate its endpoints |
| **Alias-candidate** | Restorable duplicate of a value already live elsewhere | Yes — borrow as dirty scratch |
| **Truncatable** | Bits provably zero or provably irrelevant to the final output | Yes |

### Binary vs graded failure modes

A critical distinction before applying any technique:

- **Graded-failure levers** (carry truncation, comparator narrowing): Correctness degrades
  *continuously* with aggressiveness. A small fraction of inputs go wrong. You can iterate
  on the parameter and search for a nonce where all 9024 test inputs avoid the failures.

- **Binary-failure levers** (register live-range holes, transcript compression, structural
  reuse): Correctness is all-or-nothing. Either the circuit is value-exact on all inputs, or
  it's wrong on essentially all inputs. There is no graded near-miss ladder to climb. You must
  get the implementation mathematically correct before searching for nonces.

**The trap**: applying the "tweak-and-triage" loop to a binary-failure lever. A structural
width cut that's not value-exact will produce all-dirty garbage on every input, not near-misses.

---

## 7. Qubit Reduction Techniques (1–19)

### 7.1 Live-Range Holes: Uncompute Early, Recompute Later

**The headline move.** If a qubit holds a value V that the peak instant does NOT need (it
was computed before the peak and will be consumed after), free it before the peak and rebuild
it after.

```
Timeline view:
Before:  ···[V computed]=====[V held live across peak]=====[V consumed]···
After:   ···[V computed][uncompute V]   (peak happens)   [recompute V][V consumed]···
                                         ^^^^^^^^^^^
                                   V is absent at peak
```

**Mechanics**: Emit the reverse of the gates that built V (returning its qubits to `|0⟩` and
freeing them), run the peak-owning phase with that freed headroom, then re-emit the forward
gates to restore V for its later consumer.

**Cost**: The recompute adds Toffoli (same cost as the original computation). For a value
that cost C₀ Toffoli to compute:
- You save k qubits at the peak
- You spend 2C₀ extra Toffoli (one uncompute + one recompute)
- The trade wins if `2C₀ < k × (avgT / peak_q)` (the break-even rate)

**Real examples**:
- **1211→1193**: A GCD-apply scratch block was uncomputed during a shift sub-phase that didn't
  use it, then reacquired after. Saved 18 qubits.
- **1166→1165** (`TLM_PARK_ODD_U0`): `u[0]` is provably 1 (GCD odd-u invariant). Apply
  `X → |0⟩` to zero it, `loan_zero_qubit` to return the lane, then `restore_known_one`
  (apply X again) to restore. Near-zero Toffoli cost, −1 qubit.

**The keep-alive dual**: Sometimes the uncompute+recompute round-trip creates a wider transient
intermediate than just holding the value. In that case, *keep* the value live across the middle
operation. Choose whichever is narrower: holding footprint vs recompute peak transient.

---

### 7.2 Passenger Relocation: Shorten Live Ranges Without Recomputing

A **passenger** is a qubit that was allocated early and consumed late, but does nothing at the
peak — it just sits idle.

**The cheaper fix**: Don't uncompute and recompute. Just **allocate later** (right before
first use) and **free earlier** (right after last use). If both endpoints fall outside the
peak window, the passenger vanishes from the binder count at zero Toffoli cost.

**Example**: In the PZ inversion track (§7.6), the value `dy` (y-coordinate difference
computed before the inversion) is needed only at the very end. After computing `λ = dy/dx`,
the GCD runs for ~530 steps with `dy` riding along occupying 256 qubits. HMR ghosting (§7.14)
eliminates it from the peak window.

**Check passengers first** before resorting to live-range holes — relocation is free.

---

### 7.3 Range-Bound a Register to Drop a Guard Bit

Some registers need an extra "guard bit" (sign or overflow indicator) only because an
intermediate could transiently go negative or overflow. If you can prove the value always
stays in a non-negative range by reordering operations, delete the guard bit entirely.

**Example** (benhuang Lever B): The fold quotient register had bit 33 (a sign guard) because
Solinas reduction terms `[(0,+),(4,−),(5,−),(10,+),(32,+)]` could make the partial sum
dip below zero. Reorder to apply positives first:
`[(0,+),(10,+),(32,+),(4,−),(5,−)]`. Now the sum is always in `[0, 2^33)`. Allocate 33 bits
instead of 34. **Net: −1 qubit at zero Toffoli cost.** This produced the 1221→1220 drop.

**General rule**: In `+A − B` sequences, applying positives first and subtracting last keeps
partial sums non-negative, eliminating sign-guard bits.

---

### 7.4 Truncation: Keep Only the Bits That Matter

Carry chains, high words of partial sums, and intermediate registers often hold more bits than
actually affect the final result.

**Example**: An n-bit adder computes n+1 bits (including carry-out). If you know the result
is always at most n bits, the carry-out is always 0. Don't allocate it — save 1 qubit at
0 Toffoli cost.

More aggressive: Drop high bits of intermediates if subsequent modular reduction makes those
bits irrelevant. The risk is that dropped bits sometimes aren't 0, silently corrupting results.

**Per-step scheduling**: In a 530-step loop (the GCD), a single constant truncation width must
be set safe for the worst iteration. A per-step schedule `width(step)` lets each iteration be
exactly as tight as it can tolerate — saving qubits only at the steps that are actually at the
peak, without weakening the others.

**Two truncation flavors**:
- Structural truncation (density-neutral): prove from circuit analysis that the dropped bits
  are always zero on all inputs.
- Empirical truncation (island-exact): verify the dropped bits are never 1 on the 9024
  challenge inputs specifically. Requires re-hunting a nonce after each change.

---

### 7.5 Free-and-Recompute a Cheap Value (The 1153→1152 Breakthrough)

When a dead-qubit scan finds **no** unused qubits at the peak, don't conclude "the floor is
structural." Ask instead:

> Is any held value a cheap function of the other values already live at the peak?

If yes, **free** that qubit, let the peak phase use its slot, then **recompute** the value
from the live qubits afterward for negligible cost.

**The cy0 trick** (d44cad3, BitWonka): The qubit `cy0` holds the carry-in at bit 0. No dead
qubits found by scan. But because the secp256k1 prime constant `f[0] = 1`:

```
cy0 = control_bit AND (NOT final_a0)
```

Both `control_bit` and `final_a0` are already live at the peak. So:

1. Uncompute `cy0` using 2 CNOT-equivalent gates (~0 Toffoli)
2. Return the freed lane via `loan_zero_qubit`
3. After the peak phase: recompute `cy0` from `control_bit` and `final_a0` (2 gates)

Applied 40 times (once per binding fold iteration): 40 × 4 CNOTs = 0 Toffoli. Saves 1 qubit.
The 1153→1152 drop.

**Generalized lesson**: After a dead-qubit scan fails, scan again for "whose value is a CHEAP
FUNCTION of other live qubits?" The second question catches what the first misses.

---

### 7.6 Dynamic-Width Registers: Size Registers Per Step

In a GCD algorithm, operands naturally shrink as computation proceeds. After k steps of binary
GCD, the operands `u` and `v` have lost at most k bits from their high ends. A naive circuit
allocates full 256-bit registers for all 530 steps.

**Dynamic-width registers**: At each step `i`, determine the actual live bit-width and only
allocate that many qubits. Free the high bits as they become known-zero.

**Ablation results** (from the Shrunken-PZ q980 track):
```
Source-level dynamic PZ (universal schedule):     1027 qubits
+ thin support-tuned schedule (per-step widths):   990 qubits  (−37q)
+ counter/rotation metadata trimming:              983 qubits  (−7q)
+ quotient cap:                                    980 qubits  (−3q)
```

**Thin schedule (island-exact)**: An even tighter version samples actual GCD widths over many
random inputs and builds per-step bounds tight to that distribution. This is island-exact — the
thin schedule may be too narrow for inputs outside the sampled set. Requires nonce hunting.

---

### 7.7 Known-Constant Teardown Before the Peak

When the GCD terminates, certain registers are in known, predetermined states: `A = 0`, `B = 1`,
`ca = p`, `q = 0`. These are **classical constants** — not quantum information.

**What to do**: XOR the known constant *out of* the register (zeroing it) before the peak
computation, then XOR it *back in* afterward.

**Example**:
- Register `ca` holds `p = 2^256 − 2^32 − 977` at termination.
- Before the lambda multiply: XOR `p` out of `ca`, returning it to `|0⟩`. Free the register.
- Run the lambda multiply with the freed headroom.
- After the lambda multiply: XOR `p` back in for uncomputation.

**Toffoli cost**: XOR (CNOT) operations are Clifford gates — free. The teardown and recreation
cost 0 Toffoli. This is a pure qubit win.

**Why this is allowed**: You're not erasing quantum information. You're applying a known unitary
(XOR-with-p) to a known classical state, which is equivalent to zeroing it. The reverse operation
(XOR-with-p again) restores the value exactly. Reversibility is preserved.

---

### 7.8 Transcript / Log Compression

**The GCD must record its decisions.** At each of the 530 divstep iterations, the algorithm
makes data-dependent decisions: did we swap? did we subtract? These decisions are recorded in
a **transcript** (also called "dialog tape") because they're needed to run the GCD backward
during uncomputation. With one qubit per decision, the raw transcript is ~772 bits long.

**Why transcripts compress**: Not all 2^530 patterns are reachable. The GCD dynamics forbid
certain sequences, leaving fewer bits of entropy.

**Compression techniques**:

**1. Base-5 codec** (trailmix_ludicrous): Each 3-step window of `(subtracted, swap, s₂)` has
8 possible bit patterns, but only 5 are reachable. Encode each 3-step window in
`⌈log₂(5³)⌉ = 7` bits instead of 9 raw bits.
```
Raw:        1 + 3×257 = 772 qubits
Compressed: 1 Step0 (2b) + 85 Triples (7b ea.) + 1 Pair tail (5b) + t1 flag (1b) = 603 qubits
```
The SAT-synthesized reversible codec maps 25 valid 2-symbol pairs to 25 distinct 5-bit codes.

**2. K5 exact 11-bit codec**: Enumerate all reachable 5-step transcript windows exhaustively.
If there are exactly 2^11 = 2048 reachable patterns, encode each in 11 bits. This is
information-theoretically optimal — no further compression possible. Implemented via a
borrowed-ancilla 17-CCX reversible codec. Converts 1203q → 1193q.

**3. Three-step tail codec** (32 symbols): The last few GCD steps are heavily constrained.
Enumerate the exact reachable set (32 symbols), encode in 5 bits. The 1185q → 1170q drop.

**4. Streaming decompression**: Instead of decompressing the entire transcript before use,
decompress one window at a time, use it, then immediately clear that window. Only one window
is "open" at a time, reducing the peak overhead from the codec.

**The hard constraint**: The codec must be a **bijection** — a perfect 1-to-1 map between
reachable patterns and codes. If two distinct transcripts mapped to the same code, the
information needed to run the GCD backward is destroyed, and the circuit gives wrong answers.
Every codec must include a self-test proving bijectivity over the full reachable support.

---

### 7.9 Plateau Decomposition: Lower Every Co-Binder Together

When multiple independent phases all tie at the same peak height, you're in plateau mode.
Lowering one phase alone doesn't change the global peak.

**The protocol**:
1. List ALL phases tied at the current peak (not just the first one). Build a "co-binder ledger."
2. Find a **local** qubit reduction for each binder independently.
3. Verify each local reduction doesn't accidentally raise a neighboring phase.
4. Combine all compatible local reductions in one package.
5. Re-measure the combined package.

**The mental model**: Each local reduction is a **lemma**. The combined package is the
**theorem**. A single lemma that leaves the global peak unchanged is still progress — mark
that binder as "locally lowered" and move to the next.

**Real example — the q1170 plateau** (9-way co-bind, all tied):
| Phase | Local fix | Effect |
|-------|-----------|--------|
| Solinas square | smaller square segment notch | square peak 1170→1169 |
| apply final ripple | low-qubit final ripple variant | ripple 1170→1162 |
| apply double/reverse halve | fold carry parking + per-step map | 1170→1169 |
| special overflow/underflow folds | fold parking + per-step map | 1170→1169 |
| non-final apply ripple | source-as-carry suffix for one lane | 1170→1169 |

Each was independently developed, then combined into a package. Only when all binders were
locally reduced did the global peak drop to 1169.

---

### 7.10 Dynamic Headroom Clamp: A Circuit-Wide Peak Governor

Define a **circuit-wide qubit ceiling** and have every arithmetic primitive clamp its
carry/chunk width to stay under it:

```rust
fn target_qubit_headroom(circ: &Circuit) -> usize {
    TLM_TARGET_Q - circ.active_qubits()
}

fn varchunk_adder(circ: &mut Circuit, bits: usize) -> ... {
    let k = min(scheduled_k, target_qubit_headroom(circ));
    // ... use k as the carry chunk width ...
}
```

**Effect**: No single call can exceed `TLM_TARGET_Q` total qubits. **Lower `TLM_TARGET_Q`
by 1 → peak drops by 1**, as long as the narrower adder is still correct.

This is the structural generalization of a static per-step carry-cap (`TLM_GCD_K_ADJUST`) into
a dynamic per-call clamp. Instead of finding a specific qubit to shave, the runtime governor
finds it automatically on every call.

**The tradeoff**: Tighter ceilings force narrower carries → more carry-chunk splits → more
Toffoli. The break-even exchange rate governs when to tighten.

**Crucial nuance — the clamp is only a *ceiling*, not a lane-freeing lever.** Lowering
`TLM_TARGET_Q` declares an aspiration; it does nothing unless there are *actually freeable lanes*
for the narrower arithmetic to fit into. "A clamp with no freed lanes just panics or fails to fit."
So a clamp drop must be **paired with companion levers that genuinely eliminate live qubits** at the
peak. The **1156 → 1153** drop is the textbook example — it stacked three coordinated levers:

1. **The clamp** itself: `TLM_TARGET_Q` 1156 → 1152 (the binding peak lands at 1153, one above the
   aspiration — the irreducible co-resident set).
2. **Zero-cin fold** (`TLM_FOLD_CHUNK_ZERO_CIN`): the fold-chunk loop's persistent carry-in ancilla
   `cin0` is *no longer allocated at all* — the first chunk's carry-in is provably 0, so a new
   "zero-cin boundary-erase" path (`fold_boundary_erase_zero_direct`) does the carry cleanup without
   it. This is the actual freed lane (a live-range elimination, cf. §7.11). This is what the clamp
   reclaims.
3. **FFG vent-count cap** (`TLM_FFG_MAX_G = 47`): caps the FFG half-product fold's clean-vent count
   `g` so fewer transient vent qubits co-reside at the peak (`capped_g = min(scheduled_g, cap)`).

**And the qubit drop alone is not enough to *win*.** Pushing the peak 1156 → 1153 makes the clamped
adders run on tighter chunks → more carry work → avgT went *up* by +11,369 (to 1,392,603), i.e.
~3,790 Toffoli/qubit, far above break-even. That "clean q1153 base" was **rejected** until Toffoli
levers (the cinc cascade replacement §9.17 + iterated dead-CCX §9.8) were stacked back on top to
carry it over the line. A perfect illustration of the product-race rule (§10): a qubit drop is only
real on the score once enough Toffoli is recovered to pay for it.

---

### 7.11 Lazy Carry Liveness

A specific instance of live-range shortening for carry-in qubits. The carry-in qubit was being
allocated before a chunk loop and held live across all N iterations, even though it was only
needed at the loop boundaries.

Fix (`TLM_FOLD_CHUNK_LAZY_CIN0`):
```
Before: carry_in allocated → live across all N chunk iterations → used only at boundaries
After:  carry_in allocated inside boundary_erase() → used → freed inside boundary_erase()
```

The carry-in qubit's liveness is reduced to just the boundary operation. Peak saved: 1 qubit
per chunk at 0 Toffoli cost.

---

### 7.12 In-Place Decode: Hold Blocks Compressed

For persistent register blocks that live across the peak, encode them compressed and decode
*in place* only at the single use site.

**Before**: Full-width raw K2-pair block (6 lanes) held live across the whole peak.
**After**: 5 compressed cells + one zero lane stored at rest; decode in place only at the use
site (allocate the 6 lanes transiently, use them, re-encode to 5 cells). During the rest of
the circuit, only 5 cells are allocated. This is `DIALOG_GCD_K2_APPLY_INPLACE_RAW_BLOCK=1`,
the 1218→1215 qubit drop.

The principle: any persistent multi-lane block (raw GCD blocks, K2 pairs, materialized
operands) can live compressed and reconstruct transiently at its single use site.

---

### 7.13 Borrowed-Carry Fusion

Standard carry/borrow vectors allocate fresh qubits. But if an adjacent scratch register is
currently known `|0⟩`, borrow its qubits as the carry vector instead:

```rust
borrowed_const_fold_carries(circ, need, borrowed_carries);
// Uses borrowed[..need] as carry vector; no fresh allocation
// At exit: borrowed restored to |0⟩
```

**Net effect**: No fresh qubits allocated for the carry prefix. The peak doesn't rise.

**Hard requirement**: The borrowed qubits must be genuinely `|0⟩` at the borrow point and
restored to `|0⟩` before the borrower reads them again as data. Getting this wrong causes
silent data corruption. (`DIALOG_GCD_SPECIAL_FOLD_BORROW_CARRIES=1`, the `461a4a3` commit.)

---

### 7.14 Passenger Ghosting via HMR (Shrunken-PZ Track)

**Standard passenger relocation**: Free before peak; recompute after. Requires the value to
be recomputable from live data (costs Toffoli).

**HMR ghost** (more aggressive): Measure the passenger qubit in the Hadamard (X-basis). The
qubit is freed. The measurement result (a classical bit `m`) is recorded. Later, reconstruct
the value algebraically and apply a classically-conditioned Z correction to fix the phase.

**Why this works**: An X-basis measurement of `|ψ⟩` projects it into `|+⟩` or `|−⟩`. The
measurement outcome `m` tells you which. If `m = 1` (got `|−⟩`), a phase `(−1)` was applied
to the computational-basis components — the CZ correction cancels this exactly. After the
correction, the measured qubit is factored out from the rest of the system and can be freed
without information loss.

**In the q980 EC point addition**:
- `dy` (256-bit) computed before the GCD inversion. After GCD, `λ` and `dx` are live.
- The identity `dy = λ × dx` holds by construction.
- HMR-ghost `dy` before the GCD peak (measure it, record `m`).
- At the end: reconstruct `dy = λ × dx`, apply phase correction via `m`.
- Freed 256 qubits across the peak at the cost of one modular multiply for reconstruction.

---

### 7.15 EEA Register Sharing — The Low-Qubit Frontier

**The deepest qubit-reduction idea, and the headline technique for the low-qubit competition**
(§2, track 2 — minimize peak qubits, Toffoli unconstrained). This is what drives the lowest qubit
counts ever recorded on the challenge: the 948q → 851q → 829q descent. Because that competition does
not score Toffoli at all, register sharing is free to spend gates lavishly in exchange for lanes —
exactly the trade it makes.

**The naive EEA register budget.** The extended Euclidean algorithm carries four full-width
256-bit registers through all ~530 steps:
- `A`, `B` — the two operands (the shrinking `u`, `v`)
- `CA`, `CB` — their two Bézout cofactors (the running `a`, `b` such that `a·dx + b·p = gcd`)

Naively that is `4 × 256 = 1024` qubits just for the inversion core, before any scratch.

**The sharing observation** (Proos–Zalka 2003, the origin of "inversion dominates point-add space"):
the operands and their cofactors are *complementary in size*. As the algorithm runs, operand `A`
loses high bits (it shrinks toward 1) while its cofactor `CA` grows from zero. At every step the
sum `bitlen(A) + bitlen(CA)` is bounded by roughly one word. So `A` and `CA` can be **packed into a
single physical 256-bit register**: `A` in the high part, `CA` in the low part, with a small
*bit-length tracker* recording where the boundary sits. As `A` shrinks and `CA` grows, the boundary
simply slides — but the total never exceeds one word.

```
Naive:   [====== A ======][== CA (mostly zero) ==]   two separate 256-bit words
         [====== B ======][== CB (mostly zero) ==]

Shared:  [== A ==|== CA ==]   ONE word; boundary slides right as A shrinks, CA grows
         [== B ==|== CB ==]   ONE word; a 9-bit length tracker remembers the split
```

Four full registers collapse to **two "work words" + a handful of small length/control trackers**.
This is the structural source of Luo et al. 2026's compact exact reversible inversion at
`3n + 4⌊log₂ n⌋` qubits (1333q for n=256 as a standalone inversion). In the Shrunken-PZ track,
packing `A∥CA` and `B∥CB` plus dirty-catalytic borrowing and gate-hosting drove the inversion core
down to `REGISTER_SHARED_PAPER_INVERSION_QUBITS = 3·256 + 52 = 820` qubits, giving an **851-qubit
peak** for the whole point-add — a 97-qubit drop below the prior 948q record, and the 851→829q race
then squeezed out another 22.

**Where the Toffoli goes (and why that's fine here).** Packing is not free in gates: a shared word
has a *data-dependent boundary* — "where does `A` end and `CA` begin?" depends on values computed at
runtime. So every arithmetic step must first **locate and realign that boundary with a full-width
comparator**, and because the circuit is reversible, that comparator is recomputed *before and
after* each hosted gate:

```
Cost to realize ONE useful Toffoli on a packed word:
   toggle_gate ; ccx ; toggle_gate
   where toggle_gate ≈ a full-width comparator ≈ 12 × width ≈ 3,075 Toffoli at width 256
```

Across 530 divsteps this lands the 851q route at ~464.5M average Toffoli (vs ~54.8M for the
unshared 948q route). **Under the low-qubit objective this is a non-issue** — Toffoli does not enter
the score, so spending ~8× more of it to buy 97 qubits is precisely the intended trade. (For
contrast, under the *Q×T product* objective the very same packing would be ~250× over break-even, so
this technique belongs squarely to the low-qubit track, not the score track. The two objectives have
genuinely different optimal constructions — see §10 for the exchange-rate math behind that statement.)

**How to read the 851q figure.** 851q is a carefully-scoped **lower-bound witness** — a research
milestone that says "this width looks reachable," with its modeling assumptions documented openly in
the source. It is exactly the kind of result objective 2 (§2) is meant to surface. Three things are
worth knowing so you read the number for what it is:

- **The deepest figure rests on a *classical* feasibility model.** `register_shared_eea.rs` computes
  on `U256`/`U512` integers — a classical simulation rather than an emitted gate stream. Its job is
  to confirm the packing invariant `l_t + 1 + l_q + bitlen(r) ≤ n + 3` holds at all 1,479 steps —
  i.e. that operand and cofactor genuinely *fit in one word*, establishing the packing is **feasible
  in principle**. The authors flag this transparently in the header: *"an analysis oracle … passing
  this oracle does not establish a challenge-valid qubit count"* (i.e. it is a feasibility model, to
  be paired with a hardened emission before it counts as a finalized circuit).
- **The lowest counts use gate-hosting whose zero-claims are *sampled* rather than proven** (see §7.16).
  The route is honest about which guarantees are still open: `q945_local_hosts.rs` notes the
  reachable-state zero claims are not yet certified and lists the remaining "Q946 hardening"
  prerequisites; `q944_gate_host_lifecycle.rs` verifies the hosting exhaustively *at small widths*
  and extrapolates to 256 bits.
- **The status is labelled, not hidden.** `Q949_ROBUST_ENVELOPE_FRESH_VALIDITY_CLAIMED = false` and
  the `proof_status` fields mark these as lower-bound explorations rather than finalized circuits —
  good hygiene for a frontier-mapping result.

In short: the `0/0/0` run check confirms the **outputs are correct on the hunted island**, and the
851/829q figures show **how low the width can plausibly go**. The lowest count backed by a
fully-emitted, island-validated circuit with *no* outstanding hosting assumptions is the **948q**
route — the natural "validated" milestone to cite — while 851q/829q are the further-reaching
witnesses on top of it. Either way, the durable, fully-sound takeaway is the structural mechanism:
operand/cofactor packing.

**The lesson.** Register sharing is *the* route below ~948 qubits, and the Proos–Zalka / Luo-2026
mechanism is the structural source worth knowing. It is the right tool when your objective is pure
qubit count. The broader point generalizes both ways: **know which competition you are playing
before pricing a lever** — a move that is a clear win for the low-qubit objective (trade unlimited
Toffoli for lanes) can be a clear loss for the Q×T objective, and vice versa.

---

### 7.16 Gate-Hosting: Borrowing an Idle Lane Instead of Allocating

**A workhorse peak-reduction technique — it powers the 948 → 851 drop (§7.15), and it doubles as a
clean illustration of the value-exact vs island-exact distinction at the level of a *single borrowed
qubit*.**

**The idea.** Every reversible gadget needs **scratch ancilla**: a multi-controlled-X needs a lane
to accumulate the AND of its controls; a carry chain needs carry bits; a comparator needs a borrow
bit. Allocating a fresh `|0⟩` for each one is exactly what drives the peak up. But at the instant
you need scratch, some lane *elsewhere* is often sitting idle — the high bits of a number that has
shrunk, a register between its last read and next write, an idle metadata lane. **Gate-hosting
borrows that idle lane as scratch, then restores it before its owner needs it again** — so the
ancilla costs no new peak qubit. The gadget's scratch is "hosted" inside a register that belongs to
something else (hence the name; the codebase has explicit per-step tables saying which `A/B/CA/CB/Q`
lane+bit hosts each gate). This generalizes §7.13 (borrowed-carry fusion) to *any* gate's scratch.

**The hot-desking intuition.** Qubits are desks in a crowded office. Allocating a fresh ancilla =
renting a new desk (the office gets more crowded). Gate-hosting = doing your hour of work at a
colleague's empty desk while they're at lunch, then clearing it spotless before they return — no new
desk, the peak never rose.

**Two flavors:**
- **Clean hosting** — the borrowed lane is known `|0⟩`. Use it directly, restore it to `|0⟩`.
- **Dirty hosting** — the borrowed lane holds unknown live data `ψ`. You can still borrow it via a
  trick that disturbs `ψ` and then exactly un-disturbs it (the Barenco "surrounded" pattern):
  ```
  ccx(c0, c1, ψ)        ← scribble onto the borrowed lane
  ccx(ψ,  c2, target)   ← do the real work using it
  ccx(c0, c1, ψ)        ← un-scribble: ψ restored to its original value
  ccx(ψ,  c2, target)
  ```
  The two extra gates restore `ψ` perfectly. Cost: 4 Toffoli instead of 3 — a textbook
  **−1 qubit, +1 Toffoli** trade (great when the objective does not score Toffoli).

The principled, scaled-up form of dirty hosting is **conditionally-clean ancillae** (Khattar–Gidney
2024, "Laddered Toggle Detection"): a method to borrow dirty bits *as if they were clean*, with no
allocation and no separate toggle-detection pass. It is what lets a multi-controlled-X run in `~3n`
Toffoli with only `log* n` truly-clean ancilla, and it underlies the cheap MCX/`cinc` primitives
(§9.17). When you need a lot of scratch and have only dirty lanes, this is the formal tool.

**It is a compile-time bet, not a runtime scan.** A quantum circuit is static — you cannot peek at a
qubit mid-run to check "is this `|0⟩`?" (measuring would collapse it). So nothing searches for zeros
at runtime. The hosting choices are **frozen into the gate list at build time**: the compiler
asserts *"at step 437, lane 12 of register B will be `|0⟩`, so host the scratch there,"* and the
circuit runs that exact plan on every input. The whole question is whether that compile-time claim
was *true*.

**Proven-zero vs sampled-zero (value-exact vs island-exact, one qubit at a time).** The zero-claims
come in two grades:
- **Proven zero (sound, density-neutral):** the lane is zero for a *structural* reason — e.g. the
  high bits of an operand the GCD has provably shrunk, or a known-constant register. Safe for all
  inputs.
- **Sampled zero (island-exact, risky):** the claim "this lane is `|0⟩` here" is established by an
  **empirical census** — run many sample inputs, observe the lane was always zero, *assume* it
  always is. This is the grade the aggressive 851q borrows rely on. "The desk was empty every time I
  checked" is not "the desk is always empty."

**How it breaks.** If an input arrives (one not in the sample) that makes a sampled-zero host lane
*non-zero* at borrow time, the hosted gate scribbles onto live data and the circuit silently returns
a wrong answer — reversibility offers no safety net. The reason the shipped circuit still scores
`0/0/0` is that the **nonce/test island is hunted to dodge exactly those inputs**: the 9024 graded
inputs are chosen so none trips a bad borrow. So it never breaks on its own test set — because the
test set was fitted to the circuit, not because the circuit is universally correct.

**Takeaway.** Gate-hosting is a perfectly sound, standard peak-reduction technique **when the host
lane's state is proven**; it becomes an island-overfit assumption the moment the state is only
*sampled*. The same value-exact vs island-exact split from §11 applies here at the granularity of a
single borrowed `|0⟩`.

---

### 7.17 Reset-Bounded Qubit-ID Compaction (Register Allocation for Qubits)

**A free, value-exact post-pass that closes the gap between the *true* peak and the *scored* peak.**

Here is a subtlety in how the score is computed: the benchmark charges **the largest qubit *id* that
appears in the circuit**, not the true count of simultaneously-live qubits. The circuit builder
reuses freed lanes, but if its lane-numbering is even slightly loose — a temporary gets a high id
when a lower one was already free — the *max id* can sit above the real concurrent peak. That slack
is pure wasted score.

**The fix is classic register allocation, applied to qubit ids.** After the whole op stream is
built, run a compaction pass (`compact.rs`, introduced in the 1133 Pareto push):

1. Cut the timeline at every **unconditional reset** (`R`) or measurement (`Hmr`) — these mark where
   a lane's value is destroyed, so its id is free to reuse from that point.
2. Build the **lifetime interval** of every non-IO temporary lane (first use → last use within a
   reset-bounded segment).
3. **Interval-color** those intervals onto the fewest possible ids (a min-heap of free colors keyed
   by lifetime end — the textbook interval-graph coloring), while **pinning the four IO registers**
   (R.x, R.y, Q.x, Q.y) so the evaluator still finds its inputs/outputs.

The result is the same circuit (every gate identical) renumbered so that `max qubit-id` equals the
true coloring optimum. It is **value-exact and density-neutral** — it changes only the *labels* on
wires, never the computation — so it stacks freely with everything else and needs no nonce re-hunt.

**Why this is the right mental model.** A qubit id is exactly a *register* in a compiler: lanes that
are never live at the same time can share one id, just as non-overlapping variables share a machine
register. Lifetime-coloring is how compilers minimize register pressure, and it is the *provably
optimal* way to minimize `max id` for a fixed gate schedule. Whenever a circuit's reported qubit
count exceeds its measured concurrent peak (check with `TRACE_PEAK`), this pass recovers the
difference for free.

(In the 1133 push this lever is present but gated off — the 1133 count came from active-width trimming,
not compaction — so it remains an untapped drop-in for any future rung whose `max id` exceeds its
true peak.)

---

### 7.18 Windowed (Chunked) Materialization — the `F_CUT` Dial

**The biggest peak lever of the 1693→1411 era.** Many operations need a *materialized* operand — a
full-width quantum register built from something cheaper. The classic case: to add the
quantum-controlled value `f = ctrl · a` into an accumulator (where `a` is 256 bits), the naive
circuit first builds all 256 bits of `f`, then runs a 256-bit ripple adder. Two wide things are now
live at once — the materialized `f` *and* the adder's carry lane — and their sum is the peak.

**The fix: never materialize the whole operand at once.** Split the add into chunks. For each chunk:
materialize only that slice of `f`, run a small adder over just that slice, then **immediately clear
the slice with a measurement (HMR)** before moving to the next chunk. Only one chunk's worth of `f`
is ever live, and the boundary carry between chunks is cleaned up with a short truncated comparator
against the source bits.

```
Naive:   build all 256 bits of f=ctrl·a   →  256-bit ripple add   (f + carry lane both wide → tall peak)
Chunked: for each block:  build slice of f  →  add slice  →  HMR-clear slice  →  fix boundary carry
         (only one slice of f live at a time → much shorter peak)
```

**Why it's a *dial*, not a one-shot.** The chunk boundary (`F_CUT`, `APPLY_CHUNKED_F_BLOCKS`) is
tunable: each `+1` to the cut narrows the materialized slice and lowers the peak by ~1–2 qubits, at
the cost of one more boundary comparator (a few Toffoli). So you "sink" the apply phase to the next
floor by turning the dial, then re-tune it after every *other* lever lands. This single knob, re-cut
at nearly every step from 1572q down to 1411q, did most of the era's peak work.

It is the materialized-operand version of the same idea behind venting and per-step truncation:
**process a wide value a window at a time so its full width never co-resides at the peak.**

---

### 7.19 Shift-Free Scaling via Modular Doublings

A subtle qubit trap hides in "multiply by a power of two." Computing `x · 2^k mod p` the obvious way —
`shift_left(k) → operate → shift_right(k)` — needs a **spill register** to catch the `k` bits that
fall off the top during the shift, plus overflow/sign flags. In the Solinas `2^32` fold of the square
tail, that parked ~24 persistent flag qubits and pinned the peak.

**The fix uses a number-theoretic identity:** modulo `p`, multiplying by 2 *is* a modular doubling
(`mod_double`, §9.18) — a shift that immediately folds its overflow back via `+f`, leaving nothing to
spill. So `x · 2^k mod p` can be done as **`k` successive modular doublings** (and `÷2^k` as `k`
modular halvings), value-identical to the shift route but allocating **no spill register and no
flags**. It trades a handful of extra Toffoli for ~24 freed qubits — a steep, clean win at the
break-even rate (`KARA_SOL_SHIFT22_DOUBLES`, the 1558q drop).

The lesson: a "free" classical operation (a bit-shift) can be quietly *expensive* in a reversible
circuit because the shifted-out bits must be stored, not discarded — and re-expressing it in the
modular arithmetic you already have can dodge that storage entirely.

---

## 8. Toffoli Reduction: The Core Loop

1. **Measure** — get the Toffoli count; find the **hot-spot** (the phase emitting or executing
   the most CCX gates). Note emitted vs average-executed.
2. **Classify** — identify what *kind* of Toffoli these are (table below).
3. **Pick the matching move** — the kind determines the technique.
4. **Cost it** — depth-neutral? qubit cost? worth it at the exchange rate?
5. **Re-measure** — the hot-spot migrates; repeat.

### Classifying Toffoli by kind

| Kind of Toffoli at the hot-spot | The matching move |
|----------------------------------|-------------------|
| **Carry-uncompute** (reverse carry chain returning scratch to `|0⟩`) | **Vent** via MBU (§9.1) |
| **Self-uncomputing scratch** (comparators built then cleanly reversed) | **Conditional replay** (§9.3) |
| **Data-controlled arithmetic** (`cadd`, fold-sub on live data) | Fusion / avoid materialization |
| **Majority gadgets** (3-CCX majority in carry logic) | **Ancilla-free majority** (§9.12) |
| **Redundant final cleanup** (top-clean made unnecessary by structure) | **Skip it** (§9.14) |
| **Full intermediate products / wide rows** | **Avoid materialization** (§9.5) |
| **Adjacent algebraic stages** (add/negate/subtract chains) | **Algebraic fusion** (§9.4) |

---

## 9. Toffoli Reduction Techniques (1–19)

### 9.1 Measurement-Based Uncomputation (MBU) — The Most Important Technique

**The Toffoli lifecycle problem**: An AND gate costs 4 T-gates (1 Toffoli) to compute.
The uncomputation normally costs another 4 T-gates. Computing + uncomputing one AND = 2 Toffoli.

**MBU** (Jones 2013, applied to adder carry chains by Gidney 2018):

```
1. Forward: ccx(a, b, out)       → 4 T-gates (1 Toffoli)
2. Use 'out' in downstream logic
3. Uncompute: measure 'out' in X-basis (Hadamard, then Z-basis measure)
   Result is classical bit m ∈ {0, 1}
   - If m = 0: done, free 'out'  → 0 Toffoli
   - If m = 1: apply CZ(a, b)    → 0 Toffoli (CZ is a Clifford gate)
Total uncompute cost: 0 Toffoli
```

**Why does this work?** When you compute `out = a AND b` into a clean `|0⟩` ancilla, the system
is in state `|a, b, a·b⟩`. Measuring `out` in the X-basis either succeeds cleanly (m=0) or
applies a phase kick `(−1)` to the `|a=1, b=1⟩` component (m=1). The CZ gate corrects exactly
that phase. After correction, `out` is disentangled from `(a,b)` and can be freed.

The key insight: **measurement collapses entanglement for free**. Coherent uncomputation must
undo entanglement gate-by-gate; measurement does it in one shot.

**The tradeoff**: The `out` qubit must remain live from when it's computed to when it's measured
(typically between the forward and reverse carry chains). This costs +1 peak qubit during that window.

**Practical effect on adders**: An n-bit ripple-carry adder normally costs ~2n Toffoli
(n forward, n reverse). With MBU on every carry-uncompute:
```
Total adder cost = n Toffoli (forward only) + 0 (measured uncompute) = n Toffoli
```
This halves the adder cost — the most important constant-factor improvement in the SOTA.

---

### 9.2 The Vent Dial

§9.1 showed that MBU can *uncompute* one carry bit for **0 Toffoli** (measure it, then a free
Clifford fix-up) instead of the 1 Toffoli a coherent uncompute would cost — the catch being that the
carry qubit has to stay alive a little longer. Applying that choice to *one* carry in an adder is
called a **vent**. The whole "dial" is just: *how many of an adder's carries do you choose to vent?*

**Where the `3n − 2` comes from.** A reversible n-bit adder builds a chain of carry bits climbing up
the word (the *forward* pass), uses the final carry, then unwinds that chain (the *reverse* pass) to
return all the scratch qubits to `|0⟩` (this compute–use–uncompute cycle is the reversibility tax
from §3). Tallying the Toffoli in that cycle for the hybrid carry adder used here gives a fixed
baseline of about `3n − 2` Toffoli when *nothing* is vented. Each carry you vent deletes one Toffoli
from the reverse (uncompute) half. So with `k` vents:

```
Toffoli cost = 3n − 2 − k        ← one fewer Toffoli per vented carry
Peak qubits  = baseline + k      ← but each vented carry stays live a bit longer
```

The dial is therefore perfectly linear and perfectly priced: **each vent = −1 Toffoli, +1 temporary
peak qubit.**

**Why the qubit is only *temporary* — the "forward↔reverse window."** A vented carry can't be freed
the instant it's measured: its measurement outcome is still needed later, when the reverse pass
reaches that bit position to clean it up. So the qubit is occupied only from when that carry is first
computed (forward) until it is finally cleaned up (reverse) — the stretch in between is the
"forward↔reverse window." Outside that window the lane is free, which is exactly why the `+k` qubits
don't add to the circuit's permanent footprint.

**When to vent — it depends on *where* the adder sits in the timeline.** Recall from §5 that the
circuit's qubit peak happens during a few specific phases (the *binder*), while other phases have
**slack** — spare qubits sitting idle. So:
- **Off-peak adders** (running during a phase with slack): holding `+1` qubit there does *not* raise
  the *global* peak, so venting is **pure profit** — free Toffoli savings at zero score cost. Vent
  every carry you can.
- **On-peak adders** (running at the binder): every extra qubit pushes the peak — and the score — up.
  Vent only if the Toffoli saved is worth more than the qubit, judged by the exchange rate (§10).

**How the SOTA automates it.** `trailmix_ludicrous` doesn't choose by hand. It fixes a circuit-wide
qubit ceiling `TLM_TARGET_Q`, and for each adder call vents exactly `TLM_TARGET_Q − active_qubits`
carries — i.e. it spends *all* the spare headroom beneath the ceiling on Toffoli savings, and not one
qubit more. An adder already sitting at the ceiling gets `0` vents (no room); an adder with lots of
slack gets vented heavily. This is the dynamic-headroom clamp (§7.10) and the vent dial working
together.

**Gidney 2025 streaming vented adder** (arXiv:2507.23079): a newer construction that uses 2 clean +
(n−2) *dirty* (borrowed, §7.16) ancilla for ~3n Toffoli. Partially implemented in `venting.rs` but
**currently leaks phase** — the phase correction for the dirty ancilla is incomplete — so it is not
yet in the SOTA. Expected ~n/4 Toffoli savings per adder once fixed.

---

### 9.3 Conditional / Measured Replay (Average-Executed Only)

**The idea**: If a comparator flag is `|0⟩` on most inputs, measure the flag instead of keeping
it coherent. Then replay the dependent computation conditionally on the measurement outcome.

```
1. Compute flag F into scratch ancilla (costs C Toffoli)
2. Measure F in X-basis → classical bit m
3. If m = 0: dependent block is a no-op on this shot  → 0 Toffoli from the block
4. If m = 1: replay the block classically conditioned on m  → full cost
Average cost = C + Pr[F=1] × (block cost)
```

When F fires on fraction f of inputs: average-executed drops from `(block cost)` to
`f × (block cost)`. If `f = 0.05`, you pay only 5% on average.

**The hard constraint**: This ONLY works on **self-uncomputing scratch** — a comparator you
compute, read under the condition, and cleanly reverse. It does NOT work on:
- Data-controlled operations (where the control is live quantum data, not a measurable scratch bit)
- Predicates reused downstream (you can't measure-and-discard them)

**Named implementations** in the SOTA:
- `DIALOG_GCD_REVERSE_BRANCH_CONDITIONAL_REPLAY`
- `DIALOG_GCD_SPECIAL_CLEAN_CONDITIONAL_REPLAY`
- `DIALOG_GCD_APPLY_BOUNDARY_CONDITIONAL_REPLAY`
- `MOD_FAST_FLAG_CONDITIONAL_REPLAY`

The key primitive: `cmp_lt_phase_conditioned()` in `compare.rs`. It: (1) HMRs the comparison
flag, (2) replays the predicate classically (CZ/CX conditioned on the measurement), (3) the
comparison's Toffoli collapses to near 0 on most shots at zero peak qubit cost.

---

### 9.4 Algebraic Fusion: Collapse Add/Negate Chains

Adjacent modular-arithmetic stages that are algebraically equivalent to a simpler single
operation can be collapsed to eliminate intermediate carry chains.

**Example (`DIALOG_FUSE_C_FORM`)**:
```
Old:
  tx += 2*Qx    (mod add)
  tx = -tx      (mod negate)
  tx -= Qx      (mod sub)
  tx = -tx      (mod negate)

Algebraically (two negations cancel, constants combine):
  tx += 3*Qx    (one mod add)
```

**Example (`DIALOG_FUSE_X_RESTORE`)**:
```
Old:
  tx = -tx      (mod negate)
  tx += Qx      (mod add)

Algebraically:
  tx = Qx - tx  (one operation)
```

Each removed negate/add/subtract eliminates a carry chain, a modular reduction fold, and a
cleanup phase — saving significant Toffoli.

**Checklist before applying**:
1. Prove the algebra holds modulo p, including underflow/overflow behavior.
2. Confirm the intermediate value is not used as a control, measured, or needed by an uncompute
   step between the original operations.
3. Implement behind a default-off knob; verify the off path is byte-identical to the original.
4. Run component self-tests for value, phase, and ancilla cleanliness.
5. Re-measure peak qubits AND average Toffoli — a fusion should be peak-neutral but check.

---

### 9.5 Witness-First / Deferred-Output Dataflow

Sometimes a cancellation only needs a *witness relation*, not the final output value.
Computing the output early and then cleaning it is wasteful when the witness is cheaper.

**The 4352cfb Toffoli cut** (−10.8M Toffoli at fixed 980 qubits):

Old EC dataflow for slope cancellation:
```
1. Compute dx_diff = tx_orig - new_x    (allocates temp register)
2. Compute new_y = dy + λ × dx_diff - oy  (uses expensive multiply + constants)
3. Derive new_dy = new_y + oy           (the witness numerator)
4. Cancel λ using new_dy / new_dx
5. Use new_y as output later
```

New route (zero-dy/newdx):
```
Key identity: new_dy = λ × new_dx  (from the curve equation, no new_y needed)

1. Erase dy using: dy = λ × dx  (subtract λ×dx from dy → zero)
2. Reuse the zeroed dy register as scratch
3. Compute new_x
4. Compute new_dx = ox - new_x
5. Compute new_dy = λ × new_dx  (the witness, not the output)
6. Cancel λ using new_dy / new_dx
7. Materialize new_y = new_dy - oy  (only NOW compute the output)
```

The old route built `dx_diff`, ran a full multiply, added constants, then converted to the
witness form. The new route skips the expensive early `new_y` materialization and computes
only what the cancellation actually needs (the ratio `new_dy/new_dx`).

**Ablation**:
```
zero-dy disabled, defer-y disabled:   110,227,695 emitted ops
defer-y materialization only:         105,573,887 emitted ops  (−4.6M)
both zero-dy + defer-y:                92,105,748 emitted ops  (−18.1M total)
```

**General principle**: Before materializing any output, ask: "does the next operation NEED the
output, or just a function of it that's cheaper to compute directly?"

---

### 9.6 Karatsuba Modular Square (−22.4 Million Toffoli)

The largest single Toffoli reduction in the project's history.

**The schoolbook problem**: Computing `λ²` for a 256-bit number using schoolbook multiplication
visits every pair of bit-chunks, costing O(n²) multiplications.

**Karatsuba**: For a 256-bit number split as `λ = hi × 2^128 + lo`, use the identity:
```
λ² = (hi × 2^128 + lo)²
   = hi² × 2^256 + 2(hi × lo) × 2^128 + lo²
   = hi² × 2^256 + [(lo+hi)² − lo² − hi²] × 2^128 + lo²
```

So instead of computing 4 products (lo², hi², lo×hi twice), compute only 3 squares:
- `lo²` (128-bit square)
- `hi²` (128-bit square)
- `(lo + hi)²` (128-bit square)

Then reconstruct the cross-term via additions (which are cheap Clifford operations).

**Why −22.4M Toffoli**: The squaring operation runs at EVERY GCD step (258 steps × 2 passes).
Any O(n²) → O(n^1.585) improvement compounds massively across all those calls.

**Density-neutral**: The Karatsuba identity `(lo+hi)² = lo² + hi² + 2·lo·hi` is a pure
algebraic identity, correct for all integers. No approximation.

**Recursive Karatsuba**: Tested on 128-bit sub-squares → net Toffoli LOSS (the overhead of the
additions outweighs the sub-square savings at that level). Dead end.

**The space/Toffoli tension (it cuts both ways).** Karatsuba's middle-term trick saves Toffoli but
*needs scratch* for the three sub-products and the `(lo+hi)²` term. When the square is sitting at the
qubit peak, the **opposite** move can be the win: drop back to a plain **schoolbook** square, which
needs no middle-term scratch (fewer qubits) at the cost of more Toffoli. The SOTA toggles this per
context (`ROUND84` "schoolbook x-tail") — Karatsuba where Toffoli is the binding constraint,
schoolbook where *qubits* are. This is the same exchange-rate decision as everywhere else (§10):
which axis is binding here decides which square you want.

---

### 9.7 NAF Recoding of Constants

**The problem**: The secp256k1 constant `977 = 1111010001₂` has 6 set bits. Each Solinas
reduction fold involving `977` requires 6 modular additions.

**NAF (Non-Adjacent Form)** uses signed digits `{−1, 0, +1}`:
```
977 = 2^10 − 2^5 − 2^4 + 1   (4 signed terms vs 6 unsigned)
```

In NAF, no two adjacent digits are both non-zero, and the number of non-zero digits is minimal.
For `977`: 4 terms instead of 6, saving ~33% of the Solinas fold cost.

**Density-neutral**: The identity `977 = 1024 − 32 − 16 + 1` is a mathematical fact, correct
for all inputs.

Also applied to `c = 2^32 + 977` (the secp256k1 pseudo-Mersenne fold constant — see §9.18),
saving terms in every modular reduction fold.

---

### 9.8 Dead-CCX Elimination (Empirical Drop vs Structural Skip)

Some CCX gates contribute nothing to the answer — either their control is always zero, or their net
effect cancels out — yet the scorer still *charges* them. Deleting such "dead" gates lowers the
average-executed Toffoli. There are two ways to find them, with **very different correctness
profiles**, and the difference is the single clearest example of the overfitting trap in the whole
project.

**(1) Empirical dead-CCX drop (the island-overfit lever).** Run the circuit over a large sample of
inputs (~9 million reachable EC points, or many Fiat-Shamir test sets); record which CCX gates
**never flip their target** — i.e. are *inert-but-charged* on the sample. Collect their positions
into a `.idx` file (e.g. 13,873 op indices) and simply filter them out of the emitted op stream:

```
ops = ops.filter(|(i, _)| !drop_set.contains(i))   // delete the inert-but-charged CCX
```

This was the engine behind the SOTA average-Toffoli for a long time (a single drop was worth
~13,000+ avg-Toffoli). **But it is distribution-exact / island-overfit, and dangerous for three
reasons:**

- **It deletes gates that *could* fire on unsampled inputs.** The result is "clean on its island"
  (`0/0/0` over the hunted 9024) but **not** provably correct off-island. A gate that was inert on
  every sampled input may be live on some input you never tried — and then the deletion silently
  corrupts the output.
- **The indices are absolute positions in one exact op stream.** *Any* structural change — a clamp,
  a knob, a fold toggle, even reordering — shifts every later gate onto the wrong index, so a stale
  list now deletes *live* gates → catastrophic failure (the `9024/141/141` all-shots breakage). Every
  variant must ship its own freshly-screened list and a freshly-hunted nonce.
- **It does not improve the construction.** A genuinely better circuit would not *emit* these gates
  in the first place; the drop just hides them from the scorer. It is the first thing invalidated by
  any real structural improvement. Think of it as a sophisticated nonce grind — worth knowing it
  exists (it's why the SOTA avg-T looked low), but low-value to reimplement except to squeeze a
  *frozen* final artifact.

**Iterated (two-pass) empirical drop** (`DROP_DEAD_ROBUST_SECOND`): the drop is **iterable**. After
the first drop reshapes the stream, re-screen the *already-dropped* stream — a second screen finds
gates that are newly (or only now detectably) dead — drop a second, smaller list, and re-hunt the
nonce with *both* drops on. Each pass is subset-monotone with diminishing returns (the 2nd pass was
worth ~−2,411 avgT at 1153q). All the overfitting caveats above apply at every pass.

**(2) Structural dead-CCX skip (the sound, density-neutral lever — CURRENT SOTA).** Instead of
*sampling*, **prove** a CCX never fires on *any* input from circuit structure alone (known-constant
carries, exact-remainder conditions, call-site bit patterns). Named predicates in
`trailmix_ludicrous`: `TLM_FFG_SKIP_STRUCTURAL_DEAD_*`, `TLM_CUCCARO_SKIP_STRUCTURAL_DEAD_*`,
`TLM_COMPARE_SKIP_STRUCTURAL_DEAD_*`, `TLM_GIDNEY_SKIP_STRUCTURAL_DEAD_*`. These are keyed by
call-site and bit-index, not by sampled data, so they are **density-neutral** (correct on all
inputs, stackable freely, no `.idx`, no re-screen).

**The 6dafa07 pivot.** The SOTA *replaced* the empirical drop entirely with structural skipping —
which turned out to be **both sound and lower-Toffoli**. This is the general lesson in miniature:
when an island-exact lever is doing real work, look for the *structural* reason those gates are dead
and skip them provably. If the gates truly never fire, you can usually prove it — and then the
overfitting risk disappears for free. (See §11 for the value-exact vs island-exact framing.)

---

### 9.9 Classical Constant Folding (Zero-Toffoli Operations)

When one operand of an arithmetic operation is a **classical constant** (known at compile time),
the operation can often be implemented with 0 Toffoli gates.

**The mechanism**: A `BitId` register holds a constant pattern as compile-time information.
Operations with one classical operand:
- `qubit XOR 0` = identity (no gate)
- `qubit XOR 1` = Pauli X (free Clifford gate)
- `qubit + classical_constant mod p` = a series of CNOT-like operations on specific bit
  positions — 0 Toffoli.

**In trailmix_ludicrous**: `Q = (Qx, Qy)` is classical. So:
```rust
coord_add3x(circ, x2, ox, qubits);  // x2 += 3·Qx mod p
```
Since `Qx` is fixed at compile time, `3 × Qx mod p` is also fixed. The addition becomes a
series of `x_if_bit` (CNOT-like) operations — **0 Toffoli**.

The zero-Toffoli negate (step 15 in the point-add): `ox − x2 = −(x2 − ox)`. Load classical
`ox`, subtract, free, then `mod_neg` (a const-add of `f−1`). All X / const-add gates, 0 Toffoli.

---

### 9.10 Converged-Tail Gate Elision (`TLM_APPLY_CSWAP_SKIP_LASTK`)

In the last K iterations of the 530-step GCD, the algorithm has converged and the apply-phase
`cswap` (which swaps u and v based on the swap decision) has a control that is deterministically
0 on all but rare inputs.

**The optimization**: Skip the cswap for those last K iterations. On the overwhelming majority
of inputs, this is exact. The rare input that actually needs the swap is caught by the nonce-hunting
process (find a nonce where all 9024 test inputs happen to not trigger the swap in those iterations).

**Cost**: Island-exact. Requires re-hunting the tail nonce after applying.

---

### 9.11 GAP_J2 Comparator Window Narrowing (−1.33M Toffoli)

The swap decision comparator at each GCD step checks whether `|u| > |v|`. A full 256-bit
comparison would be expensive, but the GCD ensures that `u` and `v` typically differ somewhere
in their top bits.

**The schedule `GAP_J2[i]`** (258-element table) sets the comparator window width per GCD step.
The comparator scans only the top `GAP_J2[i]` bits. If the highest differing bit is below the
window, the swap decision might be wrong (probability ~`2^(−k)` per step, calibrated against the
challenge's input distribution).

**Effect**: A 22-line edit to the `GAP_J2` table to shave ~1 bit per step across 258 steps:
```
Toffoli saved = 1 bit × 516 comparator calls ≈ 1.33M Toffoli
```

This is one of the highest-leverage edits in the project: 22 lines, 1.33M Toffoli savings.
**Island-exact** — requires nonce hunting.

---

### 9.12 Ancilla-Free Majority

Standard carry logic uses a 3-input majority gate with 3 Toffoli and an ancilla. The identity:
```
maj(a, k, c) = c XOR ((a XOR c) AND (k XOR c))
```

implements the same majority with **2 Toffoli and no ancilla** (XOR = CNOT, AND = CCX).
Peak-neutral, value-identical, pure count reduction wherever majority gates appear.

Applied to every carry position in every adder in the circuit.

---

### 9.13 Exact-Adder Recovery (Removing a Truncation Can REDUCE Toffoli)

Counter-intuitive: Sometimes a truncated adder costs **more** Toffoli than the exact
full-carry adder, because the truncation requires an expensive correction to handle the rare
carry-escape cases.

**The rule**: If the correction overhead of a truncated adder exceeds its savings from
dropping bits, revert to the exact adder:
- Saves Toffoli (no correction overhead)
- Reduces hard inputs (fewer inputs where truncation would fail, so easier nonce hunting)

Named: `DIALOG_GCD_APPLY_FINAL_TOPCLEAN=0` — removes the truncated top-clean adder, replacing
with the exact variant → ~−2,597 avg-Toffoli, value-exact.

---

### 9.14 Skip Redundant Final Cleanup

A folded/structured computation sometimes makes a final "top-clean" pass redundant — the
structure ensures the cleanup bits are already zero by construction. Dropping the cleanup
removes its Toffoli.

**This is the highest-risk move**. If the cleanup is not actually redundant, you get silent
phase/classical dirt on some inputs. Always pair with strong `cls/pha/anc` validation before
enabling.

---

### 9.15 Off-Peak Loosening (The Dual Move)

When a phase falls **off** the qubit peak (another phase is now the binder), you can WIDEN
that phase's arithmetic to recover Toffoli for free:

```
Phase A: was binder at 1170q → locally reduced to 1162q
Phase B: now binder at 1170q (unchanged)
Action: widen Phase A's carry width back toward the old value
Effect: Phase A's Toffoli drops; Peak stays at 1170 (Phase B is binding)
```

**The rule**: Shrinking an off-peak phase is a pure-Toffoli play (no qubit cost). Widening
an off-peak phase is a free Toffoli refund. Govern both on gates alone, not qubits.

---

### 9.16 Constprop: Automated Static Gate Elimination

The constraint-propagation pass (`CONSTPROP_MAX_ITERS`) analyzes the circuit statically and
eliminates:
- **Provably-constant CCX gates**: control always 0 → remove; control always 1 → replace with CNOT
- **Inverse-pair cancellation**: consecutive `CCX(a,b,c)` gates that cancel algebraically
- **Affine simplification**: sequences simplifying to an affine function, implementable with fewer gates

Setting `CONSTPROP_MAX_ITERS=256` (vs default 16) runs to a deeper fixpoint, finding more
opportunities: −377k Toffoli in one version.

---

### 9.17 Quadratic-Cascade → Controlled-Increment (cinc)

**Replace an O(t²) gadget with an O(t) one when the math allows.** A recurring pattern is a
"carry-into-tail" or prefix-propagation built as a **quadratic cascade of multi-controlled-X gates**
(`mcx_clean_k` over a window `[nv, L)` — every position controls on all the positions below it,
giving O(t²) MCX work).

When the cascade is computing a *carry propagation* (the standard "increment if all low bits are 1"
pattern), it is exactly a **controlled increment**, and there is a cheaper exact primitive for that:
the **Khattar–Gidney controlled-increment** `cinc` (arXiv:2407.17966), which uses only `log* n`
clean ancilla and O(n) Toffoli instead of the quadratic cascade.

```
Old: clean-tail fold carry = mcx_clean_k prefix cascade over [nv, L)   → O(t²) MCX
New: clean-tail fold carry = cinc_khattar_gidney (one controlled +1)   → O(t),  log*-ancilla
```

**Value-exact and density-neutral**: it is an exact functional replacement (same truth table), so
it does not touch the island distribution — it can be stacked freely without re-hunting a nonce.
Named `TLM_FOLD_TAIL_CINC`; worth ~−5,175 avgT alone. This is the **"safe" Toffoli lever class**:
unlike dead-CCX deletion (§9.8, distribution-exact), a cinc swap is correct on all inputs. When
choosing what to stack first, prefer this class — it carries none of the dead-CCX re-screen risk.

The general principle: **whenever a gadget's cost is quadratic in a window width, ask whether it is
secretly a standard primitive (increment, compare, prefix-AND) with a known linear construction.**

---

### 9.18 Pseudo-Mersenne (Solinas) Modular Arithmetic

This is the workhorse that makes *every* modular operation cheap. The math background is in §4
(pseudo-Mersenne reduction): because `p = 2^256 − c` with `c = 2^32 + 977` only 33 bits,
`2^256 ≡ c (mod p)`, so a reduction is a cheap **fold** of the top bits into the bottom, not a
division. Here is how that identity becomes actual reversible gadgets (Schrottenloher Algs 7/10/11;
trailmix `pm_prims.rs` / `arith.rs`). The constant `c` is called `f` in the code.

**Modular doubling — `2x mod p` (Alg 7).** Shift `x` left by one bit (now up to 257 bits). The part
that spilled past bit 256 has weight `2^256 ≡ c`, so it folds back as `+c`:

```
2x mod p:
  1. shift-left by 1                       (a relabel — 0 Toffoli)
  2. if the top bit overflowed: add c into the LOW limbs   (controlled +f, short)
  3. one CX to clear the overflow ancilla
```

**Modular addition — `x + y mod p` (Alg 10).** `x + y` overflows `2^256` by at most one bit; on
overflow, fold it as `+c` in the low limbs, then erase the overflow flag with a compare:

```
x + y mod p:
  1. add y into x                          (a Cuccaro/Gidney adder)
  2. if overflow (carry-out = 1): add c into the low limbs
  3. erase the overflow ancilla via a y<x comparison
```

Alg 11 additionally handles the degenerate case `x + y = p` (all the high bits equal) — needed only
in the GCD's first `≈c·√n` "empty" padding iterations, so the expensive variant is routed *only*
there and the cheap Alg-10 used everywhere else.

**The two approximations that make it cheap (and their dials).** Doing these *exactly* would still
need full-width compares and adds. Two structural facts let you truncate — because `c` is small:

- **`+f` touches only the low limbs (the `lsbs` dial).** Folding `+c` perturbs only the bottom ~33
  bits plus a short carry ripple, so the `+f` adder is run over a narrow window of width `lsbs`
  (trailmix uses ~54–63). Too narrow and a long carry ripple is missed; per-call failure
  ≈ `2^(−padding)` ≈ `2^(−30)` at their settings. *Shipped as* `*_CARRY_TRUNC_W` /
  `ROUND84_INPLACE_SOLINAS_FOLD` / the low-54-bit `+f` fold (§13).
- **Overflow/degeneracy is decided from only the top bits (the `msbs` dial).** Whether `x+y ≥ p`
  (or `2x ≥ p`) is dominated by the high bits, so the comparison scans only the top `msbs` bits
  (the paper uses 40–50). *Shipped as* `DIALOG_GCD_COMPARE_BITS` / `*_APPLY_CLEAN_COMPARE_BITS`.

Both are **graded / island-exact** levers (§6, §11): tightening a notch is value-exact only on a
searched nonce-island, because it makes a `2^(−k)`-rare fraction of inputs reduce wrong. They sit on
exactly the binary-vs-graded line of §6 and are tuned against the 9024-shot `0/0/0` target.

**Borrowed-dirty `+f` window (`gidney_cadd_f_window`).** The `+f` add needs carry scratch; instead
of fresh ancilla it **borrows the register's own idle high bits** as that scratch (~3 clean ancilla
instead of ~10), restoring them after — gate-hosting (§7.16) applied to the fold. So the reduction
adds ~0 clean qubits at the peak, value/phase-identical to the vented path.

**Why it matters.** A generic-prime reduction is a full multiprecision divide (Barrett/Montgomery,
~n-bit work) on *every* add and double, and the GCD/Bézout reconstruction does thousands of them.
Pseudo-Mersenne turns each into a short `+f` fold + a top-bits compare. That is the entire
secp256k1 advantage: constant-adder 15% vs 34% of Toffoli, modular-double 8% vs 24% (§4). **No
Montgomery form is used** — both the paper and trailmix keep plain integer representation and fold
directly. NAF recoding (§9.7) is the next layer: it makes the fold constant `c` itself cheaper
(4 signed terms instead of 6), shaving each fold further.

---

### 9.19 Merging Adjacent Controlled-Swaps

The GCD loop swaps its two operand registers conditionally at almost every step (the
"is `|u| > |v|`?" decision swaps `u` and `v`, and likewise their Bézout cofactors). A controlled swap
of two n-bit registers costs n Toffoli (one `cswap` per bit position). Across ~530 steps × two
register pairs, these `cswap`s are a large slice of the Toffoli budget.

**The identity that merges them.** Two controlled swaps of the *same pair of registers*, controlled
by bits `p` and `q`, compose into a *single* controlled swap controlled by `p ⊕ q`:

```
cswap(p, A, B) · cswap(q, A, B)  =  cswap(p ⊕ q, A, B)
```

(Swapping under `p`, then again under `q`, swaps exactly when an odd number of the two controls fired
— i.e. when `p ⊕ q = 1`.) So wherever two swap decisions on the same registers sit next to each other
— for example the cofactor swap at the *end* of one GCD step and the operand swap at the *start* of
the next — you can replace **two** n-Toffoli swaps with **one**, after spending a single cheap CNOT to
compute `p ⊕ q` into a "frame-parity" qubit. That parity bit (one qubit) carries the accumulated swap
state across the boundary.

This is **algebraic fusion (§9.4) specialized to swaps**, and it is value-exact (a pure identity, all
inputs). It was the single biggest Toffoli win of the early era — the Kaliski `step9 ∘ step3` boundary
merge, **−274,000 Toffoli, peak-neutral**. The general lesson: *controlled swaps compose through XOR
of their controls* — look for adjacent swaps on the same lanes and collapse them.

---

## 10. The Qubit ↔ Toffoli Exchange Rate and the Product Race

### The fundamental arithmetic

At the current SOTA (1152q × 1,364,230 avgT = 1,571,592,960 score):

```
break-even rate = avgT / peak_q = 1,364,230 / 1152 ≈ 1,184 Toffoli per qubit
```

A lever that saves 1 qubit at the cost of fewer than 1,184 Toffoli **improves the score**.
A lever that costs more than 1,184 Toffoli per qubit saved **worsens the score** — even though
it reduced qubits.

This rate **changes with every optimization**:
- After a large Toffoli reduction: the rate drops (qubits become more valuable). Previously-marginal
  qubit cuts are now worth trying.
- After a large qubit reduction: the rate rises. Previously-marginal Toffoli cuts might now dominate.

### The product-race caveat: always compare products, not just break-even

A qubit drop that clears break-even can STILL lose the product race if the Toffoli-grinding
track moves faster in parallel.

**Concrete example** (June 2026):
- A 1157q clamp cost ~1,127 Toffoli/qubit — below break-even at landing, won SOTA.
- But the 1159q Toffoli-grind reached 1,378,242 avgT.
- Score comparison: `1159 × 1,378,242 = 1,597,506,378 < 1157 × 1,380,890 = 1,598,290,330`
- The 2-qubit savings was overtaken by the parallel Toffoli-cutting track.

**Lesson**: Always run both tracks and compare products. Never minimize qubit count in isolation.

### The shelved-lever rule

A qubit lever that **failed break-even on one Toffoli base** can become favorable on a
cheaper Toffoli base.

**Example**: The dynamic headroom clamp (`TLM_TARGET_Q`) cost ~1,514 Toffoli/qubit on the
schoolbook-square base. After Karatsuba reduced the square cost, the same clamp cost only ~20
Toffoli/qubit on the new base — well below break-even. It won.

**Rule**: After any major arithmetic win (Karatsuba, algebraic fusion, structural rewrite),
re-test **all previously-shelved qubit levers** at the new exchange rate.

### Different peak layers have different exchange rates

At any peak, there are typically two layers:

1. **Persistent floor**: long-lived state held across the whole peak (transcript, passenger
   values, GCD state). Often **cheap** to reduce — a denser codec or transcript streaming costs
   few gates to save many qubits.

2. **Transient working registers**: the current step's carry bits, arithmetic scratch. Often
   **expensive** to reduce — freeing them requires recompute/dirty-borrow, adding many Toffoli.

Counter-intuitively: **compress the transcript before freeing the scratch**. The transcript
looks "irreducible" (structured data) but is often the cheap lever. The scratch looks
"wasteful" but is often the expensive lever.

---

## 11. Density-Neutral vs Island-Exact — Correctness Regimes

### The fundamental distinction

**Density-neutral (value-exact)**: The circuit produces the same output on ALL inputs.
The optimization is grounded in mathematical identity or circuit structure.

**Island-exact (distribution-specific)**: The circuit is correct only on the specific 9024
test inputs. On other inputs, it may give wrong answers.

### Why this matters

When you apply an island-exact optimization, some inputs that were previously "clean" (pass
the validator) may now fail. You need to find a new **nonce** — a 48-byte seed for the test
input generator — such that all 9024 generated inputs happen to be in the safe zone.

Stacking multiple island-exact optimizations makes the safe zone smaller. After enough
stacking, no valid nonce exists. You've optimized yourself into a corner.

Density-neutral optimizations preserve the valid nonce pool. They can be stacked freely.

### A common island-exact lever: active-iteration trimming

The GCD inversion is run for a fixed number of steps chosen to cover the *worst-case* input. But the
worst case is rare, so you can run **fewer** iterations (`DIALOG_GCD_ACTIVE_ITERATIONS`, e.g. 399→393)
and accept that a `~2^(−k)`-rare fraction of inputs won't have fully converged. This is a pure
island-exact lever — it drops whole divsteps (qubits *and* Toffoli) but makes the circuit wrong on
those rare inputs, so it must be paired with a nonce hunt. It sits alongside carry-truncation (§7.4)
and comparator-narrowing (§9.11/§9.18) as a "graded" knob (§6).

> **The line between island-exact and cheating.** Island-exact levers are legitimate *because the
> 9024 validated inputs are the actual scored distribution* and the failures they introduce are
> genuinely rare and structurally understood. There is a real line, though: deliberately truncating
> the circuit so it is wrong on a *large* fraction of inputs and then re-rolling the nonce purely to
> *hide* those failures is verifier-gaming, not optimization — a "red-team" demonstration that the
> early history contains at least one flagged example of (a 396-iteration build wrong on ~3×10⁻⁴ of
> inputs, shipped with a comment admitting it). The community norm: an island-exact cut should be a
> structurally-sound approximation whose error you can *bound and explain*, not a way to launder a
> broken circuit past the gate.

### The 6dafa07 pivot: empirical → structural dead-CCX

Before the current SOTA, the circuit used **empirical dead-CCX elimination**: sample 9M inputs,
find CCX gates that never fire, skip them. Island-exact — those CCX might fire on other inputs.

The 6dafa07 commit replaced this with **structural dead-CCX skipping**: prove from circuit
structure which CCX gates can never fire on any input. These predicates are keyed by call-site
and bit-index, not sampled data. Density-neutral.

### The correctness check triple: `cls / pha / anc`

Every validation run checks three error types:
- `cls`: classical mismatch (the output value is wrong on some input)
- `pha`: phase error (the output is correct but entangled with extra phase — kills interference)
- `anc`: ancilla mismatch (a qubit failed to uncompute back to `|0⟩`)

A correct circuit shows `0 / 0 / 0`. Measurement-based uncompute fails in `pha` (which value
checks miss). Truncation failures typically show in `cls`. Missed uncompute shows in `anc`.

---

## 12. Pebbling Theory — The Formal Foundation

### The reversible pebble game

The **pebble game** models space-time tradeoffs in reversible computation. The computation is
a directed graph (nodes = values, edges = dependencies). A "pebble" = a qubit holding that
value. Rules:
- Place a pebble on a node if all predecessors have pebbles (compute it)
- Remove a pebble by running computation backward (uncompute it)

Peak qubits = maximum pebbles simultaneously.

### Bennett pebbling: classical reversibility is expensive

Bennett (1989) showed that reversibly simulating a T-step computation using S extra pebbles costs:
```
Time = ε × 2^(1/ε) × T^(1+ε) / S^ε   (for any ε > 0)
```

The hidden constant `c(ε) = ε × 2^(1/ε)` grows **exponentially** as ε → 0 (Levine-Sherman 1990).

**Concrete example**: Halving the GCD transcript (S halved, ε = 1):
```
Time blowup ≈ 1 × 2 × 530² / 370 ≈ 1,518 extra GCD passes
```
At ~2,500 Toffoli per pass: 3.8M extra Toffoli for ~370q savings.
Break-even needs: 3.8M / 1,184 ≈ 3,200 qubits. Actual saving: 370. Not worth it.

### Quantum (spooky) pebbling: exponentially better

**Gidney (2019)** introduced **spooky pebbling**: also allow removing a pebble by measuring it
in the X-basis, recording the measurement outcome as a classical bit. When the value is needed
again, recompute it and apply a classically-conditioned phase correction.

**Kornerup, Sadun, Soloveichik (2021)** proved tight bounds:
```
Quantum: Time = O(T/ε)        [constant factor 1/ε — polynomial]
Classical: Time = O(2^(1/ε) × T)  [constant factor exponential in 1/ε]
```

The quantum advantage is exponential. This is the theoretical backbone of why MBU and
measurement-based techniques dominate — they exploit a space-time tradeoff physically impossible
for purely classical reversible computation.

### Parallel spooky pebbling (Kahanamoku-Meyer et al. 2025)

For a length-ℓ sequential computation chain:
```
qubits needed = 2.47 × log(ℓ)  at depth 2ℓ
```

For our 530-step GCD: `2.47 × log(530) ≈ 23 qubits`. Our current GCD state machine uses ~22
qubits — already near the theoretical minimum. The remaining qubit costs (1152 total) come
from the transcript, passengers, and arithmetic scratch — not the GCD control logic itself.

### How the optimization techniques *are* pebble-game moves

This theory is not background decoration — **every qubit-freeing technique in §7–§9 is literally a
move in one of these two pebble games.** Naming the move tells you its exact cost and risk:

| Technique | Pebble-game move | Which game | Cost to "un-pebble" |
|-----------|------------------|------------|---------------------|
| Live-range hole (§7.1) | remove a pebble by **uncompute**, re-place it later by **recompute** | Bennett (classical-reversible) | full Toffoli, *twice* (uncompute + recompute) |
| Free-and-recompute cy0 (§7.5) | same, on one cheap pebble | Bennett | ~0 (a few CNOTs) |
| MBU / carry vent (§9.1–B) | remove a carry pebble by **X-measurement + CZ** | spooky (quantum) | **0 Toffoli** |
| Conditional replay (§9.3) | measure the pebble; recompute only on the branch that needs it | spooky (quantum) | `Pr[fire] ×` cost |
| HMR ghosting (§7.14) | remove a pebble by measurement, leave a **ghost**, recompute + phase-fix | spooky (quantum) | one recompute |
| Transcript compression (§7.8) | **don't pebble it** — shrink the data so fewer pebbles must persist | (takes the value *out* of the game) | codec only |
| Parallel GCD schedule (§13) | optimal pebble *placement* over the 530-step chain | parallel spooky | — (already optimal) |

**The Bennett→spooky upgrade is the single biggest constant-factor lever.** Compare the first two
rows against the MBU row. A live-range hole (§7.1) is a *Bennett* move: to free a pebble you
uncompute it (paying its Toffoli) and later recompute it (paying again) — the classical-reversible
game, where un-pebbling is expensive. MBU (§9.1) is the *spooky* move applied to the same kind of
pebble: you remove it by **measuring** it, and a measurement is free of Toffoli. That is precisely
why an n-bit adder drops from ~2n Toffoli (compute + coherent uncompute) to ~n (compute +
measured uncompute) — **MBU is the pebble game's quantum advantage cashed out on every carry bit.**

**Pebbling theory also tells you *which* qubits to attack and which to leave alone.** The
recompute-to-free move only pays when `recompute_Toffoli < qubits_freed × break_even` (§10). Plug the
two extremes into that rule:

- **The transcript is firmly in the "never recompute" regime.** Bennett's exponentially-growing
  constant is exactly why: re-deriving it would cost ~3.8M Toffoli to free ~370 qubits (the example
  above) — ~8× over break-even. So you must take it *out* of the pebble game entirely by
  **compressing the data** (§7.8, the base-5/K5 codecs), not by recomputing it.
- **A scratch pebble like `cy0` is deep in the "always recompute" regime.** It is a cheap function
  of live qubits, so recompute costs ~0 Toffoli — free it without hesitation (§7.5).

And the parallel-spooky bound says the **GCD control chain is already done**: ~22q vs the
`2.47·log(530) ≈ 23q` floor leaves no room. So the theory directs every remaining qubit lever at the
**data pebbles** — transcript, passengers, coordinate registers — which is exactly where §7 and §13
spend their effort. In short: pebbling theory is the map that says *recompute the cheap pebbles
(Bennett), measure the carry pebbles (spooky), compress the expensive data instead of pebbling it,
and stop optimizing the control chain.*

---

## 13. The SOTA Circuit: How trailmix_ludicrous Works

### The decisive architectural choice: Q is classical

The second point `Q = (Qx, Qy)` is kept as classical `BitId` values, not quantum registers.
Materialized into a transient quantum temp **only** at off-peak coordinate steps, then freed.
This eliminates 512 qubits from the peak — by far the biggest single qubit reduction ever.

A naive design that kept `Q` as resident quantum registers would add 512 qubits live across
the entire GCD peak.

### Two GCD passes sharing one tape

The affine point addition needs:
1. `λ = dy × dx⁻¹ mod p` — inverse GCD (drive `(p, dx)` → `(1, 0)`)
2. `new_y_component = λ × (Px − new_Px) mod p` — forward GCD (drive `(p, new_dx)` backward)

Both share **one** modular-inverse engine and **one** dialog tape (transcript). The forward
and reverse GCD passes are the same circuit running in opposite directions.

This avoids having two separate inversion circuits, saving both qubits (one shared tape) and
Toffoli (shared codec overhead).

### The base-5 codec: 772 → 603 qubits live

At each of 257 divstep steps, the algorithm records `(subtracted, swap, s₂)` — 3 bits raw.
But only 5 of 8 possible 3-bit patterns are reachable from the GCD dynamics. Triple windows
of 3 consecutive symbols have `5³ = 125` reachable states, encoded in `7` bits instead of `9`:

```
Layout: 1 Step0 (2b) + 85 Triples (7b each) + 1 Pair tail (5b) + 1 t1 flag (1b) = 603 qubits
```

The SAT-synthesized reversible codec maps the 25 valid 2-symbol pairs to 25 distinct 5-bit
codes, with the terminal AND-uncompute vented (0 Toffoli). Triple codec adds via affine normalization.

### The vented-adder zoo

Every adder in `trailmix_ludicrous` vents its carry-uncompute via MBU:
```rust
hmr(carry, bit);       // X-basis measurement, 0 Toffoli
cz_if_bit(a, b, bit);  // phase correction conditioned on measurement
```

The adder family dispatches per-call by baked schedule tables:
- Plain Gidney AND-carry
- Variable-chunk (varchunk)
- Headroom-adaptive (√n-chunk → chunked-then-Cuccaro tail)
- Fused `double+cdouble` combining `y := 2(1+s₂)·y mod p` with one shared reduction

Each call's vent budget: exactly `TLM_TARGET_Q − active_qubits`, spending every spare qubit
below the ceiling on Toffoli savings.

### The deliberate island-exact components

trailmix_ludicrous includes calibrated island-exact approximations:
- **Low-54-bit +f fold** (`LSBS = 54`): reduction folds touch only low 54 bits; carry beyond
  bit 53 is dropped with probability ~`2^(−21)` per fire.
- **Narrow-top-window comparators** (`MSBS = PAD = 21`): swap predicates scan only the top 21
  bits. Mis-decision probability ~`2^(−21)` per call.

`PAD = 21` is the master knob for these. These are safe under the 9024-shot verifier because
independent ~`2^(−21)` per-fire divergences keep the expected failing-shot count under tolerance.

### Where 1152q comes from

At the SOTA (d44cad3):
- **603q**: compressed base-5 GCD transcript (live during both GCD passes)
- **512q**: two 256-bit coordinate registers (quantum P.x, P.y)
- **~37q**: transient carry/vent ancilla at the peak-binding fold operations

The co-binder plateau at 1152q spans the forward-multiply GCD apply, the inverse GCD apply,
and boundary-carry phases at the peak.

---

## 14. The Three Tracks: Score, Low-Qubit, and Pareto Frontier

The challenge has three distinct objectives (§2), and each has its own history and its own winning
constructions. This section walks all three: the **score track** (minimize Q×T), the **low-qubit
track** (minimize Q alone), and the **Pareto-frontier track** (map the clean (Q, T) curve).

### The score track (Q×T): the 2715q→1152q journey

The score track has three clearly distinct eras, each defined by its **inversion engine**: the
Kaliski pre-history, the dialog-GCD frontier (which stalled at a 1168q wall for days), and the
*ludicrous* breakthrough that broke it and drove to today's SOTA.

#### Era 1 — Pre-history: 2715q → 1698q (the Roetteler/Kaliski era)

The challenge *started* at a baseline of **2,715 qubits × ~3.96M Toffoli**: a **Roetteler-style
two-Kaliski affine** point addition — affine coordinates (not projective), the modular inverse done
by *two* runs of the Kaliski binary-GCD algorithm, direct/Solinas reduction (no Montgomery), with the
prime and `Q` known as compile-time constants. The inverse was ~80–90% of the Toffoli (the bottleneck
§4 names), and was treated as algorithmically fixed — so the early drops were *all* live-range and
hosting tricks, the same methods in this primer appearing in cruder form:

- **2708 → ~2002 (scratch-packing on a fixed inverse):** the `cswap(p⊕q)` swap-merge (§9.19, −274k
  Toffoli), borrowing **provably-`|0⟩` high bits of the shrinking GCD register** as carry scratch
  (gate-hosting §7.16 in its first form, reaching the published "9n" peak floor), square-recompute
  eviction (§7.1), and **joint-pin plateau breaking** (§7.9) — the realization, present from the very
  start, that a peak co-owned by several scratch clusters only drops when you reduce all of them
  *together*.
- **2002 → 1698 (the engine swap):** the first true *architectural* jump replaced the entire Kaliski
  stack with a **dialog-GCD inverter that streams a compressed transcript** (§3) instead of holding
  wide history registers resident — a single change worth −304 qubits, and the lineage everything
  after descends from.

#### Era 2 — The dialog-GCD frontier: 1698q → 1168q (and the wall)

On the dialog-GCD engine the peak fell steadily via the **windowed/chunked apply** dial (§7.18, the
era's biggest peak lever), carry self-hosting on the operand lanes (§7.13/§7.16), shift-free modular
doublings (§7.19), keep-live-vs-recompute in the Solinas fold (the keep-alive dual, §7.1), the first
**recompute-to-free fold carries** (`FOLD_FREED_TAIL` / `FOLD_PARK_LOW_CARRIES`), and progressively
tighter transcript codecs:

| Transition | Technique | What was released |
|-----------|-----------|-------------------|
| 1698→1211 | windowed apply + recompute-to-free + carry self-hosting | the whole 1698→1211 descent (§7.18/§7.13/§7.19/§7.1) |
| 1211→1193 (−18q) | Live-range hole (§7.1) | GCD-apply scratch block freed during shift sub-phase; reacquired after |
| 1193→1192 (−1q) | Truncation / segmentation (§7.4) | Square segment one notch tighter |
| 1192→1185 (−7q) | Transcript codec (§7.8) | Per-step fold carry scheduling + exact 11-bit head codec |
| 1185→1170 (−15q) | Plateau decomposition (§7.9) + 5 techniques | Coordinated: tail codec, streaming apply, square rebalance, 5 co-binders |
| 1170→1169→**1168** | MBU vent on fold carry (§9.1/2) | `hmr+cz_if` on the −f fold peak owner: 0 Toffoli to vent it — and then **the wall** |

**The 1168q wall.** The dialog-GCD frontier reached 1168q (BitWonka, 6/15) and *stuck there for
days*. Every remaining lever on that engine was a single-qubit grind against a hard floor: with the
two 256-bit `Q` coordinates materialized as resident quantum operands across the GCD peak, the
architecture simply had no more room. Breaking 1168 needed a different circuit, not another knob.

#### Era 3 — The *ludicrous* breakthrough: 1167q → 1152q

On 6/18 **tob-joe (Trail of Bits), `af5abb1`**, broke the wall by porting trailmix's **"ludicrous"**
point-add — *a new circuit family, distinct from dialog-GCD* — onto the challenge. It landed at
**1167q × 1,422,591** (only −1q below the wall on day one), but the point wasn't the −1q: it opened a
**fundamentally lower-headroom family** that the dialog-GCD line could not reach, and over the next
days drove to 1152. Its design (the architecture §12 describes in full):

- **The decisive lever — `Q` classical *and off-peak* (−512q).** Hold both 256-bit `Q` coordinates as
  *classical* registers and load them into a transient quantum temp **only at off-peak coordinate
  steps**, so all 512 of those qubits never co-reside at the GCD peak. (Earlier circuits knew `Q` was
  a constant but still paid for it as resident quantum operands at the peak; ludicrous is what finally
  kept it off — tob-joe's note calls this "the decisive product-min lever.")
- **One shared inversion, two passes.** The whole add is two GCD passes sharing one modular-inversion
  primitive (`Direction::{Inverse, Forward}`), a fused square-subtract for `λ²`, and a zero-Toffoli
  negate `ox − x2 = −(x2 − ox)` (§9.9).
- **Schrottenloher jump-GCD (jump=2, 258 steps).** Each forward step records a 3-bit dialog symbol
  `(subtracted, swap, s₂)`; the reverse replays it. The GCD registers **shrink and regrow along a
  baked width schedule**, running the adders in the freed headroom — this sets the 1167q floor and is
  the primary lossy lever.
- **All-triple base-5 codec** (§7.8): 3 jump-2 symbols (9 raw bits) fold into a 7-bit code (only 5 of
  8 patterns reachable; `log₂(5³) ≈ 6.97`), from a SAT-synthesized in-place pairs core — tighter than
  the earlier K5 15→12 codec.
- **Inline interleaving + streamed decompression:** each window is compressed the instant its symbols
  are produced, so the full raw tape never exists (resident **603q vs ~775 raw**); the reverse pass
  decompresses one window at a time, and the apply is fused *into* the GCD passes, not a separate phase.
- **A vented-adder zoo on baked per-call schedules** (§9.2): plain / variable-chunk / headroom-adaptive
  / chunked-Cuccaro / carry-out adders plus a fused `double+cdouble` `(e+2d)·f` fold; for each of the
  ~258×2 calls the adder choice, carry cap, vent count and chunk split are replayed from baked tables
  sized for that call's live-qubit position — not a live cost model.
- **Deliberate exact-modular truncations:** the `+f` fold touches only the low 54 bits (~2⁻²¹ miss)
  and the swap comparators recompute on a narrow top window — bounded rare errors for large savings
  (§9.18, §11). Everything is baked, so `build()` is deterministic and a tail nonce (28565) is ground
  to land all 9024 shots clean.

From that base the trailmix_ludicrous line ground down to the SOTA:

| Transition | Technique | What was released |
|-----------|-----------|-------------------|
| 1167→1166 | Step-0 swap_flag elimination | `swap_flag` becomes `Option<QubitId>`, lazy-alloc; freed one tape lane |
| 1166→1165 | Odd-u0 parking (§7.1) | `u[0]` is provably 1; park+loan the lane, restore in 2 gates |
| 1164→1163 | Source-as-carry suffix | Paid drop: surrendered apply-phase vents to free one carry lane |
| Toffoli: −22.4M | Karatsuba square (§9.6) | 3 sub-squares instead of 4 |
| Toffoli: −1.33M | GAP_J2 narrowing (§9.11) | 22-line per-step comparator table edit |
| Toffoli: −377k | Constprop deeper (§9.16) | `CONSTPROP_MAX_ITERS` 16→256 |
| 1163→1159→1156 | Headroom clamp returns (§7.10 + shelved-lever rule §10) | Same clamp that lost early now wins on the cheap Karatsuba+dead-CCX base (~527 T/qubit) |
| 1156→1153 | Clamp + zero-cin fold + FFG cap (§7.10), paid by cinc (§9.17) + iterated dead-CCX (§9.8) | Qubit drop alone cost +11,369 avgT (rejected); Toffoli levers stacked back to win → SOTA at the time |
| **1153→1152** | Free-and-recompute cy0 (§7.5) | `cy0 = ctrl & !a0`; loan lane for 40 binding folds |
| Structural | 6dafa07 pivot (§9.8/§11) | Replaced empirical dead-CCX with ~15 structural predicates |

**Key meta-lessons**:

1. **Every "floor" fell to a better encoding or a better question.** Not always a new algorithm —
   often a denser codec or the question "whose value is a cheap function of live qubits?"

2. **The shelved-lever rule is real.** The 1157q clamp tried early and lost; won after Karatsuba.

3. **Plateau mode is the endgame.** The final qubit drops each required coordinated packages of
   4–9 independent local reductions applied simultaneously.

4. **Structural correctness wins over island-exact tricks.** The 6dafa07 pivot to structural dead-CCX
   eliminated the empirical approach entirely — correct for all inputs, not just the 9024.

### The low-qubit track: the Shrunken-PZ inversion (§2, track 2)

#### What the Shrunken-PZ approach is (the backbone of this track)

Almost every record on the low-qubit track is built on one architecture, **Shrunken-PZ**
(Proos–Zalka). It is worth understanding as a whole, because it is a *fundamentally different
inversion engine* from the ludicrous/dialog-GCD circuit that holds the product SOTA — different
module, different objective, sharing only the problem statement (`P += Q`).

**The core idea.** Where the ludicrous track records a small **decision tape** and replays it (§4
dialog transcript), Shrunken-PZ runs the **Proos–Zalka binary-GCD / Kaliski divstep inversion
directly as a bit-by-bit reversible state machine** — no big transcript. It carries the actual
Euclidean state in **five working registers** and *resizes them every step*:

| register | meaning | width over the 530 steps |
|----------|---------|--------------------------|
| `A`, `B` | the two running GCD magnitudes | start 256, **shrink toward 1** as the GCD converges |
| `CA`, `CB` | the two Bézout cofactors (the inverse accumulators) | start 1, **grow toward 256** |
| `Q` | the per-step quotient | small, ~21–25 bits |

**Why the peak is in the middle, and why register sharing fits.** `A,B` shrink while `CA,CB` grow,
so the qubit peak is not at either end — it is at the **GCD crossover** (~step 363), where both pairs
are mid-sized. The peak width is

```
peak ≈ 2·max(|A|,|B|) + 2·max(|CA|,|CB|) + |Q| + FIXED(~267)
```

At the crossover this is `[81,81,248,248,23] = 681` working bits + ~267 fixed (the 256-bit
coordinate passengers, modulus, sign/parity, counter, comparator scratch) = **948 qubits**. Crucially
`A` and its cofactor `CA` are **complementary in size** (one shrinks exactly as the other grows) —
which is precisely what makes EEA register sharing (§7.15) able to pack `A∥CA` into one word and push
toward 851/829.

**The levers that define the track** (each is a §7 technique, here applied to the divstep machine):
- **Dynamic-width registers (§7.6)** — resize `A,B,CA,CB` per step; free known-zero high bits.
- **CLZ-context window narrowing** — the divstep arithmetic only touches bits above a provably-zero
  low region, so each op runs over a narrowed window `[lo..len)`. The "robust width envelope" projects
  the tightest per-step window that still covers all sampled inputs — the qubit-side twin of empirical
  dead-CCX (§9.8), and equally **island-exact**.
- **Known-constant teardown (§7.7)** — at convergence `A=0, B=1, CA=p, Q=0` are constants; XOR them
  out (0 Toffoli) before the λ multiply so they don't co-reside with it.
- **Passenger ghosting (§7.14)** — HMR-ghost `dy`/`λ` so only one 256-bit coordinate co-resides with
  the EEA peak (+256, not +512).
- **Pipelined two-quotient divstep** — build the *next* quotient while draining the *previous*, so the
  quotient record stays ~26 bits instead of a full 256-bit tape.
- **EEA register sharing (§7.15)** — the deepest lever; packs operand and cofactor, reaching 851/829q.

**Why it is the qubit backbone but not score-competitive.** Running full per-step modular arithmetic
*without* the transcript-replay and Karatsuba machinery makes the divstep inversion inherently
gate-heavy: ~33–55M Toffoli at 948–980q (~40× the ludicrous SOTA's 1.36M), and ~460M at 851q. So
Shrunken-PZ maps the **qubit floor** (objective 2) but loses the **product** by a wide margin — a
qubit-lower-bound witness, not a contender on score.

#### The record ladder

Running *alongside* the Q×T product-SOTA journey above is this separate **low-qubit competition**
line — the Shrunken-PZ family — whose objective is to minimize peak qubits with Toffoli
unconstrained:

| Qubit record | Technique | Notes |
|--------------|-----------|-------|
| 1050q | trailmix shrunken-PZ embedded op stream | early low-qubit route |
| 1019q | source-level dynamic-width PZ port | |
| 988→956q | dirty-borrow / gate-hosting lever stack | |
| 952→948q | further lane borrowing + thin schedule | lowest *fully-validated* circuit witness |
| **851q** (`e7dd3de`, 6/23) | **EEA register sharing (§7.15), Luo 2026** | **−97q; the register-sharing breakthrough** |
| 829q (`1dd61ca`, 6/24) | more borrowing/relocation on a frozen envelope | current low-qubit frontier |

These are records on the **pure-qubit objective**, where the ~400–500M Toffoli they spend simply
does not enter the scoring. The 851q and 829q figures come from an analysis-oracle accounting
(§7.15) — read them as the leading **lower-bound witnesses** for the qubit floor; the 948q route is
the lowest fully-validated circuit on the track. This is a *different game* from the Q×T product SOTA
(1152q × 1.36M, value-exact): more qubits but ~340× fewer Toffoli. The two minima are reached by
different constructions, and which one is "best" depends entirely on which competition you are
entering — see §7.15 and §10.

### The Pareto-frontier track: clean (Q, T) basis circuits 1153q → 1133q (§2, track 3)

The third track (§2, objective 3) maps the **(Q, T) Pareto frontier** below the 1153q SOTA as a
sequence of **clean, dead-CCX-free basis circuits** others can fork. "Dead-CCX-free" is the precise
claim: every rung hard-sets `DROP_DEAD_ROBUST_DISABLE=1`, omitting the most overfit lever (whose
hard-coded gate-index `.idx` lists are tied to one exact op stream, §11) — that omission is what keeps
the basis *reusable*. They are **not fully value-exact**, however: each still carries the route's
standard calibrated **approximations** (comparator-width narrowing §9.18, carry truncation §7.4, and
at the lowest rungs **active-width trimming** §11) that are island-exact and require a per-rung nonce
hunt. So treat the curve as a *cleaner, more forkable* reference than a dead-CCX-stacked SOTA, not as
an all-inputs-provable bound.

Unlike the low-qubit witness track above, these stay in the **useful corner** — every point beats the
published *single point-addition* estimate on *both* axes: **q < 1175** and **T ≈ 1.37–1.46M,
comfortably under the ~2.69M (2²¹·³⁶) Toffoli** of the Babbush space-optimized secp256k1 point-add
(Schrottenloher 2026, Table 1). So the whole curve clears the bar with ~20–40 qubits and roughly 2×
Toffoli to spare. They are "rejected" on the Q×T product *by construction* (they trade qubits down for
Toffoli up); the deliverable is the exchange *curve*, not a score.

| q | T_clean | clean exchange vs prev | new lever introduced |
|---|---------|------------------------|----------------------|
| 1153 | 1,392,603 | — (anchor, dead-CCX off) | — |
| 1147 | 1,396,769 | −694 T/q | fold-vent clamp (`TLM_FOLD_CALL_CODE_OVERRIDES`) |
| 1146 | 1,408,582 | −11,813 T/q | graduated→dirty carry-in (`TLM_GRAD_DISABLE`) |
| 1143 | 1,411,643 | −1,020 T/q | codec scratch reuse + direct-dirty fold ctl |
| 1142 | 1,415,790 | −4,147 T/q | pair-raw codec last-k + tighter layout search |
| 1141 | 1,423,723 | −7,933 T/q | no-ancilla/dirty body + constant-lane loan family |
| **1133** | **1,460,511** | **−4,599 T/q** | **GCD active-width trimming** + fold-cout drop |

The qubits sort by exchange rate into four lever classes: **fold-vent clamping** (the cheap qubits —
clamp a peak fold's measured-vent windows, §9.2), **no-ancilla / dirty-borrow substitution** (convert
a carry ancilla into Toffoli, cf. §7.13), **constant-lane loan + recompute** (the Bennett pebble move
on provably-constant GCD low bits, §7.1/§12), and — new at 1133 — **GCD active-width trimming**: per-step
shrinking of the live GCD operand width in the convergence tail (`TLM_GCD_ACTIVE_WIDTH_TRIM=3` after
step 205), the dynamic-width-register idea (§7.6) applied to the ludicrous GCD. The 1133 rung is a
*value-exact repair* of an over-aggressive 1131 attempt: trimming the active width is a **graded**
correctness lever (§6) — push until the residual breaks, then give back one notch (1131→1133) so a
clean nonce is reachable. The push also introduced a reusable general pass — **reset-bounded qubit-id
compaction** (§7.17). Full analysis: [`pareto-frontier-push.md`](https://github.com/jieyilong/ecdsafail_skills/blob/main/ecdsafail-circuit-optimization/references/pareto-frontier-push.md).

---

## 15. Open Frontiers

### Density-neutral Toffoli cuts not yet applied

1. **Gidney 2025 streaming vented adder** (arXiv:2507.23079): Uses 2 clean + (n−2) dirty
   ancilla for ~3n Toffoli. Partially implemented in `venting.rs` but **leaks phase** — dirty
   ancilla phase corrections are incomplete. Expected ~n/4 Toffoli savings per adder once fixed.

2. **Apply-swap structural dead-CCX**: The GCD apply-step `cswap` block (~256 cswap per iter ×
   258 iters × 2 passes) has NO per-bit structural-dead skip — only whole-iteration skip. Porting
   the structural-dead analysis to these operations is a high-priority open lever.

3. **Extended Cuccaro structural dead-carry**: Currently checked for call indices 13–37 only.
   Extending to ALL Cuccaro adder call sites would save proportionally more.

4. **Apply-swap involutory pair cancellation**: The forward GCD-swap and the immediately following
   GCD-cswap on the same (u/v) lanes may cancel algebraically (swap twice = identity). Not yet
   checked structurally.

5. **Windowed arithmetic / QROM lookup** (Gidney 2019, arXiv:1905.07682) — *the biggest untried
   structural lever.* A multiply-by-a-quantum-value normally does `2^w` controlled add-shifts. The
   windowed trick reads a **`w`-bit window** of the multiplier and uses it to **address a QROM table
   lookup** that adds the precomputed partial product in one shot — turning `2^w` controlled adds
   into one table read. The Bézout-reconstruction multiplies (§4) are ~90% of the Toffoli, so if
   they admit a windowed/QROM form it is the largest single cut on the board. Open question: whether
   the in-circuit, *value-dependent* reconstruction multiply can be windowed the way the
   fixed-base `k·G` scalar mult already is.

### Density-neutral qubit cuts not yet applied

1. **The co-bind plateau at 1152q**: Multiple independent phases all tie at 1152q. Each needs a
   local reduction before the global peak drops. Challenge: finding compatible local reductions for
   all co-binders simultaneously.

2. **FFG cy0-style recompute on other binders**: The cy0 trick (§7.5) worked because `cy0` was
   a cheap function of live qubits. Other binder qubits may have similar cheap-function properties
   not yet identified.

3. **SumHiLo/shifted vents** (`TLM_SQUARE_SUMHILO_VENT`, `TLM_SQUARE_VENT_SHIFTED`): Exist in
   the codebase as default-OFF options. Off-peak phases could enable these for free Toffoli savings.

---

## 16. Quick-Reference Summary Tables

### Qubit reduction techniques

| Technique | Qubits saved | Toffoli cost | Density-neutral |
|-----------|-------------|-------------|-----------------|
| Live-range hole (§7.1) | k qubits | +2 × compute(V) | YES |
| Passenger relocation (§7.2) | k qubits | 0 | YES |
| Range-bound guard removal (§7.3) | 1 per register | 0 | YES |
| Truncation (§7.4) | varies | 0 | PARTIAL |
| Free-and-recompute cheap value (§7.5) | 1 | ~0 (CNOTs only) | YES |
| Dynamic-width registers (§7.6) | varies | small | PARTIAL |
| Known-constant teardown (§7.7) | k | 0 (CNOT = Clifford) | YES |
| Transcript compression (§7.8) | varies | decode overhead | YES |
| Plateau decomposition (§7.9) | 1 (global) | combined cost | YES |
| Dynamic headroom clamp (§7.10) | 1 per ceiling drop | small | YES |
| Lazy carry liveness (§7.11) | 1/chunk | 0 | YES |
| In-place decode (§7.12) | varies | codec overhead | YES |
| Borrowed-carry fusion (§7.13) | k | 0 | YES |
| HMR ghosting / passenger ghosting (§7.14) | 256 | +1 modular multiply | YES |
| EEA register sharing (§7.15) | ~97–119 (to 851→829q) | high (irrelevant to low-qubit objective) | YES — for the low-qubit competition (§2) |
| Gate-hosting (§7.16) | 1 per hosted gate | 0 (clean) / +1 Tof (dirty) | YES if host-zero *proven*; island-exact if *sampled* |
| Reset-bounded id compaction (§7.17) | gap (max-id − true peak) | 0 | YES (relabels wires only) |
| Windowed/chunked materialization (§7.18) | many (the `F_CUT` dial) | +few (boundary comparators) | YES |
| Shift-free modular doublings (§7.19) | ~24 (drops spill+flags) | +few | YES |
| GCD active-width trim (§7.6 applied) | varies (deep tail) | small | PARTIAL (graded; nonce-hunted) |

### Toffoli reduction techniques

| Technique | Toffoli saved | Qubit cost | Density-neutral |
|-----------|--------------|------------|-----------------|
| MBU / carry vent (§9.1/2) | 1 per vent | +1 temporary | YES |
| Conditional replay (§9.3) | (1−f) × block cost | 0 | YES |
| Algebraic fusion (§9.4) | varies | 0 | YES |
| Witness-first dataflow (§9.5) | ~13M / instance | 0 | YES |
| Karatsuba square (§9.6) | ~22M (one change) | 0 | YES |
| NAF recoding (§9.7) | ~5–10% of constant-fold cost | 0 | YES |
| Pseudo-Mersenne reduction (§9.18) | huge (15% vs 34% of CCX) | 0 | YES (fold); PARTIAL (lsbs/msbs trunc) |
| Merge adjacent controlled-swaps (§9.19) | n per merged pair (−274k once) | 0 | YES |
| Structural dead-gate skip (§9.8) | varies | 0 | YES |
| Classical constant ops (§9.9) | significant | 0 | YES |
| Converged-tail elision (§9.10) | ~hundreds/iter × K iters | 0 | NO |
| GAP_J2 narrowing (§9.11) | ~1.33M / 22-line change | 0 | NO |
| Ancilla-free majority (§9.12) | 1 per majority | 0 | YES |
| Exact-adder recovery (§9.13) | ~2,600 / call | 0 | YES |
| Redundant cleanup skip (§9.14) | varies | 0 | RISKY |
| Off-peak loosening (§9.15) | free refund | 0 | YES |
| Constprop deeper (§9.16) | ~377k | 0 | YES |
| Cinc cascade replacement (§9.17) | ~5,175 (O(t²)→O(t)) | 0 | YES |
| Empirical dead-CCX drop (§9.8) | ~13,000+ (1st pass) | 0 | NO (island-overfit) |
| Iterated 2-pass dead-CCX (§9.8) | ~2,400 / extra pass | 0 | NO (island-overfit) |

### Key theoretical results

| Result | Source | Insight |
|--------|--------|---------|
| MBU: uncompute AND for 0 T-gates | Jones 2013 (Phys Rev A), Gidney 2018 (arXiv:1709.06648) | X-measurement + CZ = free uncompute |
| 1 Toffoli = exactly 7 T-gates | Gosset et al. 2013 (arXiv:1308.4134) | Tight lower bound |
| Bennett classical pebbling | Bennett 1989 (SIAM J. Comput. 18:4) | Classical: exponential constant in space savings |
| Quantum spooky pebbling | Kornerup, Sadun, Soloveichik 2021 (arXiv:2110.08973) | Quantum: polynomial constant (exponential advantage) |
| Parallel spooky pebbling | Kahanamoku-Meyer et al. 2025 (arXiv:2510.08432) | 2.47×log(ℓ) qubits for ℓ-step chain |
| Conditionally-clean ancilla | Khattar & Gidney 2024 (arXiv:2407.17966) | 3n Toffoli MCX with log*n clean ancilla |
| Conditionally-clean (co-discovery) | Nie, Zi & Sun 2024 (arXiv:2402.05053) | Independent discovery, Feb 2024 (5 months earlier) |
| secp256k1 *full ECDLP* frontier | Babbush, Gidney et al. 2026 (arXiv:2603.28846) | ≤1200q / ≤90M Toffoli for the whole Shor run (~28 windowed PAs) |
| secp256k1 *single point-add* (the challenge unit) | Babbush space-opt, via Schrottenloher 2026 Table 1 (arXiv:2606.02235) | **1175q / 2²¹·³⁶ ≈ 2.69M Toffoli** (the "useful corner" bar); Schrottenloher space-opt = 1192q / 2²¹·¹⁹ ≈ 2.39M |
| Karatsuba algorithm | Karatsuba & Ofman 1962 | O(n^1.585) vs O(n²) for multiplication |
| EEA register sharing (origin) | Proos & Zalka 2003 (arXiv:quant-ph/0301141) | Inversion dominates point-add space; operand+cofactor packing |
| Compact exact reversible inversion | Luo et al. 2026 (arXiv:2604.02311) | 3n + 4⌊log₂n⌋ qubits (1333q, n=256) via bit-length-tracked register sharing |
| DQI "Dialog" in-place EEA multiply (§4) | Khattar, Shutty & Gidney 2025 (arXiv:2510.10967) | construct/reconstruct split; (y,0) seeding fuses inverse+multiply, no explicit inverse |
| Windowed arithmetic / QROM (§15) | Gidney 2019 (arXiv:1905.07682) | 2^w controlled adds → one w-bit-window table lookup |

---

*See also* — these detailed reference docs live in the GitHub repo
**[github.com/jieyilong/ecdsafail_skills](https://github.com/jieyilong/ecdsafail_skills)**, under
`ecdsafail-circuit-optimization/references/`:
- [`density_neutral_tradeoffs.md`](https://github.com/jieyilong/ecdsafail_skills/blob/main/ecdsafail-circuit-optimization/references/density_neutral_tradeoffs.md) — detailed technique catalog with exchange rate math
- [`gidney-techniques.md`](https://github.com/jieyilong/ecdsafail_skills/blob/main/ecdsafail-circuit-optimization/references/gidney-techniques.md) — Gidney's full lever catalog with blog/paper pointers
- [`external-literature-2000-2026.md`](https://github.com/jieyilong/ecdsafail_skills/blob/main/ecdsafail-circuit-optimization/references/external-literature-2000-2026.md) — broader academic literature map
- [`REPORT_1168_wall_revamp.md`](https://github.com/jieyilong/ecdsafail_skills/blob/main/ecdsafail-circuit-optimization/references/REPORT_1168_wall_revamp.md) — the trailmix_ludicrous introduction and burst analysis
- [`frontier-1211-to-1170.md`](https://github.com/jieyilong/ecdsafail_skills/blob/main/ecdsafail-circuit-optimization/references/frontier-1211-to-1170.md) — detailed 1211→1170 step-by-step record
- [`pareto-frontier-push.md`](https://github.com/jieyilong/ecdsafail_skills/blob/main/ecdsafail-circuit-optimization/references/pareto-frontier-push.md) — the (Q,T) Pareto-frontier push (§14.3)
- [`SHRUNKEN_PZ_q948_track.md`](https://github.com/jieyilong/ecdsafail_skills/blob/main/ecdsafail-circuit-optimization/references/SHRUNKEN_PZ_q948_track.md) — the low-qubit Shrunken-PZ track (§14.2)

> **Note on code paths.** Source files named in this primer (e.g. `arith.rs`, `fused.rs`,
> `register_shared_eea.rs`) refer to the **ecdsa.fail challenge circuit** — the `trailmix_ludicrous`
> / `trailmix_port` modules — which is pulled per-submission via the `ecdsafail` CLI
> (`ecdsafail reset <submission>`); they are *not* part of this docs repo.
