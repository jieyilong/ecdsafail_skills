# Craig Gidney — Techniques Catalog (for ECDSA Fail point-add)

Craig Gidney (Google Quantum AI) is the most relevant single author for this benchmark: he
authored the temporary-AND, windowed arithmetic, conditionally-clean ancillae, the DQI
"Dialog" (the EEA-split our `dialog-GCD` descends from), and the secp256k1 frontier estimate.
Many of his sharpest *practical* tricks live only on his blog **algassert.com**, not in papers.

Built by `/expert-autoresearch` (2 Gidney angles). Durable record: `research/index.json`
(99 entries), `research/papers/` (PDFs), `research/search_results/gidney_*.json`. Each entry:
**technique** — *source* — **how it maps to our route.**

---

## A. Toffoli/T primitives (apply-phase modular arithmetic)

- **Temporary logical-AND** — *1709.06648 + blog "Verifying Measurement-Based Uncomputation"*.
  Compute an AND/Toffoli with **4 T**; **uncompute with 0 T** via an X-basis measurement + a
  classically-controlled CZ fixup. The uncompute is *free*. Rule: **every paired
  compute/uncompute AND in our adders/comparators must use this** (it already underlies them).
- **The "adder hides a CCZ" floor** — *blog "Producing an N+1 Qubit CCZ State with an N Qubit
  Adder" (2019)*. An n-bit adder contains a hidden (n+1)-qubit CCZ, and must consume **≥ n−1 CCZ
  (Toffoli) states**. This is a **hard magic-state lower bound** on any adder-based block — use it
  as a sanity check: if a proposed Toffoli cut would push an adder below ~n−1 CCZ, it's wrong
  (it's hiding the cost elsewhere or breaking correctness).
- **Windowed quantum arithmetic** — *1905.07682*. Replace `2^w` controlled add-multiplies with a
  **single QROM table lookup addressed by a w-bit window** of the multiplier — the dominant Toffoli
  cut for modular multiplication in factoring. Our fixed-base `k·G` comb is the lookup-table idea
  for *scalar mult*; the open question is whether the **in-circuit Bézout-reconstruction multiplies**
  (the 90%-of-Toffoli apply phase) admit a windowed/table form. High-value to investigate.
- **Constant-workspace classical–quantum adder** — *2507.23079 (2025)*. In-place add of a *classical*
  constant, **3n–4n Toffoli, O(1) clean ancilla, free to control**. Directly applicable to the
  **Solinas/pseudo-Mersenne constant folds** and any add-a-constant modular reduction in our route.
- **Phase-gradient / proxy / computed phasing** — *blog 2016–2017 ("Gradients into Additions into
  QFTs", "Efficient Controlled Phase Gradients", "Proxy/Computed Phasing")*. Add into a prepared
  phase gradient to apply many rotations cheaply; compute a predicate into an ancilla, phase it,
  uncompute → structured phasings cost only compute+uncompute. Our route is Toffoli-based so this is
  mostly orthogonal, but the **compute-phase-uncompute** pattern is exactly the host-gated/measured
  lever, and worth knowing if any step is reformulated with phase encodings.
- **Control/target duality, SWAP=3·CNOT, relabel-don't-move** — *blog 2017 ("Thinking of Operations
  as Controls", "Breaking Down the Quantum Swap")*. Swap which wire is the control to **fuse gates**;
  a cswap is 1 CCX/bit; **relabel registers instead of physically swapping** them. The tobitvector +
  apply **cswaps are a large Toffoli chunk** in our route — these identities are the toolkit for
  attacking them (the existing cswap-floor analysis is this lens).
- **Large multi-controlled X / increment via borrowed dirty ancilla** — *blog 2015 ("Constructing
  Large Controlled NOTs", "...Increment Gates")*. C^n X in **O(n) Toffoli** down a ladder of
  *borrowed* bits; an n-bit +1 with **one borrowed dirty ancilla**. The borrowed-ancilla mindset
  behind our round84 dirty/vent tricks.
- **Multiplicative inverse mod 2ⁿ by reversing the multiply** — *blog 2017*. `K⁻¹ mod 2ⁿ` is free by
  running the multiply circuit backwards (high bits never carry into low). **Power-of-2 moduli only**,
  so *not* for the prime `p` — but relevant to any 2-adic/Montgomery sub-step.

## B. Qubit/ancilla & uncomputation (peak reduction)

- ★ **Conditionally-clean ancillae** — *Khattar–Gidney 2407.17966*. Borrow dirty bits **as if clean,
  with zero allocation and no toggle-detection** (Laddered Toggle Detection). The principled
  generalization of our `ROUND84_XTAIL` dirty/vented peak tricks — audit our borrowed-carry adders
  against it for a cleaner peak win than the hand-tuned `1309→1285` trade.
- **Spooky pebble games** — *blog 2019 ("Spooky Pebble Games and Irreversible Uncomputation")*.
  Remove a pebble (free an ancilla) *early*, leaving a 50/50 **"ghost"** to clean up later with a
  classically-controlled phase → reclaim qubits **before** uncomputation; a line graph drops to
  **S=3**. This is the scheduling theory behind our measured-cleanup / transcript-hosting; a DAG
  pebble solver could schedule our venting automatically.
- **Dirty-ancilla in-place arithmetic** — *1706.07884*. Borrowed-qubit ops (≈2× Toffoli for net-zero
  qubits) — quantifies the exact qubit↔Toffoli exchange we measured at `1309↔1285`.

## C. The DQI "Dialog" — the EEA-split our route descends from

- ★ **Verifiable Quantum Advantage via Optimized DQI Circuits** — *Khattar–Shutty–Gidney 2510.10967*.
  The **"Dialog"** decomposes the GCD/EEA execution trace into a sequence of small invertible **2×2
  transition matrices** — *implicit* Bézout coefficients **without carrying wide r,s registers**.
  This is exactly the idea Schrottenloher credits (the `[14]` in the existing skill notes) and our
  `dialog-GCD` is built on. Read it for the **in-place EEA construction** and to check whether it
  implements **jumpdivstep-style batching** (batching `T` steps into one matrix — the unexplored
  generalization of our `K2`/`ACTIVE_ITERATIONS` lever; see `external-literature-2000-2026.md` §1).

## D. ECC / factoring frontier + the cost model

- **Securing Elliptic Curve Cryptocurrencies** — *Babbush–Gidney–Boneh et al. 2603.28846 (2026)*.
  secp256k1 ECDLP at **≤1200 q / ≤90M Toffoli** or **≤1450 q / ≤70M Toffoli** — the published Pareto
  frontier our scored affine point-add ultimately answers to.
- **Spacetime-volume cost model** — *Gidney–Ekerå 1905.09749 (8h / 20M qubits)*; *2505.15917 (<1M
  qubits, <1 week — approximate residue arithmetic + yoked codes + cultivation)*; factories
  *1812.01238*; **magic-state cultivation 2409.17595**. Two takeaways: (1) Toffoli count is the cost
  because each consumes a distilled magic state; (2) **cultivation drops the per-Toffoli cost toward
  a CNOT**, which *shifts the balance toward idle-qubit/peak cost* — i.e. under modern FT the **qubit
  factor matters relatively more**, supporting peak-reduction work as much as Toffoli-cutting.

---

## Top Gidney levers to try on our route (ranked by fit)

1. **Windowed arithmetic on the in-circuit Bézout multiplies** *(1905.07682)* — the apply phase is
   ~90% of Toffoli; if those multiplies can be QROM-windowed, it's the biggest structural cut.
2. **Conditionally-clean ancillae** *(2407.17966)* — clean version of our round84 dirty/vent peak win.
3. **Constant-workspace adder** *(2507.23079)* — for the Solinas constant folds (O(1) ancilla).
4. **Spooky-pebble scheduling** — automate transcript hosting / measured cleanup at the peak.
5. **Adder-CCZ floor** *(blog)* — Toffoli lower-bound sanity check on any adder cut.
6. **DQI Dialog `2510.10967`** — read for in-place EEA + jumpdivstep batching of `K2`/`ACTIVE_ITERATIONS`.
