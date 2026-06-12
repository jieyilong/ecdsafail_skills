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
each and rank them by how likely they are to land an island. Then hunt the most promising route
first; only fall back to the next-ranked route if the leader is exhausted or fails its stop rules.

Two signals predict island findability, and they multiply:

1. **GCD-clean candidate density** — higher density means more shots on goal. A route producing
   2x the candidates per nonce reaches any given island count in half the nonces.
2. **The `cls / pha / anc` distribution of those candidates** — *how close* a typical GCD-clean
   candidate is to a clean island. A clean island is `0 / 0 / 0`; a candidate at `(1, 2, 0)` is a
   few constraint-bits away, while `(4, 5, 1)` is far away. Because each residual violation must
   independently vanish on the reachable verifier support, the chance a candidate is fully clean
   **falls off steeply (roughly geometrically) as its residual grows.** So a route whose candidates
   cluster at `(1, 2, 0)` is exponentially more likely to yield an island than one clustering at
   `(4, 5, 1)`, even at the same density.

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

### Ranking metric

The single best predictor is the **estimated island rate per nonce**, which you read off the low
end of the histogram:

```text
island_rate(route) ~= GCD_clean_density * P(candidate is clean | GCD-clean)
```

Estimate `P(clean | GCD-clean)` from the near-miss tail. In practice rank by this proxy
(higher = hunt first):

```text
landability = GCD_clean_density * (fraction of GCD-clean candidates with severity <= 2)
```

This rewards both axes the user cares about: dense candidates AND candidates that sit close to
`0 / 0 / 0`. If the histogram is clean enough to see a geometric fall-off (e.g. counts at
sev = 1, 2, 3 in a roughly constant ratio `r`), extrapolate the tail down to sev = 0 to estimate
the island density directly — that is the most principled rank key. The `severity <= 2` fraction
is the no-fit fallback.

Tie-breakers and adjustments, in order:

- Prefer the route with the **lower mean/median severity** — a route whose mass is at `(1, *, 0)`
  beats one at `(3, *, 0)` even if the `<=2` fractions are close.
- **Penalize nonzero `pha` and `anc`.** Classical (`cls`) residuals are what nonce hunting most
  directly drives to zero; persistent `pha`/`anc` across candidates is usually a structural defect
  that no nonce will fix (see Stop Rules). A route at `(1, 0, 0)` ranks well above `(1, 0, 1)`.
- Penalize routes whose near-misses all share **one identical fingerprint** (no diversity) — that
  is a structural near-miss, not a distribution you can search through.

### Worked example

| route | density (c/Mn) | sev<=2 frac | typical triple | landability | decision |
|-------|---------------:|------------:|----------------|------------:|----------|
| A | 0.8 | 0.45 | `(1, 2, 0)` | 0.36 | hunt first |
| B | 1.6 | 0.10 | `(4, 5, 1)` | 0.16 | hunt second |
| C | 0.3 | 0.50 | `(2, 0, 0)` | 0.15 | hold |
| D | 1.2 | 0.05 | `9024 / 141 / 0` | 0.06 | drop (structural) |

Route B has the highest raw density but its candidates sit far from clean, so A — fewer but much
closer candidates — is the better first hunt. D is dropped outright on the uniform high fingerprint
regardless of density.

### Cost discipline

The bake-off is a **comparison**, not a hunt. Keep each pilot to the 5-10M band and stop as soon as
the ranking is clear — if one route is an order of magnitude better on landability after a few
million nonces, commit GPUs to it rather than finishing equal pilots on the obvious losers. Re-run a
fresh bake-off whenever the base circuit changes (a new SOTA base reseeds every route's inputs).

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

When choosing among multiple candidate routes, the quantitative method is the **Route Bake-Off**
ranking above (rank by `landability = GCD_clean_density * fraction with severity <= 2`, tie-broken by
mean severity and `pha`/`anc` penalties). The qualitative checklist below is the same idea in
prose — use it to sanity-check the ranking and to judge a single route in isolation.

Prefer routes that have:

- lower estimated score than SOTA
- healthy GCD-clean density
- low single-digit near misses
- diverse dirty fingerprints
- stable fast/full and local/remote validation

Avoid routes that have:

- score at or above SOTA
- starved candidate density
- repeated high dirty triples
- no severity `<= 10` after dozens of candidates
- stale validator or CFG uncertainty
- suspicious per-node behavior that cannot be explained
