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

3. Start with a short triage scan, not a large frontier burn.
4. Use GCD-clean candidate density and `cls / pha / anc` statistics to classify the route.
5. Extend only routes that pass score, density, and validation gates.
6. Validate every newly flushed candidate in fast modes.
7. Submit only measured clean solutions whose score beats current promoted SOTA, unless the user explicitly gives different submission rules.

## Score Gate

Before scanning, compare the estimated score against current promoted SOTA.

- If `estimated_score >= SOTA_score`, do not start a large island search.
- If a later heartbeat finds a new SOTA that beats or ties the active estimate, keep already-running scans unless told to stop, but do not extend the route.
- Resume structural or Toffoli optimization before assigning new GPU ranges.

Use measured benchmark output for final score decisions. Estimated score is only a pre-scan gate.

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
