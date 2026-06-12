# External Literature Map (2000–2026)

Survey of the broader quantum-circuit-optimization literature beyond the TrailMix /
Schrottenloher route already covered in `SKILL.md`. Built by `/expert-autoresearch`
(6 parallel angles, 80 indexed candidates, 15 PDFs). Durable record:
`research/index.json`, `research/search_results/`, `research/papers/`.

Each entry: **technique** — *citation (arXiv/eprint)* — **how to apply / why it does or
doesn't fit our affine-PA + dialog-GCD route.** The two highest-value *new* directions for
our benchmark are flagged ★.

---

## 1. Inversion-algorithm frontier (the largest structural levers)

- ★ **jumpdivsteps / safegcd2 batching** — *Bernstein–Yang safegcd, eprint 2019/266 + secp256k1
  jumpdivsteps*. Batch `T` binary-GCD `divstep`s computed on the **low `k` bits only** into one
  `(k+2)`-bit 2×2 transition matrix, then apply that matrix to the **full-width** operands ~`n/T`
  times. This **decouples the iteration count from the number of full-width arithmetic ops** — the
  expensive part of our route is the full-width apply-cswap/add executed once *per recorded step*
  (`ACTIVE_ITERATIONS` × 256-wide). Our `K2` is the degenerate case (strip ≤2 trailing zeros per
  step); a true jump-`T` would record one matrix per `T` steps and do far fewer full-width applies.
  Caveat (consistent with our measured K3 loss): the matrix **decode/apply must be cheaper than the
  steps it replaces**, and the transcript stores a wider symbol per block — so the win is a
  transcript-width vs full-width-op trade. This is the most promising unexplored generalization of
  the lever we already win on.
- **divstep / branchless constant-time GCD** — *Bernstein–Yang 2019; Bos 2014 constant-time Kaliski*.
  The divstep folds all binary-GCD branches into `sign(δ)` + low bit of `g`, becoming a fixed small
  matrix — **branchless = exactly what reversibility requires** (no data-dependent control flow).
  ~724–741 divsteps bound for 256-bit. This is the theoretical backbone of why our recorded-transcript
  GCD is correct as a fixed-length unroll. Jin–Miyaji (SAC 2022) give a *fewer-iteration* divstep
  variant = a shallower reversible unroll.
- ★ **Inversion elimination via Legendre/Jacobi symbol** — *Chevignard–Fouque–Schrottenloher 2026
  (eprint 2026/280, EUROCRYPT); Jacobi Factoring Circuit 2412.12558*. In **projective** coordinates,
  compress the modular-inverse output to a **single bit** via a Legendre/Jacobi symbol (GCD-style
  reciprocity), removing the explicit inverse **and its full-width result register** → **1098 q
  (≈3.12n)** for 256-bit ECDLP, the current qubit-floor witness. Architecturally orthogonal to our
  dialog-GCD (which *computes* the inverse). It is a **moonshot for this benchmark** because the
  scored circuit is the *affine* point-add and needs the actual output coordinates, not a symbol —
  but it is the direction the qubit frontier is moving, and worth understanding before any
  projective/teardown attempt. (Note Huang 2502.12441, *withdrawn*: naive projective coords do NOT
  help because non-uniqueness reintroduces modular division — the Legendre trick is what sidesteps it.)
- **Compact exact reversible inversion at `3n + 4⌊log₂n⌋` qubits** — *Luo et al. 2026, 2604.02311*
  (1333 q for n=256). Tracks the **bit-lengths** of the shrinking `u,v` in small length-registers and
  uses "location-controlled arithmetic" on the active window. This is our `WIDTH_SLOPE`/variable-width
  register-sharing idea pushed to its exact-reversible extreme; mine it for peak-floor mechanisms.
- **Baselines / provenance**: Proos–Zalka 2003 (quant-ph/0301141 — origin of "inversion dominates
  point-add space" + register sharing); Roetteler–Naehrig–Svore–Lauter 2017 (1706.06752 —
  `9n+2⌈log₂n⌉+10` q, reversible Kaliski EEA); Häner et al. 2020 (2001.09580 — windowed scalar mult +
  adaptive uncompute, the 2124-q n=256 figure). Litinski 2023 (2306.08585 — ~50M Toffoli/key by
  **amortizing modular division across parallel instances**, up to ~5×; not applicable to a single
  scored PA but the amortization idea is worth noting).

## 2. Toffoli-primitive catalog (for the apply-phase modular arithmetic)

- **Temporary logical-AND** — *Gidney 1709.06648*: compute = 4 T, **uncompute = 0 T** (measurement +
  classically-controlled fixup). Already the basis of our adders; the rule is **every paired
  AND/compute–uncompute must use it**.
- **4-T Toffoli variants** — *Jones 1212.5069 (measurement-assisted, 4 T)*; *Maslov relative-phase
  Toffoli 1508.03273 (4 T when the spurious phase cancels across a compute/uncompute pair)*. Use the
  relative-phase form for MCTs that sit inside a paired block (the phase is uncomputed away).
- **Adder family as a depth↔ancilla↔Toffoli knob** — *Cuccaro 1-ancilla ripple quant-ph/0410184*
  (count-optimal, depth ∝ n — what our route uses); *Draper–Kutin–Rains–Svore QCLA quant-ph/0406142*
  (log-depth, O(n) ancilla — only if a **depth** metric ever matters); *Takahashi–Tani–Kunihiro
  0910.2530* (zero-ancilla, the qubit floor). Under our `Toffoli×qubit` score, ripple/Gidney is right.
- **RL for finite-field multiply T-count** — *AlphaTensor-Quantum 2402.14396*: rediscovers Karatsuba,
  beats heuristics on Shor-relevant GF multiplication. Candidate tool for the field-mult block, though
  ours is already Karatsuba/Solinas-tuned (expect small gains).

## 3. Qubit/ancilla toolkit (peak reduction)

- ★ **Conditionally-clean ancilla + Laddered Toggle Detection** — *Khattar–Gidney 2407.17966*: use
  borrowed/dirty bits **as if clean with zero allocation**. This is the principled generalization of
  our `ROUND84_XTAIL` dirty/vented and borrowed-carry tricks — audit our borrowed-carry adders against
  it for a cleaner peak win. Also *measurement-adaptive large MCX with one clean ancilla* (2605.18169).
- **Dirty/borrowed in-place adders** — *Häner–Roetteler–Svore 1611.07995; Gidney 1706.07884*:
  borrowed-qubit arithmetic costs ≈2× Toffoli for net-zero qubits — the **exact `1309↔1285` trade** we
  measured. Quantifies the qubit↔Toffoli exchange rate at the adder level.
- **Measurement-based / spooky-pebble uncomputation** — *Gidney "spooky pebble game"; Quist–Laarman
  2401.10579 (DAG, PSPACE-complete, SAT solver); Kornerup et al 2110.08973*: X-measure frees ancilla
  early, paying classically-controlled phase fixups — our "measured cleanup" / host-gated lever. A DAG
  solver could *schedule* it.
- ★ **Automated uncompute scheduling** — *Meuli–Soeken–Roetteler SAT/QBF 1904.02121; Unqomp PLDI'21
  (+2503.00822); spooky DAG solver*. Could **automate** the venting / recompute / hosting decisions we
  currently make by hand for the peak phase — high-value tooling direction, not just a one-off lever.
- **Reversible pebbling (recompute vs co-residence)** — *Bennett 1989; Levine–Sherman 1990;
  Parent–Roetteler–Mosca Karatsuba pebbling 1706.03419*: trade recomputation for qubits — our
  "recompute instead of co-residence" archetype.

## 4. Generic synthesis (know the tools; expect low yield on our hand-tuned route)

- ZX phase teleportation (*Kissinger–van de Wetering 1903.10477*, PyZX), graph simplification
  (*Duncan et al 1902.03178*), T-par phase polynomial (*Amy–Maslov–Mosca 1303.2042*), verified
  rewriting (*Quartz 2204.09033, VOQC 1912.02250*). These cut T-count ~10–50% on **un-optimized**
  circuits. Ours is hand-optimized from already-tight primitives (we empirically found **0 peephole
  cancellations**), so expect little — but a one-shot ZX/T-par pass on the **field-arithmetic blocks
  in isolation** is a cheap thing to try.

## 5. Cost-model grounding (why `Toffoli × qubits`, and its caveat)

- *Gidney–Ekerå 1905.09749* (spacetime volume / megaqubitdays); *Fowler–Gidney 1812.01238* (Toffoli
  factory: ~one CCZ per ~5.5d cycles); *Beverland 2211.07629* (logical qubit-cycle). True cost ≈
  `α·(qubits × depth) + β·(Toffoli count)`; `qubit × Toffoli` is a sound proxy **under 2D surface
  codes**, where idle storage ∝ qubits. **Caveat**: *Litinski–Nickerson active volume 2211.15465* and
  *Gidney–Shutty–Jones magic-state cultivation 2409.17595* shift the balance toward **Toffoli/op count
  alone** (idle qubits become ~free). For *this* sequential circuit, depth ≈ count, so the distinction
  is largely moot here.

## 6. Validity / correctness (zero-cost wins + the island failure mode)

- *Papa 2025 (2506.03318)* catalogs **four ancilla-uncomputation bugs in published point-add
  circuits**, all fixable at **zero gate cost**. Maps directly to our `anc/cls/pha = 0` checks: a
  missed uncompute is a *free* correctness fix; conversely, an *over-eager* truncation that fails
  uncompute on some inputs is precisely the island-search failure mode (`pha`/`cls > 0` on the 9024
  shots). Audit any new truncation against these patterns before scanning.

---

## Top takeaways for *this* benchmark

1. **`jumpdivsteps` is the unexplored generalization of our winning `ACTIVE_ITERATIONS`/`K2` lever** —
   batch `T` GCD steps into one transition matrix to cut full-width applies, trading transcript width
   for full-width-op count. (§1)
2. **`conditionally-clean ancilla` (Khattar–Gidney) is the principled version of our dirty/vented
   `ROUND84` peak tricks** — likely a cleaner 1309→1285-class win. (§3)
3. **Automated uncompute scheduling (SAT/spooky-DAG)** could replace hand-tuned venting/hosting. (§3)
4. **Legendre/Jacobi inversion-elimination (1098 q)** is the qubit-frontier direction but a moonshot
   for the affine-PA score; understand it before any projective teardown. (§1)
5. Generic ZX/T-par tooling is **low-yield** on our hand-optimized route; the leverage is structural
   (inversion algorithm, ancilla hosting), not peephole. (§4)
