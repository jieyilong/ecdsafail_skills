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

## Remote Validation Hygiene

Prefer remote parallel validation for large batches because local CPU validation is slow.
**Start distributed validation as early as the first GCD-clean candidates appear — don't wait for
a large backlog — and validate FULL only (no fast-reject): the near-miss `cls / pha / anc`
distribution and the per-channel-zero check (loop step 5.2) both need exact counts, which the
fast path's early-out cannot give.**

During an active island hunt, **candidate validation is part of every heartbeat**. Do not let the
GPU scan frontier advance while the GCD-clean candidate backlog grows unchecked. Each heartbeat
should do real validation work: validate newly flushed candidates, report the validation backlog,
and say which candidates or shards were validated. If remote validation is blocked, stale, or not
yet trusted, say so explicitly and keep a small local validation sample moving so the route's
`cls / pha / anc` distribution stays current.

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
- known candidate totals, density, and best validated `cls / pha / anc` near misses
- a validation mandate: every heartbeat must drain candidate backlog using distributed validation
  when possible, and must **cross-check 5 sampled GCD-clean candidates** against local validation
  before trusting remote validator output (exact `cls / pha / anc` agreement is the trust gate)
- submission policy: submit to ecdsafail only if measured score beats SOTA, unless the user explicitly says otherwise
- branch policy for clean-but-worse low-qubit results, if requested
- a reminder not to commit temp configs, scan logs, helper binaries, `ops.bin`, GPU states, or generated artifacts

Before creating a duplicate heartbeat, inspect existing automations if the environment exposes an automation tool or local automation records. Prefer updating the current route's heartbeat when one exists. If the route changes, update the heartbeat promptly so it does not keep reporting stale ranges or an old CFG.

Heartbeat work order:

1. Poll scans, parse completed ranges, and extend idle trusted GPUs if policy allows.
2. Extract newly flushed GCD-clean candidates and update the backlog.
3. Validate candidates during the heartbeat. Prefer remote distributed validation for nontrivial
   batches.
4. Before accepting remote results, cross-check **5 sampled GCD-clean candidates** locally against
   the remote validator output. Use exact `cls / pha / anc` agreement as the trust gate.
5. Report validation progress, backlog remaining, validator trust status, best near misses, and any
   clean `0 / 0 / 0` immediately.

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
- Include a compact near-miss table sorted by usefulness: clean `pha=0, anc=0` first, then low severity, then lower phase/anc.
- If a GPU is idle and policy allows extension, report the new range/session. If policy says not to extend, report that decision.
- If no scans are currently active, set active GPUs to `0/N`, mark ranges as completed, and use historical/completed-window density and rate for the expected-next-candidate estimate.

## Clean Solution Handling

If any full validation returns `0 / 0 / 0`:

1. Bake the CFG and nonce into the challenge repo.
2. Run the normal benchmark/check.
3. Pull latest SOTA again.
4. Compute measured score from benchmark output.
5. Submit to the ecdsafail site only if measured score beats current promoted SOTA, unless the user explicitly instructs otherwise.
6. If the user wants clean-but-worse low-qubit results preserved, create a new branch in the requested challenge repo and push the validated circuit even when the score is higher than SOTA.

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
