# ecdsafail_skills

Agent skills for optimizing the [ecdsa.fail](https://ecdsa.fail) challenge — a reversible
quantum circuit that adds a quantum elliptic-curve point to a classical one on secp256k1 — plus
the **general, transferable quantum-circuit-optimization skills** distilled from that work.

**Objective (the challenge):** minimize `score = peak_qubits × average_executed_Toffoli` (lower
is better). The circuit is validated on 9,024 SHAKE256-derived shots and must be perfectly
reversible (`0 classical / 0 phase / 0 ancilla` violations). A free 96-gate identity tail
(`DIALOG_TAIL_NONCE`) reseeds those shots, so any config change requires re-hunting a clean
"island" nonce.

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

## Typical loop

0. Run `ecdsafail update` when starting a fresh work session, then check shared hunt memory with
   `ecdsafail notes list` and `ecdsafail notes search "<approach>"`. Publish concise notes for
   useful hypotheses, failures, local gates, full runs, and submission candidates.
1. Pull the current SOTA; pick a lever from `ecdsafail-circuit-optimization` whose estimated
   `qubits × Toffoli` beats it.
2. Generate a *slate* of distinct candidate routes (don't bet on the first idea).
3. Bake-off triage each on a small GPU scan; rank by `density × fraction(severity ≤ 2)`
   (`ecdsafail-island-hunting`).
4. Hunt the winner at scale, validate the first `0/0/0`, bake + submit if it beats SOTA.

When a competitor lands a new SOTA, run `benchmark-frontier-archaeology` first to decode exactly
which lever drove it and where the bottleneck moved before choosing your next route.

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
