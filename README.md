# Skills for the ECDSAFail Challenge

Agent skills for optimizing the [ecdsa.fail](https://ecdsa.fail) challenge — a reversible
quantum circuit that adds a quantum elliptic-curve point to a classical one on secp256k1 — plus
the **general, transferable quantum-circuit-optimization skills** distilled from that work.

**Objective (the challenge):** minimize `score = peak_qubits × average_executed_Toffoli` (lower
is better). The circuit is validated on 9,024 SHAKE256-derived shots and must be perfectly
reversible (`0 classical / 0 phase / 0 ancilla` violations). A free 96-gate identity tail
(`DIALOG_TAIL_NONCE`) reseeds those shots, so any config change requires re-hunting a clean
"island" nonce.

## 📘 Start here: the Optimization Techniques Primer

New to this work? Read the **[Qubit & Toffoli Reduction Techniques Primer](primer/ecdsafail_optimization_techniques_primer.md)**
([**PDF**](primer/ecdsafail_optimization_techniques_primer.pdf)) first. It's a self-contained, undergrad-level
tour of *every* optimization technique used in the challenge, explained from quantum-circuit first
principles with concrete examples and ablation numbers from real submissions:

- **What the challenge is** and why one elliptic-curve point addition is the thing being optimized.
- **20 qubit-reduction techniques** and **19 Toffoli-reduction techniques** — live-range holes, MBU /
  measurement-based uncompute, venting, Karatsuba squaring, gate-hosting, pseudo-Mersenne (Solinas)
  reduction, structural dead-gate skipping, and more.
- The **theory** (Bennett vs. spooky pebbling), the **density-neutral vs. island-exact** correctness
  split, and how the SOTA `trailmix_ludicrous` and low-qubit **Shrunken-PZ** circuits actually work.
- All **three competition objectives** — minimize the Q×T product, minimize qubits alone, and map the
  clean (qubit, Toffoli) Pareto frontier — and the full history of how the records were won.

The skills below are the operating playbooks; the primer is the conceptual foundation behind them.

## How to Use

### 1. Install the skills
Use the following command to symlink each skill directory into a location your agent scans. Do **symlinks, not copies**, so they keep tracking this repo as it's updated:

```bash
SKILLS=/path/to/ecdsafail_skills
for d in "$SKILLS"/*/; do
  [ -f "$d/SKILL.md" ] && ln -sfn "${d%/}" ~/.claude/skills/"$(basename "$d")"
  [ -f "$d/SKILL.md" ] && ln -sfn "${d%/}" ~/.codex/skills/"$(basename "$d")"
done
```

The four **general** skills are self-contained (any reversible/quantum circuit); the three
**domain** skills + the Agentic loop also need the prerequisites below.

### 2. Prerequisites (for the ecdsa.fail loop)
- the **`ecdsafail` toolchain**: Please see https://www.ecdsa.fail/ for the instructions;

### 3. Kick off an agent loop (see the "The Agentic loop" section for more details)
Once installed, **describe the task and let the skill descriptions route it** — you rarely name a
skill. For a full distributed run, paste a prompt like this into Claude Code or Codex (fill in your GPU SSH endpoints):

```text
The latest ecdsafail GPU toolkit is at https://github.com/jieyilong/ecdsafail_gpu_toolkit —
read all its markdown docs and follow the usage. Use these recommended safer fast settings:

# Phase 1 — GPU scan to find GCD-clean candidates
GPU_BATCH_INV=1 GPU_COMB_BITS=22 GPU_GCD_MODE=trunc_first GPU_FAN_BITS=22 GPU_WAVE=128 ./island.sh search s.bin <START> <N>

# Phase 2 — CPU validate to confirm 0/0/0
EVAL_FAST_REJECT=1 ./island.sh validate "<CFG>" <nonce> [<nonce>...]

Pull the ecdsa.fail SOTA and recent submission notes, analyze the techniques behind the
qubit and Toffoli savings, brainstorm further improvements, and start improving from the
current SOTA. When you find a new solution, pull the latest SOTA again and compare
score = qubit_count * average_executed_Toffoli; if your score is lower, submit it.

Distribute island scanning across the remote GPUs below over DISJOINT nonce ranges. Run a
15-minute heartbeat with progress + debugging info. On EACH heartbeat, remote-validate ALL
newly-discovered GCD-clean candidates on the GPU boxes in parallel (full validation, drain the
whole backlog) — and SEPARATELY cross-check just 5 of them against local validation as a trust
check on the remote validator (the 5 are only the cross-check, NOT the validation; validate them all):

ssh -i <path/to/key> -p <port1> ubuntu@<gpu_machine_ip1>
ssh -i <path/to/key> -p <port2> ubuntu@<gpu_machine_ip2>
ssh -i <path/to/key> -p <port3> ubuntu@<gpu_machine_ip3>
ssh -i <path/to/key> -p <port4> ubuntu@<gpu_machine_ip4>
```

For a **focused job** instead of the full loop, just say it: "this reversible adder peaks at 5n
qubits, get it to 3n" → `peak-qubit-reduction`; "cut the T-count of this multiplier" →
`toffoli-reduction`; "a competitor beat my benchmark, what changed?" → `benchmark-frontier-archaeology`.

If the skills **aren't** installed (a one-off agent / subagent / CI), point at the files instead:
"Read every `SKILL.md` under `<path>/ecdsafail_skills/` and apply the relevant methodologies."

**Anti-pattern:** don't tell an agent to "use all the skills" on a narrow task — they are
*selectively* triggered. Describe the task and the right subset fires.

### 4. Coordinate multiple agents with a mailbox

When running Claude + Codex, several Codex sessions, or any pair of agents on the same SOTA hunt,
also use [`ecdsafail-multi-agent-collaboration`](ecdsafail-multi-agent-collaboration/SKILL.md).
This skill is the coordination layer around the other skills: it tells agents how to exchange exact
measurements, split structural/autopsy/GPU work, independently verify each other's claims, and
converge on one score-gated route. It also covers the other axis of parallelism — a single agent
**fanning out orthogonal sub-investigations** (literature survey, multi-dimension failure autopsy,
multi-route bake-off) and reading their convergence/conflict as signal (the "multi-agent
autoresearch" pattern; pairs with the separate `expert-autoresearch` / `super-autoresearch`
skills).

The mailbox itself can be improvised per session. A common pattern is that one agent creates a
small local mailbox server with endpoints like "read messages since cursor" and "post addressed
message"; a file-backed queue or sqlite-backed script is also fine. The important contract is:

- every agent reads from its last cursor before acting;
- every substantive message includes exact config/worktree/commit/nonce, q, emitted ops, average
  executed Toffoli, score basis, `cls/pha/anc`, density or validation status, and the proposed next
  split of work;
- promising peer claims are treated as hypotheses until independently rebuilt or re-evaluated;
- broad GPU scans wait until both score-gating and short density triage justify them.

Example prompt:

```text
Collaborate with the Claude/Codex peer through the local mailbox created for this session.
Use ecdsafail-multi-agent-collaboration: read the thread from your last cursor, report exact local
measurements, split the next experiments, and keep polling until you converge on one q<1170 route.
One agent should run source/autopsy work while the other score-gates and runs short GPU density
triage. Independently verify any promising peer result before scanning broadly or submitting.
```

## The Agentic loop

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
   - **each heartbeat, remote-validate EVERY newly-discovered GCD-clean candidate** on the GPU
     machines in parallel (full validation, no fast-reject — drain the whole backlog, not a sample);
   - **separately, cross-check just 5 of those candidates against local validation** — that's only a
     trust gate on the remote validator (exact `cls/pha/anc` agreement before trusting a node), **not
     the validation itself.** Validating only the 5 and skipping the rest is the mistake to avoid;
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
| [`ecdsafail-multi-agent-collaboration`](ecdsafail-multi-agent-collaboration/SKILL.md) | **Coordinate parallel agents.** Claude/Codex mailbox discipline for benchmark hunts: exchange exact configs and measurements, split route/autopsy/GPU work, independently verify claims, reconcile disagreements, and converge on one score-gated route. |

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

**Primer (start here):** [`primer/ecdsafail_optimization_techniques_primer.md`](primer/ecdsafail_optimization_techniques_primer.md)
· [PDF](primer/ecdsafail_optimization_techniques_primer.pdf) — a comprehensive, undergrad-level explanation of
every qubit/Toffoli reduction technique used in the challenge (see the callout near the top).

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
