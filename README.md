# ecdsafail_skills

Agent skills for optimizing the [ecdsa.fail](https://ecdsa.fail) challenge — a reversible
quantum circuit that adds a quantum elliptic-curve point to a classical one on secp256k1.

**Objective:** minimize `score = peak_qubits × average_executed_Toffoli` (lower is better).
The circuit is validated on 9,024 SHAKE256-derived shots and must be perfectly reversible
(`0 classical / 0 phase / 0 ancilla` violations). A free 96-gate identity tail
(`DIALOG_TAIL_NONCE`) reseeds those shots, so any config change requires re-hunting a clean
"island" nonce.

## The two skills

| Skill | Role |
|-------|------|
| [`ecdsafail-circuit-optimization`](ecdsafail-circuit-optimization/SKILL.md) | **Design & score** structural circuit changes *before* spending GPU time. Qubit/Toffoli reduction patterns, the qubit↔Toffoli exchange model, the verified public SOTA knob-ladder, the current frontier lever, and documented dead-ends. |
| [`ecdsafail-island-hunting`](ecdsafail-island-hunting/SKILL.md) | **Validate & search.** Disciplined GPU island hunting: score-gate against SOTA, run a multi-route bake-off ranked by *landability*, triage `cls/pha/anc` candidate quality, validate `0/0/0`, and submit only confirmed score-beating islands. |

They compose: **circuit-optimization** proposes candidate routes and estimates their score;
**island-hunting** triages them on GPU and confirms which has a clean nonce worth submitting.

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
