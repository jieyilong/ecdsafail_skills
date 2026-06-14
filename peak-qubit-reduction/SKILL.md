---
name: peak-qubit-reduction
description: >-
  Reduce the peak (maximum simultaneous) qubit count — the "width" — of a reversible or
  quantum circuit. Use this whenever a circuit uses too many qubits/ancilla/scratch, when
  optimizing circuit width or the qubits-times-gates score, when an arithmetic or Shor-style
  circuit needs to fit a smaller machine, or when someone asks how to "shave qubits", "lower
  the qubit count", "reduce ancilla", "free scratch earlier", or "trade gates for qubits".
  Trigger even if the user describes the goal informally (e.g. "this adder needs way fewer
  wires", "where's all my space going", "can I reuse that register") without naming peak
  width. Provides a left-to-right timeline analysis: find the tallest moment, inventory the
  qubits alive there, and brainstorm uncompute-early/recompute-later holes, live-range
  shortening, truncation, and transcript compression to cut them.
---

# Peak Qubit Reduction

A circuit's qubit cost is not how many qubits it *names* — it is the **most qubits alive at
any single instant**. Lay the computation out left-to-right in time and plot how many qubits
are live at each moment; you get a mountain range, and the **single tallest peak** is what you
pay. This skill is the playbook for finding that peak and shaving it down.

The whole discipline follows from two facts of reversible/quantum computing:

- **You cannot delete information.** A qubit holding a value can't just be discarded; the only
  way to free it is to **uncompute** — run gates backward until it returns to a known |0⟩.
- **Width is a MAX over time, not a sum.** Lowering qubit usage somewhere that *isn't* the peak
  does nothing for the width score. Only the tallest moment counts.

Together these mean: the qubit prize comes from shrinking whatever is alive at *one specific
instant*, and every byte of "freeing" you do costs gates to uncompute and recompute. That
trade is the heart of everything below.

## The core loop

Work this loop; each pass lowers the peak by one increment and usually moves it somewhere new.

1. **Measure** — get the live-qubits-vs-time profile; find the peak height and the operation/phase that owns it (the *binder*).
2. **Inventory** — list the qubits alive at the binder instant.
3. **Classify** — label each one (essential data / scratch / transcript-log / passenger / alias-candidate / truncatable).
4. **Brainstorm** — for each non-essential qubit at the peak, propose a shave (the moves below).
5. **Cost** — price the shave in gates, depth, and correctness risk via the qubit↔gate exchange rate.
6. **Re-measure** — apply the cheapest safe shave; the peak moves to a new owner; repeat until you hit a structural floor.

The mistake to avoid at every step: **optimizing a qubit that isn't actually at the peak.** It
feels productive and changes nothing. Before proposing any shave, confirm the qubit you're
targeting is live at the binder instant.

## Match the method to the lever's failure mode

Before reaching for a lever, know *how it can fail* — because that decides whether you "tweak
and iterate" or "prove correct, then commit." There are two fundamentally different kinds:

- **Graded-failure levers** (truncate a carry/compare width, drop a loop iteration, approximate
  a reduction). Correctness degrades *continuously*: a small, characterizable fraction of inputs
  go wrong, by a little. These usually reduce *gate* cost, and you can **iterate on the
  dirtiness** — measure the per-input error, restore one bit, re-measure — and, when the input
  set is fixed, **search for an input subset / seed that dodges the failures**. This is the
  domain of triage / search loops: low near-misses are progress.

- **Binary-failure levers** (free, overlap, stream, or hole a register to cut *peak width*).
  Correctness is **all-or-nothing**: the edit is value-exact (right on every input) or it
  corrupts phase/ancilla on essentially *every* input. There is **no graded near-miss ladder to
  climb.** So you cannot tweak-and-triage a width cut — you must get it value-exact, **validate
  clean (e.g. classical/phase/ancilla all zero on random inputs) BEFORE any downstream search**,
  and only then proceed.

**The trap:** applying the graded-failure playbook to a binary-failure lever. A structural width
cut that isn't value-exact yields all-dirty garbage, not near-misses — there is nothing to
iterate *toward*. Cutting peak width is therefore "write a correct value-exact edit, validate it
clean, then search," not "turn a knob and triage."

**Corollary — when no parameter moves the target, the cost is allocation-bound.** If *every*
available knob leaves the peak unchanged, the registers are declared full-width and the only
remaining lever is a **structural code change** — which is the binary kind. Escalate to it
deliberately: inventory the binder's live set (next step), make the *smallest* value-exact edit,
validate, and only then re-measure/search. Don't keep turning knobs once they've gone flat.

**A peak can be several independent binders, not one shared floor.** The inventory (Step 2) may
show that two *unrelated* phases each independently reach the peak (e.g. an arithmetic core and a
separate squaring), co-equal but sharing no register. Then one edit that relieves one of them
leaves the other still at the peak — lowering the number requires **coordinated edits to every
co-equal binder**, and you re-trace after each to see which walls remain. Budget for "more than
one edit" before assuming a single hole drops the count.

**The deepest cuts usually end on a co-binder plateau.** Once the obvious tallest owner is shaved,
expect several phases to tie at the same peak. A real next-qubit win then needs a package of small
edits whose effects land together: one codec or live-range hole for the persistent floor, one
streaming/recompute trick for the transient apply path, one segment/notch change for a separate
arithmetic phase, and selective repairs for the iterations made fragile by the cut. Treat a
"1170 everywhere" style trace as intentional: if apply ripple, special folds, compressed apply,
and square all hit the same height, the next reduction must move *all* of them or the peak number
will not budge.

## Step 1 — Measure: find the binder

You need a **live-qubit-vs-time trace**, not just a total count. Two ways to get one:

- If the framework tracks allocation/free events, instrument them: increment a counter on
  alloc, decrement on free, and record the max along with the *name of the phase* that was
  executing when the max was hit. The phase name is the single most useful output — it tells
  you what to attack.
- If not, walk the time-ordered op list and maintain a live-set; the peak is `max |live-set|`.

The deliverable is one line: **`peak = N at phase = <owner>`**. That owner is your target.
Everything else in the circuit is taller-than-nothing but irrelevant until the owner shrinks.

> Re-run this after *every* change. The peak is a whack-a-mole: shave the current owner and a
> different phase becomes the new tallest one. You are never "done with phase X" in the
> abstract — only "X is no longer the binder."

## Step 2 — Inventory the peak's live set

Freeze the circuit at the binder instant and list every qubit alive. For each, note: what
value it holds, where it was allocated (how far back), and where it is next *used* (how far
forward). The gap between "allocated" and "next used" is the qubit's **live range**, and live
ranges that merely *pass through* the peak without being touched there are your best targets.

## Step 3 — Classify each live qubit

| Class | What it is | Shrinkable? |
|---|---|---|
| **Essential data** | the actual inputs/outputs the peak operation reads or writes | rarely — this is the real work |
| **Scratch** | temporary results (carries, partial products, comparison bits) | often — uncompute/recompute, truncate |
| **Transcript / log** | decisions recorded only to stay reversible (see below) | often — compress the log |
| **Passenger** | allocated before the peak, consumed after, *idle during* it | yes — move its live range out of the peak window |
| **Alias-candidate** | a copy/restorable duplicate of a value already live | yes — borrow the original as dirty scratch |
| **Truncatable** | holds bits that are provably zero or don't affect the result | yes — just don't keep those bits |

Most real wins come from the bottom four rows. Walk them in order; the moves below map to them.

## Step 4 — Shaving moves

### Live-range hole: uncompute early, recompute later (the headline move)

If a qubit holds a value that the **peak instant does not need**, free it *before* the peak and
rebuild it *after*. You punch a hole in its live range exactly across the peak window, so it is
no longer counted at the binder.

```
before:  ...====[VALUE held live across the peak]====...   <- counted at peak
after:   ...===]   (uncomputed)   [recompute]===...        <- absent at peak
                  ^^^^^^^^^^^^^^^^^
                  the peak instant falls in here
```

Mechanically: emit the reverse of the gates that built the value (returning its qubits to |0⟩
and freeing them), run the peak-owning phase with that headroom, then re-emit the forward gates
to restore the value for its later consumer. This is the single most reliable width reducer.

**Why it works and when it doesn't:** it converts qubits into gates. The recompute is pure
overhead — extra Toff/CNOT and, importantly, extra *depth*. It only wins if (a) the freed qubit
was genuinely at the peak, and (b) the gate/depth cost is below your exchange rate (next
section). A value that is cheap to recompute (a few gates) and held across a tall peak is the
ideal candidate; a value that took thousands of gates to build is usually not worth rebuilding.

### Live-range shortening / passenger relocation

A **passenger** is allocated early and consumed late but does nothing at the peak — it just
rides through. You don't need to uncompute it; just **move its endpoints**: allocate it as late
as possible (right before its first use) and free it as early as possible (right after its last
use). If both the first-use and last-use sit outside the peak window, the passenger vanishes
from the binder. This is cheaper than a live-range hole (no recompute) — always check for
passengers first.

### Truncation: keep only the bits that matter

Scratch often holds more bits than carry information. Carry chains, high words of partial sums,
and intermediate registers frequently have **high bits that are provably zero** or that **don't
influence the observed output**. Keep only the low *W* bits that matter and don't allocate the
rest.

**Per-step scheduling.** When the same block runs in a loop, the *safe* truncation width usually
differs per iteration (early iterations need full width, late ones have shrunk and tolerate
aggressive trimming, or vice-versa). A single constant width must be set safe for the
worst iteration — over-provisioning all the others. Replacing the constant with a **per-step
schedule** `width(step)` lets each iteration be exactly as tight as it can tolerate, and in
particular lets you trim *only the iteration(s) sitting at the peak* without weakening the
delicate ones. This decouples the peak iteration from the rest, which a single global knob
cannot do.

**Why it's dangerous:** dropping a bit that *did* matter silently corrupts the result. Truncation
must be provably safe — the dropped bits are zero, or you've verified they never reach an
observed output on the inputs the circuit will actually see.

### Transcript / log compression

Reversibility forces the circuit to **record its data-dependent decisions** ("did I subtract
here? did I swap?") into fresh qubits — because by the time you want to undo a step, the data
that produced the decision has changed, so you can't recompute it; you must have logged it. This
log (the *transcript*) is often a large, long-lived chunk of the peak live set.

The log is compressible exactly when it has **structure**: if certain decision-patterns are
impossible or correlated, a naive one-qubit-per-bit encoding wastes space on combinations that
never occur. A denser encoding (spend bits only on reachable patterns — the Shannon / Morse-code
idea) stores the same information in fewer qubits.

**The hard constraint:** the codec must be **bijective** — a perfect, invertible 1-to-1 map. You
will uncompute the transcript later, so if two distinct histories ever collide to the same code,
the information needed to reverse the circuit is destroyed and the answer is wrong. Unlike
classical compression, *lossy is not an option.* Ship a self-test that proves the codec is
collision-free over all reachable inputs before trusting it. A related free win: bits you can
*prove* are always a constant (e.g. a known-zero high word) need not be stored at all.

**Finite-support tail codecs beat generic entropy arguments.** Do not only ask "how many bits of
entropy does this whole transcript have?" Also isolate late/tail windows and enumerate the exact
reachable support there. If a tail has, say, 32 reachable patterns, encode those patterns directly
into five code bits and stream the apply from that code instead of re-materializing the raw tail.
The general tactic is:

1. Identify a long-lived transcript slice that is still live at the binder.
2. Enumerate its reachable states for the narrow phase/tail where it is used.
3. Build an explicit reversible encoder/decoder for only that support.
4. Stream each apply slot from the code, recomputing only the slot's local controls, then clear it.
5. Add a self-test proving bijection, support coverage, and phase-clean forward/reverse behavior.

This is a width lever, so it is binary-failure: if the codec or streaming apply is not exactly
reversible, the circuit is structurally dirty. Validate the codec first, then re-measure the peak.

### Aliasing / dirty-scratch borrow

If you need scratch and a register already live holds a value you can **restore before it is next
observed**, borrow it as dirty scratch instead of allocating fresh qubits: use it, then undo your
changes to return it to its expected value. No new qubits enter the live set. The risk is
dependency: be certain nothing reads that register (as data *or* as a control, and including its
phase) between your borrow and your restore.

## Step 5 — Cost the shave: the qubit↔gate exchange rate

Every move above buys qubits with gates (and usually depth). Decide *before* implementing whether
the trade is worth it:

- Compute your **break-even rate** = (gates you'd add) ÷ (qubits you'd save). Compare it to the
  prevailing cost of a qubit in your objective. If your score is `qubits × gates`, a rough
  break-even is `gates_total / qubits_total` — spend fewer gates-per-qubit than that and you win.
- **Different layers of the peak have very different exchange rates — price each reducible layer
  separately; don't go by which *looks* most wasteful.** The peak is usually a **persistent floor**
  (long-lived state held across the whole region) plus a **transient** (the current step's working
  registers). Counter-intuitively, freeing the transient — which looks like wasteful scratch — is
  often the *expensive* qubit, because freeing it means recompute / dirty-borrow / finer chunking,
  i.e. lots of added gates. Meanwhile a long-lived **log/transcript** in the floor — which looks
  irreducible — is often the *cheap* qubit, because a denser or **streamed/partial-release**
  re-encoding shrinks it for very few gates. So when more than one layer is reducible, compute
  gates-per-qubit for *each* and take the cheap one (frequently: **compress the log before you free
  the scratch**). Verified instance: on one circuit, freeing transient working registers cost ~10×
  break-even (a qubit *record* but a score *loss*), while compressing the persistent transcript on
  the same circuit cost *under* break-even (an actual score *win*) — same −qubits, opposite verdicts.
- **Depth is the hidden tax.** Uncompute/recompute and fewer-ancilla tricks inflate circuit
  *depth*. A `qubits × gate-count` score doesn't see depth, but real error-corrected hardware
  does (it can dominate runtime). Prefer width reductions that are depth-neutral; treat a big
  depth blowup as a real cost even when the score ignores it.
- **Correctness/entanglement risk.** The most dangerous failure is freeing a qubit that *looks*
  dead but is still entangled — used later as a control, or carrying a phase that matters.
  Releasing it injects a silent phase error that output-value checks may not catch. Before any
  free/reuse, confirm the qubit is genuinely disentangled (uncomputed to |0⟩), not just
  value-unused.

## Step 6 — Re-measure and repeat

Apply the cheapest safe shave, re-run the Step-1 trace, read the new binder, and go again. Stop
when the binder is an irreducible structural floor (the essential data of the peak operation) or
when every remaining shave costs more than the exchange rate allows. Keep a short log of which
phase owned the peak at each height and which move dislodged it — that history is the map for the
next person (and tells you when you're going in circles).

**Treat "we've hit the floor" as a hypothesis to disprove, not a conclusion.** Before declaring a
layer irreducible, re-inventory (Step 2) and ask of each persistent register: is this *genuinely
essential data*, or just an **encoding** I haven't beaten yet? A long-lived log can still shrink
under a tail-specific codec or a streamed/partial release even when generic entropy coding looked
saturated — so a "this can't compress further" verdict from one coding model is weak evidence.
Re-measure the actual composition before each floor claim; more than one published "floor" has
fallen to a better encoding of the *same* state, not to a new algorithm. The reliable signal that
you've truly hit bottom is a *measured* composition where every remaining live qubit is essential
data of the peak operation — not an analysis that concluded a layer "should be" irreducible.

## Worked example (this lineage, for grounding)

A reversible elliptic-curve point-add circuit, scored `peak_qubits × Toffoli`, walked down like
this — each step a different binder, each shave a different move:

- **1211 qubits**, binder = a GCD-apply scratch block → **live-range hole** (free the block during
  a shift sub-phase that didn't use it, reacquire after) → **1193**, binder moves to the modular
  square.
- **1193**, binder = the square → **truncation** (one segment notch tighter) → **1192**, binder
  moves to a fold phase. (A follow-up that shrank the now-off-peak square was *peak-neutral* — it
  only cut gates, 0 qubits — exactly the "don't optimize off-peak for width" rule.)
- **1192**, binder = the fold → **per-step scheduling** of the fold's carry truncation + a
  **denser transcript codec** (head-11, with a bijectivity self-test) → **1185**, binder moves to
  a GCD-apply ripple.
- **1185**, binders = GCD apply/fold plus square → **finite-support tail codec + streaming apply**
  for a 32-state final transcript tail, **partial raw transcript release**, selective compare
  repairs, deeper per-step carry parking, and a square segment rebalance → **1170**. The important
  ablations were diagnostic: disabling streaming raised the GCD plateau to 1171; disabling the
  tail codec raised it to 1177; reverting the square segmentation made square bind at 1185. The
  win was not one magic knob — it was coordinated pressure on every co-equal binder.

Notice the pattern: every height was unlocked by attacking *that height's specific binder* with
the move that fit it, and the win always came from the phase that was currently tallest.

## Domain specifics

This skill is the domain-agnostic method. For the concrete knob names, peak-owner traces, island
validation, and exchange-rate numbers of the ECDSA-fail / quantum-ECC point-addition circuit, use
the companion **ecdsafail-circuit-optimization** skill, which applies this loop to that codebase.
