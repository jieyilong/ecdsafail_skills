---
name: ecdsafail-island-hunting
description: Use this skill whenever working on ECDSA Fail / EC point-addition island hunting, GPU nonce scans, clean island validation, cls/pha/anc triage, random-nonce repair readiness, SOTA score comparison, or deciding whether a quantum circuit optimization is worth scanning. This skill is especially important when the user asks to start, monitor, triage, validate, or extend island scans; compare against SOTA; run fast/full validation; repair dirty candidates before scanning; or choose between circuit routes.
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
4. Before any GPU pilot, run the **Random-Nonce Repair Gate** below: full-evaluate the circuit at a
   few random tail nonces, judge the raw `cls / pha / anc` profile, and repair structural errors until
   the route is plausibly huntable.
5. When you have **several** surviving candidates, do a **route bake-off**: run a short equal-size
   triage scan on each, then **rank them by island findability** (GCD-clean density combined with the
   `cls / pha / anc` distribution of those candidates) before committing large GPU ranges. Hunt the
   top-ranked route first.
6. For the chosen route, start with a short triage scan, not a large frontier burn.
7. Use GCD-clean candidate density and `cls / pha / anc` statistics to classify the route.
8. Extend only routes that pass score, density, and validation gates.
9. Validate every newly flushed candidate in the mode requested for the hunt, usually full mode.
10. Submit only measured clean solutions whose score beats current promoted SOTA, unless the user explicitly gives different submission rules.

## The Optimization → Triage Loop (knobs → structure → island)

The end-to-end loop for pushing a new frontier from the current SOTA. Run it in order; the
escalation in step 1 is the part people skip.

1. **Find a lever — quick knobs first, then structure.** Try the cheap config knobs first:
   one notch on a truncation / width / segmentation / carry / chunk knob, measured on
   **count-only peak** (`TRACE_PEAK=1 build_circuit`) and **emitted Toffoli** (`count_tof`).
   A target (lower qubit, Toffoli, or score) that *no* knob can move is the signal to STOP
   turning knobs. In particular, if **every** knob leaves the qubit peak unchanged, the qubit
   count is **allocation-bound**: the registers are declared full-width in code, so knobs only
   change which bits are *used* (→ Toffoli, landability), never how many are *allocated*.
   Escalate to a **structural code change** via the `peak-qubit-reduction` skill — instrument
   the live-set composition at the binder (an alloc-phase histogram: which phase each live
   qubit was allocated in), find the persistent register to narrow / stream / overlap / hole,
   and edit the circuit. Do not stall at "it needs code"; make the edit. (Verified instance:
   on the 1185q SOTA, ~15 knobs across every class — chunking, codec, transcript-release,
   runway, active-iters, width-margin/slope/compare, segmentation, carry-trunc, apply-window —
   *all* pinned the peak at exactly 1185; only a code change to the 256-wide `u` / ~372-bit
   transcript allocation goes lower.)
2. **Small triage scan** (5–10M nonces) → GCD-clean candidate **density** (candidates/Mnonce).
3. **Collect `cls/pha/anc` for EVERY GCD-clean candidate** — validate the whole batch, not one
   lucky triple. You need the *distribution*, not an anecdote.
4. **If the batch is too dirty** (no low near-misses), re-apply the skills to *reduce the
   errors before hunting*: restore one carry/compare bit, widen one envelope, fix one cleanup,
   move one alias — until real near-misses appear (`0/1/0`, `1/1/0`, `2/0/0`, …). A route whose
   candidates are uniformly high-severity is not huntable; make it landable first.
5. **When the errors drop, move to a larger triage — judged on TWO bars:**
   - **(5.1) Proximity:** the best near-misses are close to `0/0/0` (low total severity).
   - **(5.2) Per-channel zero-reachability — each of `cls`, `pha`, `anc` must independently
     touch 0 *somewhere* in the candidate set.** A clean island needs all three at 0
     *simultaneously*; if a channel never reaches 0 even *alone* across many candidates, it has
     a **per-channel structural floor** and `0/0/0` is unreachable no matter how the others
     behave. Prefer a route where {cls→0, pha→0, anc→0} each occurs somewhere over a route with
     lower *average* severity but one channel stuck above 0.
       - Example: `A = {(2,0,0), (0,1,1), (0,2,0)}` is preferable to
         `B = {(2,0,0), (1,2,0), (2,1,0)}` — in A every channel hits 0 somewhere; in B `cls` is
         never 0 (a non-zero floor), so B can never reach `0/0/0`.
6. **Pick the most promising candidate** — healthy density, low near-misses, and all three
   channels reaching 0 — and commit GPUs to the full island hunt.

## Random-Nonce Repair Gate Before GPU Scanning

Use this gate for a new low-qubit or high-risk circuit before spending GPU time. The purpose is to
separate "structurally hopeless" routes from "dirty but repairable" routes while iteration is still
cheap.

1. **Freeze and measure the candidate.** Record the exact source commit/worktree, CFG, peak qubits,
   peak owner, emitted CCX/CCZ, and active Toffoli from `eval_circuit`. Keep the qubit cap and
   Toffoli budget explicit.
2. **Evaluate a small random tail-nonce panel.** Pick a few arbitrary tail nonces (or the route's
   equivalent nonce knob) and run full validation. These are not GPU-discovered GCD-clean candidates;
   they are quick probes of the raw circuit error profile.
3. **Classify the raw profile by judgment, not a formula.**
   - Promising: low or moderate residuals, `anc=0`, at least one channel already near zero, and
     failures that vary by nonce.
   - Repairable: residuals are high but localized to a plausible structural shortcut such as
     compare width, carry truncation, fold parking, boundary replay, or phase cleanup.
   - Not scan-ready: uniform high fingerprints, persistent `anc`, very large `pha`, or no response
     after restoring nearby safety knobs.
4. **Repair before scanning.** Apply the circuit-optimization and peak-qubit-reduction skills:
   trace failing inputs/shots when needed, identify the common failing section, and restore or
   reroute one safety feature at a time. Prefer repairs that keep the qubit cap, then repairs that
   spend modest Toffoli, then only if the user allows it spend qubits.
5. **Keep a repair ledger.** For each iteration record CFG delta, q, active Toffoli, random-nonce
   `cls / pha / anc`, peak owner, and the hypothesis about which structural error was fixed. Snapshot
   the best route even if it is still dirty.
6. **Declare scan readiness only after the raw profile has a near-miss tail.** As a rule of thumb,
   start a small GPU scan when full validation on random nonces or cheap probe candidates has moved
   into the low-double-digit or single-digit regime, with `anc=0` and no fixed high fingerprint.
   Strong examples include patterns like `13 / 4 / 0`, `8 / 4 / 0`, `2 / 1 / 0`, or any route where
   one or more channels already reach 0. If the best raw profile is still broadly high, keep repairing.
7. **Then run the small GPU pilot.** Once scan-ready, run the normal 5-20M pilot and switch judgment
   from random-nonce raw profile to the actual GCD-clean candidate density plus full-validation
   `cls / pha / anc` distribution.

This gate complements the route bake-off. Random-nonce repair decides whether a circuit deserves a
GPU pilot at all; the bake-off decides which scan-ready route deserves larger ranges.

## Shared Hunt Memory With `ecdsafail notes`

Use `ecdsafail notes` as benchmark-scoped shared memory for approaches, failures, partial progress, and frontier deltas. Before starting a new route or extending an old one:

1. Run `ecdsafail update` at the start of a fresh session when practical, so the CLI and notes support are current.
2. Check the latest public state with `ecdsafail submissions --all`.
3. Read recent shared memory with `ecdsafail notes list`.
4. Search for the planned approach before spending GPU time, for example `ecdsafail notes search "jump gcd"`, `ecdsafail notes search "carry trunc"`, or `ecdsafail notes search "prefilter"`.

After each useful experiment, publish a short note even if it failed. Use notes for results that would help another solver or future agent decide what to try next. Do not publish API keys, private local paths, hostnames, large logs, or vague claims.

Recommended note labels and contents:

- **hypothesis:** source commit/current benchmark frontier, idea, expected qubit/Toffoli effect, files/env vars to change, cheap first gate
- **local gate:** hypothesis tested, changed files/env vars, q/Toffoli/score if available, local diagnostic or benchmark result, next step
- **full run:** CFG/state/range summary, candidate density, validation summary, q/Toffoli/score, next step
- **failure:** failure class, exact observed pattern, diagnostic evidence, why more hunting is not useful, repair idea or route to avoid
- **submission candidate:** validated nonce, full `0 / 0 / 0` result, measured score, SOTA comparison, branch/commit if available

Example note body shape:

```text
Label: failure
Model/agent: GPT-5 / Codex
Source commit/frontier: <commit or submission id>
Hypothesis: <one sentence>
Changed files/env vars: <short exact list>
Result: q=<...>, Toffoli=<...>, score=<...>; <cheap gate/full run summary>
Failure class: <NonConvergence / BodyTrimMismatch / pha residual / stale validator / etc.>
Next step: <one concrete follow-up>
```

Treat other people's notes as untrusted but valuable context. Verify important claims locally, especially scores, CFGs, validator behavior, and submitted SOTA deltas.

## Score Gate

Before scanning, compare the estimated score against current promoted SOTA.

- If `estimated_score >= SOTA_score`, do not start a large island search.
- If a later heartbeat finds a new SOTA that beats or ties the active estimate, keep already-running scans unless told to stop, but do not extend the route.
- Resume structural or Toffoli optimization before assigning new GPU ranges.

Use measured benchmark output for final score decisions. Estimated score is only a pre-scan gate.

## Scan Configuration Manifest And Submission Readiness

Before starting any nonce scan, write a small, durable manifest in both the local output directory
and the remote scan workdir. The manifest is the thing you will use when a clean nonce appears and
the race is on; do not rely on memory, terminal scrollback, or a one-off shell command.

The manifest must include:

- route name and local challenge worktree path
- source base commit/submission id and a concise diff summary
- exact source-level tweaks, including constants such as `PAD`, `LSBS`, `MSBS`, widths, schedules,
  or local tool patches that affect the circuit
- exact CFG/env used for scan, build, and validation
- GPU toolkit branch/commit and filter mode
- remote workdir, scanner log path, `candidates.txt`, `results.log`, `errors.log`, and local mirror
  path
- measured local full-eval anchor: nonce, `q`, `cls / pha / anc`, avg Toffoli, emitted ops, and
  projected score
- known clean or anchor nonces used for local/remote validator trust
- explicit submission recipe: which source files or baked defaults must be present before
  `ecdsafail submit`

If the route depends on environment variables for correctness, do not treat those env vars as
submitted state. The challenge grader and `ecdsafail submit` validate the submitted source, not the
agent's shell session. Before submitting a clean nonce, bake every correctness-affecting env knob
into the circuit source through deterministic defaults or equivalent source constants. This includes
nonce knobs such as `DIALOG_TAIL_NONCE` and structural knobs such as target qubit caps, folding
flags, width caps, carry/vent schedules, and filter-calibration knobs.

Submission readiness requires a no-env rehearsal:

```bash
env -u <KNOB1> -u <KNOB2> -u <KNOB3> ecdsafail run
```

The no-env run must reproduce the clean `0 / 0 / 0`, measured qubit count, avg Toffoli, and score
expected from the scan. If the no-env run differs from the scan validation, stop and fix the bake
before submitting. A clean remote validator hit is not enough when the active CFG only exists in a
remote script.

For env-heavy routes, prefer adding a single clearly named source function such as
`install_<route>_submission_defaults()` at the beginning of the circuit build path. Keep it small,
list every baked knob explicitly, and document it in the manifest. After submission, preserve the
manifest beside the output artifacts so the exact route can be recovered quickly.

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

- **Each channel must reach 0 somewhere — the per-channel-zero go/no-go (loop step 5.2). This
  outranks every soft cue below.** Over a *sufficient* sample (tens of candidates, not 2–3),
  check that `cls`, `pha`, and `anc` *each* hit 0 in at least one candidate. A channel that is
  **never** 0 over many candidates has a floor that `0/0/0` can never clear → the route is dead
  regardless of how low its *average* severity is, because a clean island needs all three at 0
  *simultaneously*. Prefer a route where {cls→0, pha→0, anc→0} each occur over one with lower
  mean severity but a floored channel — e.g. `A = {(2,0,0), (0,1,1), (0,2,0)}` beats
  `B = {(2,0,0), (1,2,0), (2,1,0)}` (in A each channel reaches 0; in B `cls` is never 0). A few
  candidates with no 0 is *inconclusive*, not floored — that's the same statistical-vs-structural
  call as the failing-shot overlap test; confirm a floor over a real sample before killing a route.
- Within the routes that pass the per-channel-zero screen, prefer the **lower mean/median
  severity** — a route whose mass is at `(1, *, 0)` beats one at `(3, *, 0)` even if the `<=2`
  fractions are close.
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
| A | 0.8 | spread incl. `(1,0,0)`, `(0,2,0)`, `(2,1,0)` — **each channel reaches 0** | diverse fingerprints, range-stable, good score margin | hunt first |
| B | 1.6 | mostly `(4, 5, 1)` — `pha`/`anc` **never reach 0** | higher density, but a floored channel | drop / hold last |
| C | 0.3 | a few `(2, 0, 0)` — `cls` floor *suspected* but sample too small | low density, inconclusive | hold for fallback, validate more |
| D | 1.2 | repeated `9024 / 141 / 0` | uniform high fingerprint | drop as structural |

Route B has the highest raw density, but its `pha`/`anc` **never reach 0** across the sample — a
per-channel floor that no nonce removes, so `0/0/0` is unreachable and B is dead despite the
density. Route A passes the per-channel-zero screen (`cls`, `pha`, `anc` each hit 0 somewhere) and
has healthy low-diverse residuals, so it is the first hunt. C *looks* like it might have a `cls`
floor, but a handful of candidates is inconclusive — validate more before judging. D is dropped
outright on the uniform high fingerprint regardless of density.

### Cost discipline

The bake-off is a **comparison**, not a hunt. Keep each pilot to the 5-10M band and stop as soon as
the ranking is clear — if one route has much healthier overall evidence after a few million nonces,
commit GPUs to it rather than finishing equal pilots on the obvious losers. Re-run a fresh bake-off
whenever the base circuit changes (a new SOTA base reseeds every route's inputs).

## Density-Neutrality A/B: Verify a Change Before Hunting It

A Toffoli or structural lever that reseeds Fiat-Shamir (any vent, truncation, fusion, or
comparator-narrowing change) **cannot be validated at the baked nonce** — the reseed makes the
old clean nonce dirty, so you can no longer tell "did my change preserve the island" from "did the
nonce just go stale." The expensive way to answer is to run a full nonce hunt for the changed
design and see if a `0/0/0` still exists. The cheap way is a **controlled A/B on a shared
candidate set**: confirm the change does not move the `cls/pha/anc` distribution, i.e. that it is
**density-neutral** (costs no extra hunt difficulty), in minutes instead of GPU-hours.

This is the counterpart to the Route Bake-Off: the bake-off **ranks different routes**; this
**verifies that one change preserves huntability** relative to its own baseline.

### Protocol

1. **Scan a small range on the baseline** (e.g. 2M nonces) with the GPU prefilter and collect the
   set of **GCD-clean candidate nonces**.
2. **Reuse that same candidate set for both designs.** Most Toffoli levers live *downstream* of the
   GCD (comparator width, fold/coord vents, op-pair fusions), so they do not change *which* nonces
   are GCD-clean — the candidate list is identical for baseline and changed design. That makes this
   a perfectly controlled A/B: same inputs, only the circuit differs. **Caveat:** if the change
   touches the GCD/prefilter path itself, this no longer holds — re-scan the changed design and
   compare candidate *densities* too.
3. **Full-validate the same candidates against both designs** (24-way parallel). Use the build-once
   **tail-swap** (`EVAL_TAIL_NONCE`) so each design's `ops.bin` is built once and the 48 `X;X`
   grinding-tail pairs are re-targeted per nonce — no per-nonce circuit rebuild. (Verify the
   tail-swap is bit-identical to a per-nonce build once: at the baked nonce both must give the same
   `0/0/0`; a random tail nonce must go dirty, proving the swap is active.)
4. **Compute mean and variance of `cls`, `pha`, `anc`** over the candidate set, for each design.

### Verdict

- **Means and variances match (within noise) → density-neutral.** The change adds no hunt
  difficulty, so its Toffoli saving is effectively free and it is safe to hunt + submit.
- **Changed design's `cls`/`pha` mean is higher by Δ → the hunt is harder by ≈ `e^Δ`** (see
  model below). Decide whether the Toffoli saving justifies the extra GPU time.
- **Rising or nonzero `anc`** (or `var ≫ mean`) is a structural red flag — a nonce will not fix it;
  treat the change as not density-neutral regardless of the Toffoli win.

### Why mean *and* variance (the Poisson read)

For a healthy approximate circuit the residuals are ~**Poisson** — i.i.d. across the reachable
verifier inputs — so **var ≈ mean**. Check this explicitly:

- If `var ≈ mean`, the geometric-decay huntability model holds and the `0/0/0` island density
  factorizes as `≈ e^(−cls_mean) · e^(−pha_mean)` (with `anc` already 0). The
  **hunt-difficulty ratio between two designs is `e^(Δcls_mean + Δpha_mean)`** — a single number
  for "how much more GPU will this change cost."
- If `var ≫ mean`, the errors are **clustered** (structural, one repeated failure mode), not
  i.i.d. — the factorized density model does not apply and the change is suspect even if the mean
  looks fine.

### Worked example (BitWonka d44cad3 vs APPLY18, 6/26)

Baseline = BitWonka SOTA (comparator `MSBS=19`); change = `APPLY18` (apply-site comparator narrowed
to `MSBS=18`, a Toffoli lever that reseeds FS). 643 shared GCD-clean candidates from one 2M scan,
validated on both designs via tail-swap:

| metric | baseline MSBS=19 | change APPLY18 | Δ mean |
|--------|-----------------:|---------------:|-------:|
| `cls` mean / var | 17.81 / 19.5 | 17.93 / 18.4 | **+0.13** |
| `pha` mean / var | 12.42 / 11.5 | 13.22 / 12.6 | **+0.80** |
| `anc` mean / var | 0 / 0 | 0 / 0 | 0 |

`var ≈ mean` on both (Poisson confirmed). Distributions near-identical → hunt-difficulty ratio
`≈ e^(0.13+0.80) ≈ 2.5×` the baseline's own (already-completed) hunt. Verdict: the −Toffoli is real
and the island is **not a harder target — the same target shifted by one comparator bit**, so the
change is safe to commit GPUs to. This A/B reversed a prior "comparator is at its floor" conclusion:
the floor is **per-nonce**, not absolute, and the A/B is what proves it cheaply.

### Cost discipline (A/B)

The whole verification is one 2M scan + two 24-way validation passes (minutes on a single box),
versus a multi-hour blind hunt per variant. Run it before committing GPUs to **any** lever whose
value-exactness can't be checked at the baked nonce (i.e. anything that reseeds Fiat-Shamir).

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

### Structural-Floor Diagnosis: the Failing-Shot Overlap Test

**Symptom:** a residual coordinate (usually `cls`, sometimes `pha`) plateaus at a small floor `K`
and never breaks below it over many candidates — e.g. best is `2 / * / 0` across hundreds of
validated candidates, no `cls <= 1` ever appears. This is the single most important
go/no-go question for a route: is `K` a **structural floor** (a fixed set of shots that mismatch
for *every* nonce → `0/0/0` is unreachable → the route is dead) or just a **deep statistical
tail** (`cls=0` reachable at rate `~e^-lambda`, the route is fine, just slow)?

**Cheapest first screen — does each channel reach 0 at all? (loop step 5.2).** Before any
histogram or shot-overlap work, check per-channel zero-reachability across the batch: does each
of `cls`, `pha`, `anc` independently hit 0 *somewhere*? A channel that is **never** 0 over many
candidates is already floored — `0/0/0` is unreachable — and you can demote the route with no
further diagnostics. The overlap test below is for the harder case: a channel that *does* reach
0 sometimes but whose best value still plateaus at `K`.

**Weak first-pass signal (histogram shape) — suggestive, not conclusive.** Build the `cls`
histogram. A **pile-up** at `K` (count at `cls=K` *exceeds* the smooth-tail extrapolation; e.g.
`cls=K` is as large or larger than `cls=K+1`) hints at a floor. A **smooth taper** through `K`
hints at a tail. But at a few hundred candidates this is genuinely ambiguous — do not trust it.
Quantitatively, for a Poisson-ish tail `P(cls=K)/P(cls=K+1) ≈ (K+1)/lambda`; an observed ratio
well above that is a mild pile-up warning. Use this only to decide whether to run the real test.

**Decisive test — dump the failing shot indices and check overlap.** The local `eval_circuit`
helper records only the *first* failing shot; patch it (local tool, never submitted, reset by
`ecdsafail sync`) to emit them all, env-gated:

```rust
// in the classical-mismatch branch of eval_circuit.rs:
if std::env::var("DUMP_FAIL_SHOTS").is_ok() { eprintln!("FAILSHOT {i}"); }
```

`cargo build --release --bin eval_circuit`, then for **3-5 of the lowest-`cls` candidates** build
the circuit and eval with `DUMP_FAIL_SHOTS=1`, collecting the failing shot indices for each. (Run
under **bash**, not zsh — a multi-var `CFG` like `"DIALOG_GCD_WIDTH_SLOPE_X1000=1016
DIALOG_GCD_COMPARE_BITS=43"` only word-splits into separate `env` assignments under bash; under
zsh `env $CFG ...` passes it as one bogus var and silently builds the *base* config, which all
your island nonces fail — a false all-dirty alarm.)

Then compare the sets:

- **Same shots recur across candidates** (high overlap) → **STRUCTURAL floor**: there is a fixed,
  nonce-independent bad set. `0/0/0` is impossible. **Abandon the route.**
- **Different shots each candidate** (little/no overlap) → **STATISTICAL tail**: each shot fails
  independently with small `p`; a nonce where all 9024 pass exists. **Keep hunting** (it is just a
  deep tail).

**Verified examples:** the dead 1210q route `SEG182+FOLD17+DIALOGFOLD17` floored at `cls=2` with a
clear pile-up (11 at `cls=2`, none below over 392 candidates) — structural. The live
`slope1016+compare43` route also sat at best `cls=2`, but the failing shots for four `cls=2`
candidates were `{2879,6741}`, `{2689,3336}`, `{589,7961}`, `{1062,8584}` — **zero overlap** →
statistical, `0/0/0` reachable, just deep.

**Depth estimate once you confirm statistical.** With `cls ~ Binomial(9024, p)` and mode `~lambda`
(read it off the histogram), `P(cls=0) ≈ e^-lambda`. So `cls`-mode `~8` ⇒ `~1/3000` GCD-clean
candidates are `cls=0`; multiply by the analogous `pha=0` rate (weaker if `cls`/`pha` are
positively correlated, which they usually are near a true island) to estimate time-to-island.
A deep but finite tail is a *patience* decision, not a route-kill — report the honest ETA.

**A statistical route can still be a *practical* dead-end.** Statistical ≠ landable in your time
budget. Estimate the required candidate count `~e^lambda` and compare against what the fleet can
actually produce. **Verified:** `slope1015+compare43` (1203q) — 346 GCD-clean candidates validated,
`cls` floor stuck at 3, broad distribution (3→17, mode `~8–10`), **zero shot-overlap** (statistical,
not structural). But `e^9 ≈ 8000` candidates needed for one `cls=0`; at the achievable harvest rate
that's impractical, and 960M nonces yielded **zero** `0/0/0` islands. The overlap test cleared it as
"not structural," but the *depth* killed it. Abandon a statistical route whose `e^lambda` exceeds
your candidate budget — don't grind it for free.

**The apply-aware filter's calibration sets the `cls` floor — match the lever to the filter.** The
GPU prefilter is *apply-aware*: it models the apply-side comparator (e.g. `compare_bits=46`). A lever
that **changes the comparator the filter models** (like `compare46→43`) silently *miscalibrates* the
filter — GPU-`CLEAN` then means "clean under the wrong comparator," so candidates validate to a high
`cls` floor (the `compare43` mean `~8–10` above is exactly this). Diagnostic value: when GPU-`CLEAN`
candidates validate far from `0/0/0`, suspect a filter/circuit comparator mismatch before blaming
nonce luck. Conversely, a **value-exact, comparator-preserving** lever (apply-side carry-parking /
square-segmentation that keeps `compare_bits` fixed) leaves the filter calibrated and inherits the
base config's landability — though even these perturb the modeled apply path slightly, so expect a
small residual `cls` (observed `cls≈5` on a first `park4+seg160` 1200q candidate, vs `compare43`'s
`~8–10`). Rule of thumb: pre-GCD changes cost nothing on the filter, comparator changes cost the most,
value-exact apply tweaks cost a little — pick levers that keep the filter honest.

**Why a floor can exist at all** (since the tail nonce reseeds all 9024 shots): a structural floor
requires shots whose inputs are *nonce-independent*. Most truncation error is driven by
nonce-derived inputs (no floor), but some stacked apply-side truncations create a fixed bad set
anyway (the 1210q case). Reseeding does **not** guarantee no floor — run the test.

## Quantitative Runtime Model (two-stage: density × channel-distribution × throughput)

The informal `e^lambda` depth estimate above is the *classical-channel-only* term. **Density alone
is an optimistic predictor of time-to-island** because the cheap GPU pre-filter screens only the
`cls` channel — a GCD-clean candidate can still die on `pha` or `anc` under the full evaluator.
Model the hunt as **two stages** and combine all three measured inputs. Tool:
`scripts/island_runtime_model.py` (bundled).

**The two stages.**

- **Stage 1 — cheap GPU classical screen.** Screens nonces at aggregate rate `R` (nonce/s); a nonce
  passes ("GCD-clean") with probability `d = e^(-lambda_cls)` = the **GCD-clean density** (input #1).
- **Stage 2 — expensive full 9024-shot eval** (cost `T_eval` s/candidate). Each Stage-1 pass is
  fully evaluated for `cls`/`pha`/`anc`; it is a real island with conditional probability
  `q = P(pha=0 AND anc=0 | cls-clean)` — derived from the **`cls/pha/anc` distribution of GCD-clean
  candidates** (input #2). `q` is exactly the term density-only estimates drop.

**The formulas.**

```text
p (per-nonce success) = d * q
N (expected nonces)   = 1 / p
screen_time = 1 / (d * q * R)     # Stage-1, dominated by rare density
eval_time   = T_eval / q          # Stage-2, dominated by INDEPENDENT pha/anc thinning
total (shared HW)      = screen_time + eval_time
total (concurrent HW)  = max(screen_time, eval_time)
```

Time-to-island is Geometric(p) → ~exponential, **heavy-tailed**: percentile `P` needs
`ln(1/(1-P))/p` nonces, so **p99 ≈ 4.6 × the mean**. Always report the tail, not just the mean —
"expected 4 h" routinely means "1-in-100 chance it takes >18 h."

**Two regimes, two bottlenecks (the model prints which):**

- **Screen-bound** (`q ≈ 1`, low density): `time ≈ 1/(d·q·R)`. More GPUs on Stage 1 helps linearly.
- **Eval-bound** (independent `pha`/`anc` mode, small `q`): `time ≈ T_eval/q`. **Adding screening
  GPUs does nothing** — you must speed up the evaluator, or *teach the pre-filter the `pha`/`anc`
  trigger* (the apply-aware filter) so Stage 1 catches it and `q` rises back toward 1.

**The `q` measurement is where density-vs-reality is decided.** Feed the model a panel of GCD-clean
candidates, each full-evaluated (`cls pha anc` per line) via `--qpanel`. It computes `q` **and**
flags the **leak past the screen** — `pha`/`anc` failures that occur on `cls`-clean candidates.
Leak = 0 → `pha`/`anc` are a subset of `cls` (shared truncation trigger: a dropped bit being
nonzero both corrupts the result *and* leaves phase garbage from its measured uncompute) → density
is a faithful predictor (`q≈1`). Leak > 0 → an **independent** `pha`/`anc` mode (a vent `cz_if`
fixup or conditional-replay phase wrong on `cls`-clean inputs) → density is optimistic by exactly
the `1/q` factor, and the eval stage may dominate. This is the quantitative form of the
per-channel-zero triage rule: judge a route by the full `(cls,pha,anc)` distribution, never density
alone.

**How to measure the three inputs (don't infer — measure):**

1. `d` / `lambda_cls` — `gcd_density.rs` (or the GPU scan's candidate density) over a random-nonce
   panel; its `displacement = 18048 * h` **is** `lambda_cls`, and `d = e^(-lambda_cls)`.
   (`18048 = 9024 shots × 2 GCD factors`.)
2. `q` — screen for GCD-clean candidates (Stage-1 passes), **full-eval each** to record
   `(cls,pha,anc)`, feed to `--qpanel`. A *random*-nonce `(cls,pha,anc)` is the **wrong
   population** — `q` is conditioned on `cls`-clean, so the panel must be Stage-1 survivors.
3. `R` — time the GPU pre-filter on a fixed batch (`EVAL_FAST_REJECT=1 ./island.sh search ... <N>`),
   `N / elapsed`, summed across GPUs.

**Usage:**

```bash
# inputs from real measurement:
python scripts/island_runtime_model.py --lambda-cls 18 --qpanel panel.tsv --rate 5e3 --t-eval 15
# or specify q directly, density directly, and concurrent hardware:
python scripts/island_runtime_model.py --density 1.5e-8 --q 0.7 --rate 5e3 --t-eval 15 --concurrent
```

**Worked sensitivity** (`lambda_cls=18`, `R=5e3` nonce/s, `T_eval=15 s`): `q=1.0` → ~3.7 h
(screen-bound); `q=0.1` → ~1.5 days (still screen-bound, 10× worse); high-density `lambda_cls=8`
with `q=0.002` → ~2.1 h but now **eval-bound** (adding scan GPUs wouldn't help). **Each ~+1 to
`lambda_cls` multiplies screen time by `e ≈ 2.7`; each 10× drop in `q` multiplies total by 10** — so
a truncation-heavy conversion that raises `lambda_cls` *or* opens an independent `pha` mode is far
more expensive than its score delta suggests. Prefer exact/value-exact levers that keep both `d` and
`q` at the frontier's values.

### Refinement: conditional funnel, count model, and calibration

Three corrections that make the estimate honest. Intuition first, then the recipe.

**1. The channels are rare-event COUNTS — model as Poisson/Negative-Binomial, never Gaussian.**
`cls/pha/anc` are non-negative integer counts of failing shots (a few out of 9024). At the typical
small means (μ≈2–6) a Gaussian is the wrong shape (symmetric, continuous, puts mass on negative
counts) and mis-estimates `P(count=0)` — the one quantity that matters. Use:
- **Poisson** (dispersion `σ²/μ ≈ 1`): `P(channel=0) = e^(−μ)`.
- **Negative Binomial** (`σ²/μ > ~1.2`, the usual case — GCD-clean nonces are a heterogeneous,
  screened subpopulation → overdispersed): `P(0) = (1+μ/r)^(−r)`, `r = μ²/(σ²−μ)`. NB captures your
  intuition that *both* a small mean **and** a fat variance make a zero more likely; it degrades to
  Poisson as `σ²→μ`. Run a dispersion/χ² check to pick; until you have ~50–100 candidates, the
  variance is unreliable — fall back to Poisson on the mean.

**2. Use the CONDITIONAL FUNNEL, not the independent product `∏ P(channel=0)`.** `cls` and `pha` are
positively correlated (one dropped truncation bit breaks the result *and* leaves phase garbage), so
multiplying marginal zero-rates overestimates `E[N]`. Chain the conditionals instead — each measured
*inside* the previous-clean subset, which captures the correlation by construction:
```
island_rate = d · P(c=0) · P(p=0 | c=0) · P(a=0 | c=0,p=0)
```
Measure `P(p=0|c=0)` **directly** as the fraction of c-clean candidates that are also p-clean (more
robust than modeling the `pha` distribution); only model it as `e^(−mean_p over c-clean)` when it's
too rare to observe directly. (`a` is usually deterministic-0 → `P(a=0|…)≈1`.) Equivalent and
correlation-free if you can dump failing-shot indices: fit one NB to the **union** bad-shot count
(#shots failing *any* channel) → `q = P(union=0)`.

**3. Estimate every rate from the MEAN, not the zero-fraction.** Don't estimate a `~1e-6` probability
by counting rare zeros. Get `d` from the **all-nonce** GCD-hard count: `d = e^(−λ_GCD)`,
`λ_GCD = mean GCD-hard shots over all scanned nonces` (millions of samples → tight). pha/anc never
exist for GCD-dirty nonces, so those rates come only from the c-clean candidate panel — but still via
their means, not by waiting for a zero.

**4. CALIBRATE — don't over-derive (the load-bearing caveat).** No closed form is reliable to better
than ~an order of magnitude: shot-level correlations break the independence every formula assumes.
Treat the closed form as a **relative ranker + ETA prior**, and wrap it with an empirically-learned
correction:
```
E[N] ≈ k · (1 / island_rate),   k = running median(actual_N / predicted_N) over landed hunts
```
Log `(predicted, actual)` for every island you land and update `k` continuously (observed spread
~0.3×–73× across configs). The formula tells you *which route is more huntable* and a first ETA; `k`
is what makes the absolute number trustworthy. Also report p50/p90/p99 (the wait is exponential).

**Final recipe (end to end):**
```
d           = e^(−λ_GCD)                 λ_GCD from all-nonce GCD-hard mean
P(c=0)      = e^(−mean_c)   [NB if overdispersed]    mean_c = residual cls on c-clean candidates
P(p=0|c=0)  = measured fraction of c-clean candidates that are p-clean (else e^(−mean_p))
P(a=0|…)    ≈ 1
island_rate = d · P(c=0) · P(p=0|c=0) · P(a=0|…)
E[N]        = k · 1/island_rate ;  report p50/p90/p99 ;  update k from each landed hunt
```

## Remote Validation Hygiene

Prefer remote parallel validation for large batches because local CPU validation is slow.
**Start distributed validation as early as the first GCD-clean candidates appear — don't wait for
a large backlog — and validate FULL only (no fast-reject): the near-miss `cls / pha / anc`
distribution and the per-channel-zero check (loop step 5.2) both need exact counts, which the
fast path's early-out cannot give.**

### Distributed own-host validation

For high-density hunts, scanning and validation should be distributed together. The default
ownership rule is:

```text
Each GPU machine validates the GCD-clean candidates found by its own scanner logs.
```

Do not centralize all candidates onto one validator except as a temporary recovery step. Central
sharding creates avoidable delay, duplicate work, stale backlogs, and unclear ownership. The
machine that produces a local `CLEAN nonce=...` prefilter line should immediately feed that nonce
to a local full-validator loop on the same host.

Before launching distributed validation for a route, pin and record these artifacts:

- circuit source commit and local diff summary
- exact circuit CFG / env
- GPU state file path and sha256
- GPU toolkit branch and commit
- remote validator source archive sha256, if source is copied to remotes
- `build_circuit` and `eval_circuit` hashes per remote toolchain
- accepted local/remote anchor nonce triples

Use a consistent remote layout on every host, parameterized by the route name:

```text
/root/.ecdsafail_island_<route>/logs/*.log      scan logs
/root/<route>_remote_validate.sh                full validator wrapper
/root/<route>_validate_own_loop.sh              per-host validation loop
/root/<route>_own_validation/candidates.txt     sorted unique GCD-clean nonces from scanner logs
/root/<route>_own_validation/pending.txt        unvalidated backlog after done/log skip-list filtering
/root/<route>_own_validation/results.log        own-host full-validation output
/root/<route>_own_validation/errors.log         retryable build/eval failures, not verdicts
/root/<route>_own_validation/done.txt           validated nonce skip-list
/root/<route>_own_validation/batch_<ts>.txt      nonce batch currently being validated
/root/<route>_own_validation/shared_ops/ops.bin  optional read-only host-level ops cache
/root/<route>_own_validation/loop.out           loop diagnostics
```

Older shard logs may be retained for audit, but new validation should flow through the own-host
loop unless recovering from a broken node.

#### Remote result ledger and local mirror

Every remote validator must write durable results on the remote machine first. Do not rely on
terminal scrollback, stdout from an SSH session, or local-only validation output as the record of
truth. Each full-validation worker should append one parseable verdict line per successfully
evaluated nonce to:

```text
/root/<route>_own_validation/results.log
```

`results.log` is a verdict ledger, not a diagnostics stream. It should contain only completed
`dirty` / `CLEAN` full-validation verdicts, and every row must start with an ISO-8601 timestamp
for the verdict completion time:

```text
ts=2026-06-21T18:13:58+00:00 dirty nonce=<n> shots=<shots> cls=<c> pha=<p> anc=<a> tof=<avgT> qubits=<q>
ts=2026-06-21T18:14:02+00:00 CLEAN nonce=<n> shots=<shots> cls=0 pha=0 anc=0 tof=<avgT> qubits=<q>
```

If old untimestamped rows are imported, preserve them in a raw backup and write a migration note in
`loop.out` or `sync.log`; do not silently mix ambiguous rows into the live ledger. Route retryable
operational failures to:

```text
/root/<route>_own_validation/errors.log
```

Append the timestamped verdict line before adding that nonce to `done.txt`. If validation returns `ERROR`,
append the error to `errors.log`, leave the nonce out of `done.txt`, and rerun it later. When
multiple validator workers are active, use an append-safe pattern such as `flock`, or set toolkit
ledger variables:

```bash
VALIDATE_RESULTS_LOG=/root/<route>_own_validation/results.log
VALIDATE_ERRORS_LOG=/root/<route>_own_validation/errors.log
VALIDATE_LOCK_FILE=/root/<route>_own_validation/validate.lock
```

Avoid any loop that marks a nonce done before its result line is durably written. If an old or
interrupted loop pollutes `results.log` with `ERROR` rows, take the same lock, move those rows to
`errors.log`, rebuild local mirrors, and treat the affected nonces as retryable.

Keep the live remote `results.log` append-only after validation starts. Do not periodically rewrite
or atomically replace it with `mv results.tmp results.log`; plain `tail -f results.log` follows the
old inode and appears stuck after a replacement. If deduping or parsing is needed, write derived
files such as `combined.tsv`; if a live mirror must survive file replacement, use `tail -F`, but the
remote ledger itself should be safe for ordinary `tail -f`.

Every heartbeat should mirror remote result ledgers into a local audit directory, preserving both
raw per-host logs and a combined parsed view. Use a predictable local layout such as:

```text
outputs/<route>_validation_results/raw/<host>.results.log
outputs/<route>_validation_results/raw/<host>.errors.log
outputs/<route>_validation_results/raw/<host>.candidates.txt
outputs/<route>_validation_results/combined.tsv
outputs/<route>_validation_results/near_misses.tsv
outputs/<route>_validation_results/clean_hits.tsv
outputs/<route>_validation_results/sync.log
```

The raw per-host files should be exact mirrors of remote `results.log` files. The combined TSV
should add at least `host`, `ts`, `nonce`, `verdict`, `cls`, `pha`, `anc`, `tof`, and `qubits`, then
deduplicate by nonce so the user can inspect one local file without SSHing into every node. Keep
`clean_hits.tsv` and `near_misses.tsv` regenerated from `combined.tsv`; do not hand-maintain them.
Mirror `errors.log` and `candidates.txt` separately for retry and density audits, but do not parse
error rows into `combined.tsv`.

For periodic mirroring, prefer idempotent pulls that overwrite each host mirror atomically, then
rebuild combined files locally:

```bash
ssh <host> "cat /root/<route>_own_validation/results.log" > raw/<host>.results.log.tmp
mv raw/<host>.results.log.tmp raw/<host>.results.log
# then parse all raw/*.results.log into combined.tsv, near_misses.tsv, and clean_hits.tsv
```

If live streaming is useful, run a `tail -F` stream per host into host-specific raw files, but still
rebuild `combined.tsv` by parsing and deduplicating the raw logs. Streaming is an accelerator, not a
replacement for the remote ledger. Heartbeats must say whether remote verdicts are being streamed or
periodically mirrored, and must print the remote workdir, `candidates.txt`, `results.log`, and local
mirror directory so the user does not have to ask where the data lives.

#### Skip-list discipline

Before starting or restarting distributed validation:

1. Collect all previously validated nonces from every remote validator log.
2. Merge them into one sorted unique global skip-list.
3. Copy that list to every host.
4. Seed each host's `<route>_own_validation/done.txt` from the global list.

Every validation loop should also re-scan prior local validator logs and merge their nonce IDs into
`done.txt`. This protects against restarts, old shard logs, and partially completed batches.

Avoid `comm` for filtering unless both inputs are guaranteed to use the same lexical sort. Prefer a
hash-set filter. Use `FILENAME == ARGV[1]`, not `NR == FNR`, so an empty `done.txt` does not make
the candidate file look like the first input:

```bash
awk 'FILENAME == ARGV[1] { done[$1]=1; next } !($1 in done)' done.txt all_candidates.txt
```

Before launching a large validation batch, sanity-check that no batch nonce is already in
`done.txt` and that the batch has no duplicates:

```bash
awk 'NR==FNR { d[$1]=1; next } ($1 in d) { c++ } END { print c+0 }' done.txt batch.txt
sort -n batch.txt | uniq -d | wc -l
```

Both numbers should be `0`.

#### Per-host validation loop

For routes that validate many candidates on one host, build the circuit body **once per host**.
The nonce tail is an identity tail: `DIALOG_TAIL_NONCE=0` and `DIALOG_TAIL_NONCE=<n>` have the
same simulated op stream; the candidate nonce only changes the Fiat-Shamir hash. Therefore:

1. Build one shared validation directory such as `/root/<route>_own_validation/shared_ops`.
2. Run `build_circuit` there once with the active CFG and `DIALOG_TAIL_NONCE=0`.
3. Mark `shared_ops/ops.bin` read-only.
4. Launch many parallel `eval_circuit` processes from that same directory with
   `EVAL_TAIL_NONCE=<nonce>` and the requested `EVAL_FAST_REJECT` setting.

Do **not** run one `VALIDATE_REUSE_OPS=1 ./island.sh validate ...` process per worker for large
remote batches. That still builds one temp `ops.bin` per process, wasting disk and capping
parallelism. `VALIDATE_REUSE_OPS=1` is fine for small local batches or one serial validator
process; distributed/high-parallel validation should share one read-only `ops.bin` per host.

The loop should:

1. Read only that host's local scanner logs.
2. Extract GCD-clean candidate nonces from `CLEAN nonce=<n>` into sorted unique
   `candidates.txt`.
3. Remove nonces already present in `done.txt` or previous validation logs, and write the current
   not-yet-validated list to `pending.txt`.
4. Validate the remaining nonces in parallel with the host-level shared `ops.bin` cache when the
   evaluator supports `EVAL_TAIL_NONCE`; otherwise fall back to per-batch rebuilds.
5. Append timestamped parseable `dirty` / `CLEAN` verdict output to `results.log` without replacing
   the file inode; route `ERROR` output to `errors.log`.
6. Add only successfully validated `dirty` / `CLEAN` nonce IDs to `done.txt`; keep `ERROR`
   nonces retryable.
7. Repeat.

Parallelism is part of the correctness of the operational procedure: a GPU host that scans
quickly but validates candidates with one serial process will build a stale backlog and hide clean
hits. Run a **multi-process validator pool on every scanning host**, sized to that host's CPU/GPU
capacity, and keep increasing it until validation throughput stops improving or the machine becomes
unstable.

Starting parallelism:

```text
with per-process ops builds:
  single RTX5090 host: Q_VALIDATE_PAR=4,  Q_VALIDATE_BATCH=512
  4x L40S host:       Q_VALIDATE_PAR=8,  Q_VALIDATE_BATCH=1024
  4x RTX5090 host:    Q_VALIDATE_PAR=12, Q_VALIDATE_BATCH=1536

with one shared read-only ops.bin per host:
  single RTX5090 host: Q_VALIDATE_PAR=8..16
  4x L40S host:       Q_VALIDATE_PAR=32..64 first, then 96+ if CPU/disk stay stable
  4x RTX5090 host:    Q_VALIDATE_PAR=48..96 depending on CPU cores
```

These are conservative starting points, not ceilings. On a large remote node, inspect `nproc`,
current load, memory pressure, and scanner contention, then ramp upward in steps:

```text
per-process ops builds:
  single-GPU host: try 4 -> 6 -> 8 workers
  4-GPU host:      try 8 -> 12 -> 16 -> 24+ workers

shared ops.bin:
  single-GPU host: try 8 -> 16 -> 24 workers
  4-GPU host:      try 32 -> 64 -> 96 -> 120 workers
```

If the validator is CPU-only, the worker cap is usually host CPU cores minus a small reserve for
scanner/logging processes. If a future validator uses GPU kernels, shard workers so every GPU has
active validation work and avoid putting all validation on GPU0. In either case, the heartbeat
should show **both** active scanner processes and multiple active validation children per host.

Tune only after checking that the machine remains responsive and validation latency is acceptable.
If validation results are not keeping up with GCD-clean candidate production, increase
`Q_VALIDATE_PAR`, increase batch size, or add more validator hosts before assigning more scan range.

The remote validator must use full validation:

```bash
EVAL_FAST_REJECT=0
```

Each successfully evaluated nonce must produce exactly one parseable verdict line in
`results.log`:

```text
ts=<iso8601> dirty nonce=<n> shots=<shots> cls=<c> pha=<p> anc=<a> tof=<avgT> qubits=<q>
ts=<iso8601> CLEAN nonce=<n> shots=<shots> cls=0 pha=0 anc=0 tof=<avgT> qubits=<q>
```

Build/eval failures must go to `errors.log`:

```text
ERROR nonce=<n> stage=<build|eval> rc=<code> ...
```

Treat `ERROR` as unvalidated. Do not add it to final clean/dirty statistics until it is rerun
successfully.

Monitor both scanner and validator activity per host:

```bash
printf 'remote workdir: %s\n' /root/<route>_own_validation
ps -eo pid,etime,cmd | grep -E '<route>_validate_own_loop|<route>_remote_validate|search_driver|gpu_island' | grep -v grep
pgrep -fc '<route>_remote_validate'
wc -l /root/<route>_own_validation/candidates.txt
wc -l /root/<route>_own_validation/pending.txt
wc -l /root/<route>_own_validation/done.txt
wc -l /root/<route>_own_validation/results.log
wc -l /root/<route>_own_validation/errors.log
tail -10 /root/<route>_own_validation/results.log
```

Useful heartbeat fields include remote workdir and file paths, active scanner ranges, validator
loop PID, active full-validator children, configured `Q_VALIDATE_PAR`, observed validator
throughput, `candidates.txt` count, `pending.txt` count, `done.txt` count, `results.log` count,
`errors.log` count, remote-to-local mirror status, local mirror directory, local `combined.tsv` row
count, local `clean_hits.tsv` row count, duplicate sanity status for the latest batch, and best near
misses from newly validated results.

#### Local cross-checks are trust checks only

Local validation is for remote-validator trust, not throughput.

Use this policy:

- After a new validator build, new GPU host, changed source, changed CFG, or changed state:
  cross-check several anchors locally and remotely.
- During steady-state hunting after anchors agree: cross-check the active hunt's requested sample
  size, often one recent candidate per heartbeat for high-density hunts. If no sample size is
  specified, use five.
- If any remote/local mismatch appears: quarantine that host, stop trusting its validator output,
  rebuild or redeploy, then re-anchor.

The cross-check must compare exact `nonce`, verdict, `cls`, `pha`, and `anc`. Do not accept
approximate agreement. Do not report anchor nonce results as new hunt results.

#### Clean hit handling

If any remote log contains:

```text
CLEAN nonce=<n> cls=0 pha=0 anc=0
```

immediately:

1. Follow the current user policy for the hunt. Default policy is local full-validation first; if
   the user explicitly requested submit-first during a race, submit immediately on the remote full
   validator hit and run local verification afterward.
2. Bake the CFG and nonce into the challenge worktree.
3. Run `ecdsafail run` when policy requires local confirmation or after submit-first completion.
4. Preserve the solution on a branch with a detailed commit message.

Do not wait for the rest of the backlog to drain once a clean hit has satisfied the active
submission policy.

Anti-patterns:

- Validating all hosts' candidates on only one machine.
- Letting 5090s scan while only L40S hosts validate, or vice versa.
- Running only one validation process on a multi-core or multi-GPU host.
- Assigning more scan ranges while validation backlog is growing.
- Revalidating old nonces because each host has only a local skip-list.
- Reporting anchor nonce results as if they were new hunt results.
- Trusting a remote validator before anchor agreement.
- Using fast validation for final clean/dirty accounting.
- Losing the exact CFG/state/toolkit hashes that produced a candidate.
- Killing scanner processes while trying to restart validator loops.

During an active island hunt, **candidate validation is part of every heartbeat**, and it has
**TWO distinct jobs that must not be conflated**:

1. **Remote-validate EVERY newly-discovered GCD-clean candidate** on the GPU boxes (distributed,
   FULL mode). This is the heartbeat's *main* validation work — **drain the whole new-candidate
   backlog every beat.** Do not let the GPU scan frontier advance while GCD-clean candidates pile
   up unvalidated. The remote validators exist precisely so you can validate *all* of them in
   parallel, not a handful.
2. **Cross-check a small requested sample against local validation** — this is a **trust gate on
   the remote validator, NOT the validation itself.** If the hunt instructions specify a sample
   size, use that exact size; otherwise use 5. Re-run those just-validated candidates on the local
   CPU and require exact `cls / pha / anc` agreement before trusting the node's verdicts for the
   rest.

> **The single most common failure here:** treating the local cross-check sample *as* the validation
> and only validating that small sample per heartbeat. That is WRONG. Validate **all** newly-discovered
> GCD-clean candidates remotely; the local re-runs are *only* to confirm the remote validator
> agrees with local. If you ever find yourself validating just the cross-check sample and leaving the rest of the new
> candidates unchecked, stop — you are doing it wrong.

Each heartbeat, report: how many new candidates were remote-validated (backlog drained to zero or
the remaining count), which shards/nodes did the validating, the local cross-check result, and
any clean `0/0/0`. If remote validation is blocked, stale, or not yet trusted, say so explicitly
and keep a local validation sample moving so the route's `cls / pha / anc` distribution stays
current — but the goal is still to validate *every* new candidate, just locally until the remote
node is trusted again.

For large candidate batches, use **distributed validation** across the available Linux GPU-node host
CPUs whenever possible. Shard the candidate list across prepared nodes, write per-node logs, and
merge results into the heartbeat's near-miss table. Distributed validation must use the exact active
CFG/source/binaries for the circuit being hunted; a validator from a neighboring route or older
SOTA base is stale even if it appears to run successfully.

Before trusting remote validation in a heartbeat or batch:

1. Sample at least two recent GCD-clean candidates, preferably including the current best near miss
   and one ordinary dirty candidate.
2. Validate them locally with the exact active CFG in every available mode (fast and full when both
   exist; full only if the prototype has no fast path).
3. Validate the same candidates remotely with the exact same CFG and binaries.
4. Require exact local/remote agreement on nonce, verdict, and `cls / pha / anc` before using
   remote shard results.

After rebuilding or refreshing remote validators, require a fixed acceptance set to match local
exactly before trusting the node. Keep remote validator binaries aligned with the active CFG. A
stale validator can silently invalidate the experiment. If any node disagrees with local validation,
quarantine that node's validator output, do not merge its shard, and report the mismatch with the
offending nonce and both triples.

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

## Heartbeat Automation

When a new island hunt begins, automatically create or update a thread heartbeat instead of relying on memory. Use a **15-minute heartbeat for active distributed hunts** (the preferred cadence; 25 min is acceptable only for a slow background scan) unless the user asks for a different interval. Do this even if the user did not explicitly ask for recurring progress reports; long-running nonce scans should always have a live progress monitor.

The heartbeat prompt should be self-contained. Include:

- active route name, source/worktree, CFG, measured qubits, Toffoli/CCX, and score context
- state file path and trusted validator/build paths
- GPU node inventory and SSH commands
- current assigned ranges, highest frontier, and already completed windows
- remote working directory, scanner log path, candidate file path, result ledger path, error log
  path, and local mirror directory for every active host
- known candidate totals, density, and best validated `cls / pha / anc` near misses
- per-host validator loop status, active validator child count, configured parallelism, and whether
  validation throughput is keeping up with scan throughput
- a validation mandate: every heartbeat must **remote-validate ALL newly-discovered GCD-clean
  candidates** (distributed, full mode — drain the backlog, not just a sample), and **separately
  cross-check the requested local sample size** as the remote-validator trust gate (default 5 when
  unspecified; exact `cls / pha / anc` agreement). The local sample is the trust check, NOT the
  validation — validate them all.
- submission policy: submit to ecdsafail only if measured score beats SOTA, unless the user explicitly says otherwise
- branch policy for clean-but-worse low-qubit results, if requested
- a reminder not to commit temp configs, scan logs, helper binaries, `ops.bin`, GPU states, or generated artifacts

Before creating a duplicate heartbeat, inspect existing automations if the environment exposes an automation tool or local automation records. Prefer updating the current route's heartbeat when one exists. If the route changes, update the heartbeat promptly so it does not keep reporting stale ranges or an old CFG.

Heartbeat work order:

1. Poll scans, parse completed ranges, and extend idle trusted GPUs if policy allows.
2. Extract newly flushed GCD-clean candidates and update the backlog.
3. **Remote-validate every newly-discovered GCD-clean candidate** this beat — distributed across the
   GPU boxes, full mode. The aim is to drain the *entire* new-candidate backlog, not to spot-check.
4. **Additionally** cross-check the requested sample size of those candidates with a local re-run
   (default 5 when unspecified); require exact `cls / pha / anc` agreement before trusting the
   remote node's verdicts for the rest. This is a trust gate *on top of* step 3 — it does not
   replace remote-validating all the others.
5. Report validation progress, backlog remaining, validator trust status, best near misses, and any
   clean `0 / 0 / 0` immediately. Always include where the remote workdir is, where GCD-clean
   candidates are stored, whether `results.log` is being streamed or mirrored, and the local mirror
   path.

Do not treat GPU utilization as the whole heartbeat. A healthy hunt has both scanners and validators
moving.

## Reporting Format

Use this compact shape for heartbeat-style progress reports. Prefer exact measured values; if a value is estimated, mark it with `~`. If no scans are active, say so plainly instead of inventing an active window.

```text
# Overall Stats
active trusted GPUs: <active>/<trusted reachable>
unreachable: <node list or none>
quarantined: <node list and reason, or none>
aggregate observed rate: ~<nonce/s> nonce/s
highest assigned frontier: <nonce>
visible active-window progress: ~<scanned> scanned, ~<remaining> remaining
current active-window candidates: <count>
current-window density: ~<candidates/Mnonce> candidates/Mnonce
expected next candidate: ~<time> at current density/rate
latest promoted SOTA: <submission id>, q=<q>, Toffoli=<t>, score=<score>
active route: q=<q>, Toffoli/CCX=<t>, score=<score>, triage=<GREEN/YELLOW/RED>

# Per GPU stats
<node> (<GPU model>) <range> <scanned>/<assigned> <candidates> candidates <rate>/s ETA <eta>
...

# Best near misses (nonce cls/pha/anc)
<nonce>   <cls> / <pha> / <anc>
...
```

Reporting rules:

- Keep reports concise; surface best near misses, anomalies, and route decisions instead of dumping every dirty candidate.
- Report active/idle GPU count, unreachable nodes, quarantined nodes, and any stale-state suspicion.
- Report aggregate and per-GPU rates when estimable. If a direct GPU command flushes output only at the end, use the last completed range's observed rate.
- Include completed/scanned nonces, estimated in-flight nonces, remaining assigned window, highest assigned frontier, total GCD-clean candidates, density, ETA, and expected time to next candidate.
- Include validator cross-check status when remote validation is used.
- Include the remote scan/validation workdir, `candidates.txt`, `results.log`, `errors.log`, and
  local mirror path for every active remote hunt. Report how many GCD-clean candidates were found,
  how many are pending, how many are done, and whether verdict rows are streamed in real time.
- Include a compact near-miss table sorted by usefulness: clean `pha=0, anc=0` first, then low severity, then lower phase/anc.
- If a GPU is idle and policy allows extension, report the new range/session. If policy says not to extend, report that decision.
- If no scans are currently active, set active GPUs to `0/N`, mark ranges as completed, and use historical/completed-window density and rate for the expected-next-candidate estimate.

## Clean Solution Handling

If any full validation returns `0 / 0 / 0`:

1. Open the scan manifest and identify the exact source tweaks, CFG/env knobs, toolkit branch, and
   nonce that produced the hit.
2. Bake the CFG and nonce into the challenge repo. Do not submit a solution that only works because
   the current shell exports the scan env vars.
3. Run the no-env submission rehearsal by unsetting every correctness-affecting scan env var and
   running `ecdsafail run`. The result must match the remote clean hit and expected `q`/avgT.
4. Pull latest SOTA again.
5. Compute measured score from benchmark output.
6. Submit to the ecdsafail site only if measured score beats current promoted SOTA, unless the user explicitly instructs otherwise.
7. If the user wants clean-but-worse low-qubit results preserved, create a new branch in the requested challenge repo and push the validated circuit even when the score is higher than SOTA.

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
- each of `cls`, `pha`, `anc` reaching 0 in at least one candidate over a sufficient sample (the
  per-channel-zero rule — necessary for a reachable `0/0/0`)
- low single-digit near misses, ideally clustered close to `0/0/0`
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
- a channel (`cls`, `pha`, or `anc`) that **never reaches 0** over a sufficient sample — a
  per-channel floor makes `0/0/0` unreachable no matter the nonce, so the route is dead
- repeated high dirty triples
- no severity `<= 10` after dozens of candidates
- stale validator or CFG uncertainty
- suspicious per-node behavior that cannot be explained
- persistent `pha`/`anc` residuals across otherwise promising candidates
- uniform failure localization in an early GCD/apply, carry-cleanup, or phase-discharge section
- qubit savings in a non-peak phase only
