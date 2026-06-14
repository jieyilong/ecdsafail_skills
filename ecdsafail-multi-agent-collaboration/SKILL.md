---
name: ecdsafail-multi-agent-collaboration
description: Use this skill when coordinating two or more agents, such as Claude and Codex, on the ECDSA Fail challenge or another benchmark-driven circuit-optimization hunt — or when one agent fans out parallel sub-investigations (multi-agent autoresearch). Trigger whenever the user mentions collaborating with another agent, a mailbox, Claude/Codex teamwork, exchanging hypotheses, independent cross-checks, splitting GPU/research work, fanning out parallel research/diagnostic subagents, or converging on a route to beat SOTA. This skill turns multi-agent chat into a disciplined scientific loop: read the thread, share exact evidence, fan out orthogonal sub-investigations, divide experiments, reconcile convergence/conflict, and preserve the winning route.
---

# ECDSA Fail Multi-Agent Collaboration

Use this when another agent is working the same frontier. The goal is not more chatter; it is parallel scientific pressure with shared memory, independent verification, and fast convergence on one route worth spending GPUs on.

## Core Pattern

Run the agents as independent labs connected by a lightweight mailbox:

1. **Read before acting.** Pull the full new message thread and note the cursor/id you will resume from.
2. **State your local ground truth.** Share exact configs, commit/worktree, q, emitted ops, avg executed Toffoli, score, `cls/pha/anc`, scan density, and validation status.
3. **Split the frontier.** One agent should run structural/code or autopsy work while the other runs scoring, density triage, validation, or alternate-route sweeps.
4. **Cross-check claims independently.** Treat another agent's promising result as a hypothesis until you rebuild/eval it in your own worktree or they provide enough reproducible detail.
5. **Converge to one route.** When both agents see the same candidate as score-gated and landable, stop broad brainstorming and focus on repair, density, validation, and submission.
6. **Preserve experiment memory.** Summarize dead ends, exact knobs, why a route is RED/YELLOW/GREEN, and what the next agent should not repeat.

## Fan Out Parallel Sub-Investigations

The mailbox connects *peer* agents; the second multiplier is each agent fanning out its own
*sub-investigations*. When a question has several orthogonal angles — a literature survey, a
failure-mode autopsy across dimensions, a multi-route bake-off, a "which of N levers binds the
peak" sweep — spawn one subagent (or background job) per angle in parallel, then synthesize. This
is the `expert-autoresearch` / `super-autoresearch` pattern applied mid-hunt.

- **Make the angles orthogonal.** For "can any technique beat the floor?" use distinct lenses —
  e.g. (1) divstep/recompute circuits, (2) the specific paper's applicability to *our* exact
  objective, (3) recent published records, (4) the underlying time-space theory. Overlapping
  angles waste the fan-out.
- **Force structured returns.** Each subagent returns a small table of facts + a bottom-line
  yes/no with citations, not an essay. You synthesize; they measure.
- **Read convergence and conflict as signal.** If independent subagents (or the two peer agents)
  reach the *same* conclusion by *different* methods, that's high-confidence — stop and act. If
  they *conflict*, the conflict localizes the crux: resolve it with the smallest decisive test
  (often reading the source), not by averaging opinions. A theory predicting a cheap result and a
  measurement showing an expensive one are reconciled by finding the assumption that breaks — not
  by picking the answer you prefer. (Worked example this frontier: pebbling theory predicted a
  cheap partial-recompute "knee"; the per-step cost measurement looked compatible; reading the
  apply source — it carries no resumable GCD state — proved it was a cliff. The source read, not
  the theory or the raw number, settled it.)
- **A reproducible measurement outranks an analysis-only verdict.** If a peer's working branch or a
  subagent's measured number contradicts your reasoned conclusion, rebuild it in your own worktree
  and revise — own the correction fast. "It can't be done" loses to a branch that does it. (This
  frontier: an analysis-only "sub-1170 is closed" verdict was overturned by a peer branch that
  reached q1163; the right move was to rebuild it, measure that it was score-positive but
  density-collapsed, and re-aim the work — not defend the verdict.)

## Mailbox Workflow

Use whatever lightweight mailbox the agents can stand up locally for the session: an ad-hoc HTTP
server, a tiny file-backed queue, a sqlite table, a named pipe wrapper, or any equivalent channel
that lets each agent read messages since a cursor and post addressed replies. The transport is not
the point; the cursor discipline and reproducible message content are.

If the agents create a small local HTTP mailbox, the interaction usually looks like this:

```bash
MAILBOX_URL="<local-mailbox-url>"

curl -s "$MAILBOX_URL/msgs?since=0&agent=<your-agent>"
curl -s -X POST "$MAILBOX_URL/msg" \
  -H 'Content-Type: application/json' \
  -d '{"from":"<your-agent>","to":"<peer-agent>","topic":"<topic>","text":"<message>"}'
curl -s "$MAILBOX_URL/msgs?since=<last-id>&agent=<your-agent>"
```

Keep messages short but reproducible. A good message lets the other agent run the next experiment without asking for context.

## Message Template

Use this structure for substantive replies:

```text
Route/config:
- worktree/commit:
- env/knobs:
- nonce/state file, if relevant:

Measured facts:
- q:
- emitted ops:
- avg executed Toffoli:
- score/projection:
- cls/pha/anc:
- scan density or validation result:

Interpretation:
- GREEN/YELLOW/RED:
- likely blocker:
- what this disproves:

Proposed split:
- I will:
- Please check:
- stop condition:
```

Avoid vague encouragement. Say what you measured, what changed your mind, and what should happen next.

## Division Of Labor

Prefer complementary tracks:

- **Agent A: route and source work**
  - diff SOTA branches;
  - identify peak binders and hot Toffoli phases;
  - implement or toggle structural levers;
  - run `TRACE_PEAK=1 build_circuit`, `eval_circuit`, phase stats, and autopsy helpers.

- **Agent B: score and landability work**
  - compute score gates against the latest promoted SOTA;
  - build GPU state for candidate routes;
  - run short density triage scans;
  - remote-validate all GCD-clean candidates in full mode;
  - local-cross-check exactly 5 sampled candidates for validator trust.

Swap roles when one side is blocked. Do not let both agents spend the same hour retrying the same knob.

## Independent Verification Rules

Before accepting a peer result:

- Rebuild the exact config in your own worktree, or confirm the peer supplied worktree/commit/env/nonce sufficient to reproduce it.
- Re-run `build_circuit`/`eval_circuit` or the closest cheap diagnostic.
- If the route is dirty, collect `cls/pha/anc` and a failure histogram, not just the first failing shot.
- If the route needs island hunting, run a small density triage before allocating broad GPU ranges.
- If remote validation is used, drain the full candidate backlog remotely and use the local 5-candidate sample only as a trust cross-check.
- For submissions, let the server compute the score. Do not submit with a hand-claimed score.

## Disagreement Handling

When agents disagree, classify the cause:

- **Different defaults:** one worktree may have baked env defaults. Pin every controversial knob explicitly.
- **Different op stream:** compare `emitted ops`, `ops.bin` length, commit hash, and `DIALOG_TAIL_NONCE`.
- **Different metric:** emitted CCX, average executed Toffoli, and rounded submitted Toffoli are not interchangeable.
- **Different validation mode:** full validation beats fast validation; local/remote mismatch quarantines the remote result until resolved.
- **Different SOTA basis:** always name the promoted SOTA commit and score used for the score gate.

Do not argue from memory. Make the smallest reproducible test that distinguishes the claims.

## Route Triage Language

Use consistent labels:

- **GREEN:** score-gated, q cap satisfied, density healthy, near misses include independent zeros in each channel, validation trusted.
- **YELLOW:** score-gated but dirty or density unknown; deserves short triage/autopsy.
- **RED:** not score-gated, violates q cap, density collapsed, or failure is structurally impossible without an unaffordable repair.

Include why a route is labeled. For example:

```text
YELLOW: q1163 and score-positive by ~9M, but 60M scan has 0 GCD-clean candidates.
Autopsy shows 7 GCD-hard failures and 43 apply mismatches, so next repair target is apply replay, not uniform active iterations.
```

## Collaboration Loop For Frontier Hunts

1. **Sync SOTA.** Pull/check promoted SOTA before score decisions.
2. **Share a candidate slate.** Each agent proposes at most 2-3 routes, not a long undifferentiated list.
3. **Score-gate first.** Reject anything that cannot beat SOTA under the user's q/Toffoli policy unless the user explicitly wants qubit-frontier preservation.
4. **Cheap diagnostics.** Measure q, avg Toffoli, `cls/pha/anc`, and failure histogram.
5. **Short density triage.** Use equal small GPU windows. Stop on density collapse.
6. **Repair based on histograms.** Match the repair to the failure class: active-step convergence, tail codec, compare width, apply value mismatch, fold carry escape, phase cleanup, or ancilla cleanup.
7. **Validate before broad hunt.** Remote full validation for all candidates, local 5-sample cross-check for trust.
8. **Submit only verified winners.** Bake config+nonce, run canonical `ecdsafail run`, re-check SOTA, submit only if policy allows and measured score beats promoted SOTA.
9. **Update the peer.** Send the exact result and next recommended action.

## What To Preserve

At the end of a useful exchange, record:

- exact winning or dead-end config;
- worktree and commit;
- q / avg Toffoli / projected score;
- full `cls/pha/anc`;
- GCD-clean density and validated near misses;
- failure histogram;
- route label and reason;
- next structural move.

This is the material that should graduate into `ecdsafail notes`, skill updates, or README memory.
