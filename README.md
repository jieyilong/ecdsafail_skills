# ecdsafail_skills

Agent skills for optimizing the [ecdsa.fail](https://ecdsa.fail) challenge — a reversible
quantum circuit that adds a quantum elliptic-curve point to a classical one on secp256k1 — plus
the **general, transferable quantum-circuit-optimization skills** distilled from that work.

**Objective (the challenge):** minimize `score = peak_qubits × average_executed_Toffoli` (lower
is better). The circuit is validated on 9,024 SHAKE256-derived shots and must be perfectly
reversible (`0 classical / 0 phase / 0 ancilla` violations). A free 96-gate identity tail
(`DIALOG_TAIL_NONCE`) reseeds those shots, so any config change requires re-hunting a clean
"island" nonce.

## Agentic loop

The full life cycle of an autonomous search for a new (lower-score) solution. Each stage names the
skill that drives it; throughout, publish concise `ecdsafail notes` (hypotheses, local gates, full
runs, failures, submission candidates) so the shared pool compounds.

0. **Session setup — pull the SOTA as the basis.** `ecdsafail update`, then `ecdsafail sync` to
   download the current promoted SOTA as the working basis. Read shared hunt memory
   (`ecdsafail notes list`, `ecdsafail notes search "<approach>"`) so you don't re-walk dead
   routes, and **load the skills** in this repo.

1. **Understand the basis.** Measure what you just pulled — peak qubits
   (`TRACE_PEAK=1 build_circuit`), emitted / average-executed Toffoli, and the binder phase + its
   live-set composition. If the SOTA is *new* (a competitor just moved it), run
   **`benchmark-frontier-archaeology`** first to decode which lever drove it and where the
   bottleneck sits now.

2. **Look for a couple of candidates** (a *slate*, not one bet) with
   **`ecdsafail-circuit-optimization`**: try quick config knobs first; when knobs go flat (the cost
   is allocation-bound), escalate to a structural code change via **`peak-qubit-reduction`** (width
   axis) or **`toffoli-reduction`** (gate axis). Score-gate each candidate's estimated
   `qubits × Toffoli` against SOTA; keep the few that plausibly beat it.

3. **Small-scale test first.** Build each surviving candidate and check structural correctness on
   **random inputs** with **`reversible-circuit-validation`** — a width cut must be `0/0/0`
   value-exact *before* any hunt. Then a short GPU triage scan (**5–10M nonces**) to read the
   **GCD-clean candidate density**.

4. **Triage / bake-off** with **`ecdsafail-island-hunting`**. Per candidate route, collect the two
   landability signals: **GCD-clean density** (candidates/Mnonce) and the **`cls/pha/anc`
   distribution** of its candidates (validate the whole batch, full mode). Rank by:
   - **density gate** — GREEN `> 0.5`, YELLOW `0.2–0.5`, RED `< 0.2` candidates/Mnonce;
   - **per-channel-zero** — each of `cls`, `pha`, `anc` must independently reach 0 *somewhere*, or
     that channel is floored and `0/0/0` is unreachable no matter the nonce;
   - prefer low near-misses clustered toward `0/0/0`.
   If a route is too dirty, repair the errors (restore a carry/compare bit, widen an envelope)
   until real near-misses appear, then re-triage.

5. **Pick the most promising candidate → distributed GPU island hunt.**
   - assign **disjoint nonce ranges** across the GPU fleet;
   - **validate on the GPU machines in parallel** (full validation, no fast-reject) — but
     **cross-check 5 sampled candidates against local validation** each cycle, so a stale remote
     validator or wrong binary can't silently corrupt the result;
   - run a **15-minute heartbeat** that prints progress and useful debugging info: per-GPU
     rate / range / density, validation backlog + validator-trust status, the best `cls/pha/anc`
     near-misses, any clean `0/0/0` immediately, and anomalies (idle GPU, stale state file,
     zero-candidate node).

6. **Close the loop.**
   - **If a clean `0/0/0` island with a lower score is found:** bake the config + nonce, re-measure
     the canonical score (`ecdsafail run`), and **`ecdsafail submit`** if it beats the current
     promoted SOTA.
   - **Otherwise (no win, or a competitor moved the frontier mid-hunt):** **rebase onto the new
     SOTA** (`ecdsafail sync`), run **`benchmark-frontier-archaeology`** to decode its lever, **add
     the new technique to `ecdsafail-circuit-optimization`**, commit/push, and restart the loop from
     the new basis.


## Skills

### Domain skills (ecdsa.fail-specific)

| Skill | Role |
|-------|------|
| [`ecdsafail-circuit-optimization`](ecdsafail-circuit-optimization/SKILL.md) | **Design & score** structural circuit changes *before* spending GPU time. Qubit/Toffoli reduction patterns, the qubit↔Toffoli exchange model, the verified public SOTA knob-ladder, the current frontier lever, and documented dead-ends. |
| [`ecdsafail-island-hunting`](ecdsafail-island-hunting/SKILL.md) | **Validate & search.** Disciplined GPU island hunting: score-gate against SOTA, run a multi-route bake-off ranked by *landability*, triage `cls/pha/anc` candidate quality, validate `0/0/0`, and submit only confirmed score-beating islands. |

(The `ecdsafail-cli` skill — driving the `ecdsafail` CLI itself — is maintained separately, not in
this repo.)

### General quantum-circuit skills (domain-agnostic, transferable)

These were extracted from the ecdsa.fail work but apply to **any** reversible/quantum circuit.
Each defers to the domain skills above for concrete knob names and the GPU island search.

| Skill | Axis | What it does |
|-------|------|--------------|
| [`peak-qubit-reduction`](peak-qubit-reduction/SKILL.md) | width (qubits) | Treat the circuit as a left-to-right timeline, find the single tallest "binder" instant and which phase owns it, then shave it — uncompute-early/recompute-later live-range holes, passenger relocation, truncation + per-step scheduling, bijective transcript compression. Re-measure after every change (the binder migrates). |
| [`toffoli-reduction`](toffoli-reduction/SKILL.md) | gates (Toffoli/T) | The dual: locate the Toffoli/T hot-spot, classify its gates, and apply the matching move — vent carry-uncompute into measurement+phase fixups, conditional/measured replay (executed-metric only), fused folds, ancilla-free majority, skip-redundant-cleanup, avoid materialization. Watch Toffoli-*depth* (the non-refundable trap). |
| [`reversible-circuit-validation`](reversible-circuit-validation/SKILL.md) | correctness | The `cls/pha/anc` three-channel decomposition (a value check is *not* sufficient), differential testing on random inputs, the forward-inverse identity (`U†U = I`), telling a *designed* approximation failure from a real bug via a classical model, and localizing the first broken op. |
| [`benchmark-frontier-archaeology`](benchmark-frontier-archaeology/SKILL.md) | competitive analysis | Reverse-engineer an advancing benchmark: diff *consecutive* winners (walk every intermediate, never endpoint-diff), re-measure yourself, decompose a multi-factor score delta, separate a transferable lever from a non-transferable search artifact, and track the migrating bottleneck to name the next target. |

## How they compose

The domain pair composes as: **circuit-optimization** proposes candidate routes and estimates
their score; **island-hunting** triages them on GPU and confirms which has a clean nonce worth
submitting.

The general skills form a pipeline around any size-reduction effort:

```
benchmark-frontier-archaeology   →   peak-qubit-reduction  ┐
  (decode a competitor's lever,        (width axis)        ├→  reversible-circuit-validation
   name the bottleneck & next      toffoli-reduction       ┘     (confirm cls/pha/anc clean,
   target — the intake stage)          (gate axis)               re-hunt any borrowed artifact)
```

i.e. *archaeology* tells you which lever to pull and where the binder is → *peak-qubit-reduction*
and *toffoli-reduction* do the two halves of the `qubits × Toffoli` optimization → *validation*
confirms the change stayed correct (and that any re-hunted island is `0/0/0`). On this challenge,
the general skills hand off to `ecdsafail-circuit-optimization` / `ecdsafail-island-hunting` for
the concrete knobs and the GPU search.

## References

Deep-dive analyses backing the circuit-optimization skill (under
[`ecdsafail-circuit-optimization/references/`](ecdsafail-circuit-optimization/references/)):

- **`andre-schrottenloher-2026-analysis.md`** — space-efficient reversible modular
  arithmetic / EEA-dialog in-place multiplication / pseudo-Mersenne reduction (arXiv 2606.02235).
- **`trailmix-implementation-analysis.md`** — Trail of Bits TrailMix: transcript compression,
  jump-GCD, venting, whole-register ghosting, and verification discipline.

## Notes

- These skills are kept current with the live leaderboard — the frontier ladder and the active
  lever in `ecdsafail-circuit-optimization/SKILL.md` are updated as new SOTAs land.
- Treat `ecdsafail notes` as shared experiment memory: read/search it before starting a route and
  add a short structured note after useful experiments, including failed ones.
- GPU island hunting itself is driven by a separate toolkit (the `ecdsafail-island` GPU searcher);
  these skills cover the *reasoning and discipline*, not the kernel.
- The four general skills are self-contained and domain-agnostic; only their *worked examples* and
  knob references point back at the ecdsa.fail circuit.
