---
name: ecdsafail-island-hunting
description: Use this skill whenever working on ECDSA Fail / EC point-addition island hunting, GPU nonce scans, clean island validation, cls/pha/anc triage, SOTA score comparison, or deciding whether a quantum circuit optimization is worth scanning. This skill is especially important when the user asks to start, monitor, triage, validate, or extend island scans; compare against SOTA; run fast validation; or choose between circuit routes.
---

# ECDSA Fail Island Hunting

Use this skill to run disciplined island-hunting experiments for ECDSA Fail circuit candidates. The goal is to spend GPU time only on routes that can plausibly beat SOTA and that show healthy candidate behavior.

## Core Workflow

1. Pull the latest SOTA before starting or extending a route.
2. Estimate the candidate score:

   ```text
   score = qubit_count * estimated_toffoli_count
   ```

3. **Generate several candidate structural changes first — do not hunt the first idea.** Use the
   `ecdsafail-circuit-optimization` skill to design a slate of distinct routes (different qubit/Toffoli
   levers: carry-truncation notches, compare-bit narrowing, segmentation, in-place/aliasing tricks,
   pseudo-Mersenne folds, apply-chunk rebalances, etc.). Score-gate each against SOTA and keep the
   handful that plausibly beat it.
4. When you have **several** surviving candidates, do a **route bake-off**: run a short equal-size
   triage scan on each, then **rank them by island findability** (GCD-clean density combined with the
   `cls / pha / anc` distribution of those candidates) before committing large GPU ranges. Hunt the
   top-ranked route first.
5. For the chosen route, start with a short triage scan, not a large frontier burn.
6. Use GCD-clean candidate density and `cls / pha / anc` statistics to classify the route.
7. Extend only routes that pass score, density, and validation gates.
8. Validate every newly flushed candidate in fast modes.
9. Submit only measured clean solutions whose score beats current promoted SOTA, unless the user explicitly gives different submission rules.

## Score Gate

Before scanning, compare the estimated score against current promoted SOTA.

- If `estimated_score >= SOTA_score`, do not start a large island search.
- If a later heartbeat finds a new SOTA that beats or ties the active estimate, keep already-running scans unless told to stop, but do not extend the route.
- Resume structural or Toffoli optimization before assigning new GPU ranges.

Use measured benchmark output for final score decisions. Estimated score is only a pre-scan gate.

## Route Bake-Off: Rank Structural Changes Before Committing GPUs

**Start by generating a slate of candidate routes, not a single bet.** Before any scanning, use the
`ecdsafail-circuit-optimization` skill to enumerate several distinct structural changes that could
beat SOTA — pull from its pattern catalogue (live-range shortening, carry/borrow truncation notches,
compare-bit narrowing, in-place/operand-aliasing tricks, segmentation, pseudo-Mersenne low-limb
folds, fused folds / fast adds, apply-chunk rebalances, the verified frontier knob ladder, etc.).
Aim for a handful of genuinely different routes (vary the *type* of lever, not just one knob by one
notch), measure/estimate each route's qubits and Toffoli, and keep the ones whose estimated score
beats SOTA. This slate is the input to the bake-off.

When you are exploring **multiple** such structural changes that all pass the score gate, do **not**
just pick one and burn a frontier-scale search on it. Most of them will never land a clean island,
and you find that out fastest by a cheap comparative pilot. Run a small, **equal-size** triage on
each and judge which route has the healthiest overall evidence. Then hunt the most promising route
first; only fall back to the next-ranked route if the leader is exhausted or fails its stop rules.

Start from the two primary island-findability signals:

1. **GCD-clean candidate density** — higher density means more shots on goal. A route producing
   2x the candidates per nonce reaches any given island count in half the nonces.
2. **The `cls / pha / anc` distribution of those candidates** — *how close* a typical GCD-clean
   candidate is to a clean island. A clean island is `0 / 0 / 0`; a candidate at `(1, 2, 0)` is a
   few constraint-bits away, while `(4, 5, 1)` is far away. Because each residual violation must
   independently vanish on the reachable verifier support, the chance a candidate is fully clean
   **falls off steeply (roughly geometrically) as its residual grows.** So a route whose candidates
   cluster at `(1, 2, 0)` is exponentially more likely to yield an island than one clustering at
   `(4, 5, 1)`, even at the same density.

Do not collapse route quality into a rigid formula. Use density and residual distributions as the
main evidence, then apply engineering judgment across supporting signals:

- **Score margin vs SOTA:** a route barely below SOTA has little runway if measured Toffoli drifts
  upward or a new SOTA appears.
- **Fast/full validation agreement:** stable agreement and componentwise fast<=full behavior build
  confidence; surprising disagreement points to tooling or structural uncertainty.
- **Fingerprint diversity:** varied dirty fingerprints suggest nonce-dependent behavior; one
  repeated fingerprint suggests a structural failure.
- **Failure localization:** late, small, varying failures are more huntable than early failures in
  GCD/apply reconstruction, carry cleanup, phase discharge, or core algebra.
- **Residual type:** persistent `pha` or `anc` is usually more concerning than classical-only
  (`cls`) residuals of the same size.
- **Distribution shape:** prefer routes with a visible tail toward zero over routes clustered tightly
  around high severity.
- **Nearby-route sensitivity:** if restoring one carry bit, compare bit, or cleanup step improves
  quality at modest score cost, the route has a tunable path.
- **Per-node and per-range health:** candidate production should be roughly consistent across
  ranges and GPUs; anomalies may indicate stale state, wrong binaries, or logging problems.
- **Validator reproducibility:** local and remote validators must match sampled candidates before
  trusting distributed validation.
- **Peak-owner plausibility:** the structural change should plausibly affect the measured peak
  owner; savings in non-peak phases may not translate into a real score improvement.
- **Nonce-range robustness:** similar behavior across separated ranges is stronger than one lucky
  small band.
- **Structural provenance:** prefer routes derived from a known-clean base by one understandable
  change over piles of interacting aggressive changes.

### Bake-off protocol

For each candidate structural change:

1. Scan the **same** pilot size on each route — **5-10M nonces** is the recommended band (enough
   to get tens of GCD-clean candidates on a healthy route). Use identical GPU prefilter settings.
2. Record GCD-clean density (candidates/Mnonce).
3. **Validate a large sample of the GCD-clean candidates** (ideally all of them, or at least
   ~30-50) in fast mode to get the `cls / pha / anc` of each. You need a distribution, not a single
   triple — one lucky near-miss does not rank a route.
4. Build the **residual histogram**: bucket candidates by `severity = max(cls, pha, anc)` (sev = 1,
   2, 3, ...). Note separately any `pha > 0` or `anc > 0`, which are structural/harder signals.

### Comparative judgment

Use the pilot evidence to make a qualitative route judgment, not a pretend-precise score. Prefer
routes where multiple independent signals agree: healthy density, low and diverse residuals, stable
validation, plausible peak-owner impact, and no suspicious node or CFG behavior. Stop or demote a
route when strong structural-failure evidence appears, even if one metric looks good.

Useful comparison cues:

- Prefer the route with the **lower mean/median severity** — a route whose mass is at `(1, *, 0)`
  beats one at `(3, *, 0)` even if the `<=2` fractions are close.
- **Penalize nonzero `pha` and `anc`.** Classical (`cls`) residuals are what nonce hunting most
  directly drives to zero; persistent `pha`/`anc` across candidates is usually a structural defect
  that no nonce will fix (see Stop Rules). A route at `(1, 0, 0)` ranks well above `(1, 0, 1)`.
- Penalize routes whose near-misses all share **one identical fingerprint** (no diversity) — that
  is a structural near-miss, not a distribution you can search through.
- Prefer routes whose promising candidates appear across multiple nonce ranges and nodes.
- Prefer routes whose nearby safer variants improve smoothly rather than flipping between clean-ish
  and uniformly broken.
- Prefer routes whose estimated score has enough SOTA margin to survive final measurement drift.

### Worked example

| route | density (c/Mn) | typical validation pattern | supporting signals | decision |
|-------|---------------:|----------------------------|--------------------|----------|
| A | 0.8 | many `(1, 2, 0)` / `(2, 1, 0)` candidates | diverse fingerprints, range-stable, good score margin | hunt first |
| B | 1.6 | mostly `(4, 5, 1)` with persistent `pha/anc` | higher density, but poorer residual type | hold or hunt second |
| C | 0.3 | a few `(2, 0, 0)` candidates | low density, but clean residual type | hold for fallback |
| D | 1.2 | repeated `9024 / 141 / 0` | uniform high fingerprint | drop as structural |

Route B has the highest raw density, but its candidates sit far from clean and carry persistent
phase/ancilla dirt. Route A has fewer shots on goal but healthier near misses and more independent
supporting signals, so it is the better first hunt. D is dropped outright on the uniform high
fingerprint regardless of density.

### Cost discipline

The bake-off is a **comparison**, not a hunt. Keep each pilot to the 5-10M band and stop as soon as
the ranking is clear — if one route has much healthier overall evidence after a few million nonces,
commit GPUs to it rather than finishing equal pilots on the obvious losers. Re-run a fresh bake-off
whenever the base circuit changes (a new SOTA base reseeds every route's inputs).

## Short Triage Scan

Run a pilot before large-scale search. A useful pilot is usually a few million to a few tens of millions of nonces, distributed across available GPUs if convenient.

During triage, collect:

- total nonces scanned
- GCD-clean candidates found
- candidate density in candidates per million nonces
- `cls / pha / anc` triples for validated candidates
- best severity, median severity, and whether failures have diverse fingerprints

Define:

```text
severity = max(cls, pha, anc)
```

## Candidate Density Gate

Use candidate density to detect unpromising or broken circuit structures early.

- GREEN: `> 0.5 candidates/Mnonce`
- YELLOW: `0.2..0.5 candidates/Mnonce`
- RED: `< 0.2 candidates/Mnonce`

Also compare against recent healthy baselines. If density is less than about 25% of known-good routes, treat it as suspicious even if the absolute density is not zero.

Do not extend RED routes. For YELLOW routes, extend only if validation has promising near misses.

## Validation Gate

Validate newly flushed GCD-clean candidates. There are two modes:

Fast mode:
```bash
EVAL_FAST_REJECT=1 ./island.sh validate "<CFG>" <nonce> [<nonce>...]
```

Full mode:
```bash
EVAL_FAST_REJECT=0 ./island.sh validate "<CFG>" <nonce> [<nonce>...]
```

Interpret `cls / pha / anc` as counts of sampled violations:

- `cls`: classical constraint failures
- `pha`: phase constraint failures
- `anc`: dirty ancilla failures

A clean island is:

```text
0 / 0 / 0
```

Useful near misses are typically low single digits, such as `2 / 2 / 0`, `4 / 3 / 0`, or `5 / 0 / 0`.

### Stop Rules

Mark a route RED and stop extending it when:

- The first 16 validated candidates all share the same high dirty fingerprint.
- Any uniform fingerprint has very high severity, especially values like `9024 / 141 / 0`.
- After 64 validated candidates, no candidate has severity `<= 10`.
- After 100-200 candidates, median severity is still high and there is no near-miss tail.

Continue a route when:

- Score still beats SOTA.
- Candidate density is GREEN, or YELLOW with promising validation.
- There is at least one near miss with severity `<= 10`.
- Failure fingerprints vary across candidates instead of repeating structurally.
Exact equality is common on dirty candidates but is not required. Any invariant violation is serious; report the offending nonce and both triples prominently.

## Remote Validation Hygiene

Prefer remote parallel validation for large batches because local CPU validation is slow.

Before trusting remote validation in a heartbeat or batch:

1. Sample at least two recent GCD-clean candidates.
2. Validate them locally in fast modes.
3. Validate the same candidates remotely in fast modes.
4. Require exact local/remote agreement before using remote results.

After rebuilding or refreshing remote validators, require a fixed acceptance set to match local exactly before trusting the node. Keep remote validator binaries aligned with the active CFG. A stale validator can silently invalidate the experiment.

## GPU Scan Operations

Use the safer fast GPU prefilter settings unless the user specifies otherwise:

```bash
GPU_BATCH_INV=1 \
GPU_COMB_BITS=22 \
GPU_GCD_MODE=trunc_first \
GPU_FAN_BITS=22 \
GPU_WAVE=128 \
./island.sh search s.bin <START> <N>
```

Assign contiguous, non-overlapping ranges across GPUs. Track per node:

- range and current chunk
- processed nonces
- nonce/s
- candidates found
- candidate density
- process age
- GPU utilization
- ETA

If a GPU becomes idle and the route still beats SOTA, start the next obvious unassigned 20M or 40M range. Report the new range and session.

Watch for suspicious nodes. For example, a GPU scanning tens of millions of nonces with zero candidates while other nodes show normal density may indicate a stale state file, wrong binary, logging issue, or pathological range. Inspect before extending that node repeatedly.

## Reporting Format

For heartbeat-style progress reports, include:

- latest promoted SOTA and active estimated score
- active/idle GPU count
- aggregate nonces/s and per-GPU rates when estimable
- completed/scanned nonces
- estimated in-flight nonces
- remaining assigned window
- highest assigned frontier
- total GCD-clean candidates
- candidate density
- ETA for assigned ranges
- expected time to next GCD-clean candidate
- validator cross-check status
- validation summary and compact near-miss table
- any new ranges started
- any suspicious node or route-triage decision

Keep reports concise. Surface the best near misses and anomalies rather than dumping every dirty candidate.

## Clean Solution Handling

If any full validation returns `0 / 0 / 0`:

1. Bake the CFG and nonce into the challenge repo.
2. Run the normal benchmark/check.
3. Pull latest SOTA again.
4. Compute measured score from benchmark output.
5. Submit only if measured score beats current promoted SOTA, unless the user explicitly instructs otherwise.
6. Push the validated circuit to the requested challenge repo branch if requested.

Do not commit temporary scan configs, logs, helper binaries, remote scripts, `ops.bin`, or generated artifacts unless they are explicitly part of the validated challenge solution.

## Route Comparison Heuristic

When choosing among multiple candidate routes, use the **Route Bake-Off** above to collect equal-size
pilot evidence, then make a qualitative engineering judgment. Do not summarize route quality into a
single rigid formula. Prefer routes with several independent healthy signals; stop routes with strong
structural-failure evidence even if one metric looks good.

Prefer routes that have:

- lower estimated score than SOTA
- enough score margin to survive final measurement drift or a small SOTA movement
- healthy GCD-clean density
- low single-digit near misses
- diverse dirty fingerprints
- stable fast/full and local/remote validation
- mostly classical residuals rather than persistent phase or ancilla dirt
- failures that localize late or vary by nonce instead of breaking early core algebra
- consistent behavior across nodes and separated nonce ranges
- nearby safer variants that improve smoothly
- a structural change that plausibly affects the measured peak owner

Avoid routes that have:

- score at or above SOTA
- score margin so small that final measurement drift would likely lose
- starved candidate density
- repeated high dirty triples
- no severity `<= 10` after dozens of candidates
- stale validator or CFG uncertainty
- suspicious per-node behavior that cannot be explained
- persistent `pha`/`anc` residuals across otherwise promising candidates
- uniform failure localization in an early GCD/apply, carry-cleanup, or phase-discharge section
- qubit savings in a non-peak phase only
