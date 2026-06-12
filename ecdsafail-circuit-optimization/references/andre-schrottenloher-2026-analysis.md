# Andre Schrottenloher 2026 Paper Analysis

Use this reference when the task mentions Andre Schrottenloher, arXiv
2606.02235, the 1192/1208 qubit counts, dialog-transcript in-place modular
multiplication, EEA/Bezout splitting, pseudo-Mersenne arithmetic, or reproducing
the Qarton `ec-point-addition` reference implementation.

This file is deliberately more detailed than `SKILL.md`. Keep `SKILL.md` as the
short operating checklist; load this reference only when the task needs the
paper-level architecture, formulas, source map, or route-design lessons.

## Source Snapshot

- Paper: Andre Schrottenloher, "Optimized Point Addition Circuits for Elliptic
  Curve Discrete Logarithms", arXiv:2606.02235v1, 1 Jun 2026.
- Local PDF: `/Users/jieyilong/Personal/research/ShorOptimization/shor_optimization_workspace/readings/Schrottenloher_EC_point_addition.pdf`
- Local extracted text:
  `/Users/jieyilong/Personal/research/ShorOptimization/shor_optimization_workspace/research/papers/2606.02235v1.clean.txt`
- Reference implementation:
  `https://gitlab.inria.fr/capsule/qarton-projects/ec-point-addition`
- Local analyzed checkout:
  `/Users/jieyilong/Personal/research/ShorOptimization/shor_optimization_workspace/repos/ec-point-addition`
- Analyzed implementation commit:
  `d8d2473cb43cf9c8fef349630dbdabfd8bd49a05`
- Commit date/subject: `2026-06-01 19:26:51 +0200`, `testing script`
- Main implementation files:
  - `build_circuit.py`
  - `gcd_stats.py`
  - `point_add/point_add.py`
  - `point_add/gcd.py`
  - `point_add/gcd_functions.py`
  - `point_add/compressor.py`
  - `point_add/efficient_mod_arithmetic.py`
  - `point_add/special_mod_arithmetic.py`

Refresh this reference after pulling a newer paper or implementation commit. When
the paper table and code comments disagree, treat the paper table as the
published resource claim and rerun `build_circuit.py` before relying on the code
snapshot. The analyzed `build_circuit.py` comment says 1193 qubits for the
space-optimized circuit, while the paper table reports 1192 qubits.

## Headline Resource Claims

The paper compares against Babbush et al. for a single secp256k1 point-addition
circuit. The window-selector register is not included in these point-addition
numbers.

| route | qubits | Toffoli metric | source |
|---|---:|---:|---|
| Babbush space-optimized secp256k1 | 1175 | `2^21.36` | Table 1 |
| Babbush gate-optimized secp256k1 | 1425 | `2^21.00` | Table 1 |
| Schrottenloher space-optimized secp256k1 | 1192 | `2^21.19` | Table 1 |
| Schrottenloher gate-optimized secp256k1 | 1446 | `2^20.83` | Table 1 |
| Schrottenloher space-optimized generic prime | 1192 | `2^21.78` | Table 1 |
| Schrottenloher gate-optimized generic prime | 1446 | `2^21.42` | Table 1 |

For the full windowed Shor point-multiplication estimate, the paper adds the
`w=16` window register and uses 28 windowed point additions:

```text
single-point-add qubits + 16 window qubits = Shor-window qubits
1192 + 16 = 1208
1446 + 16 = 1462
```

The full Toffoli estimate is:

```text
28 * (Q_A + 3 * 2^16)
```

where `Q_A` is the single windowed-add Toffoli cost. For secp256k1 the paper
reports:

- space-optimized: `1208 q`, `2^26.11` Toffoli
- gate-optimized: `1462 q`, `2^25.78` Toffoli

Read the 1192/1208 distinction carefully:

- `1192` is the standalone point-addition circuit in Table 1.
- `1208` is the full Shor-window circuit in Table 2 after adding the 16-bit
  selector window.
- A reported `1195` is not the paper's table value; it is likely an
  implementation/version/accounting drift or a rounded/misremembered number.

## Why The Qubit Count Is Around 1192

The core asymptotic accounting is:

```text
peak ~= compressed EEA transcript + two n-bit modular registers + finite overhead
     ~= 2.355n + 2n + O(sqrt(n))
     ~= 4.355n + O(sqrt(n))
```

For `n=256`, the constants are concrete:

```text
expected_iterations = ceil((1.413*n + 2.4*sqrt(n)) / 3) * 3
                    = ceil((361.728 + 38.4) / 3) * 3
                    = 402

compressed_transcript_bits = ceil(expected_iterations / 3) * 5
                           = 134 * 5
                           = 670

two modular registers = 2 * 256 = 512

670 + 512 = 1182
```

The remaining roughly 10 qubits are finite-size/control/padding overhead in the
space-optimized implementation, giving the paper's 1192-qubit claim.

The reason this can be close to 4.355n is that the peak is during Bezout
reconstruction, not during the Euclidean/GCD construction. During GCD
construction, the `(u,v)` registers are shrinking while their freed high bits
are reused for the transcript. During Bezout reconstruction, the fixed transcript
co-resides with two n-bit modular registers.

The paper notes a theoretical lower direction of about:

```text
4.12n + O(sqrt(n))
```

This comes from variable-length expected garbage rather than the implemented
fixed-size compressor. Each iteration always stores `b0`, but stores `b0&b1`
only when `b0=1`, so the expected output is about 1.5 bits/iteration:

```text
iterations ~= 1.413n
expected garbage ~= 1.5 * 1.413n ~= 2.12n
peak floor ~= 2.12n + 2n = 4.12n
```

The implemented 3-iteration to 5-bit compressor uses
`5/3 = 1.666...` bits/iteration and therefore lands at:

```text
1.413n * 5/3 ~= 2.355n
```

The gap between `4.12n` and `4.355n` is the price of using the simple fixed-size
compressor instead of a more entropy-tight representation.

## High-Level Point-Addition Structure

The paper uses a standard Shor setup with semiclassical Fourier transform and
qubit recycling. The input exponent registers do not dominate the logical qubit
count; the point-addition circuit does.

The point multiplication is decomposed into windowed additions with window size
`w=16`. For secp256k1, the first addition can be replaced by a lookup and the
last three can be removed with classical post-processing, leaving 28 point
additions.

The point addition itself uses affine coordinates and follows the Gouzien/Ruiz/
Le Regent/Guillaud/Sangouard style sequence:

1. Look up the selected constant point `(x1,y1)`.
2. Form differences in the live point registers.
3. Unlookup `(x1,y1)`.
4. Use inverse in-place multiplication to divide by `x2`.
5. Look up `3*x1`.
6. Do the controlled modular square/subtract.
7. Use in-place multiplication again.
8. Negate and finish with a final lookup/unlookup of `(x1,y1)`.

The expensive parts are:

- two in-place modular multiplications
- one controlled modular square
- three table lookups
- O(n)-sized add/sub/negate glue

The table lookups are much cheaper than the arithmetic. They matter for the full
Shor formula through `3 * 2^w`, but they are not the qubit peak.

## Dialog-Transcript In-Place Multiplication

The core idea is to split extended Euclidean inversion into two stages:

1. Run a Euclidean/GCD construction on `(u,v)=(q,x)`.
2. Store the choices in a compact transcript.
3. Later apply the transcript to a separate modular pair `(r,s)`.

This avoids co-residing `(u,v)` and `(r,s)` during the whole inversion.

### Algorithm 2: Euclidean Construction

Each fixed-count iteration computes:

```text
b0 = v mod 2
b1 = u > v
store b0 and (b0 & b1)
if b0 & b1: swap(u,v)
if b0: v -= u
v >>= 1
```

The paper's heuristic:

- each iteration removes at least one factor of two;
- with probability about 1/2, the subtract step removes another bit;
- the expected product shrink is `3/8`;
- expected iterations are about `1.413n`;
- standard deviation is about `0.6*sqrt(n)`;
- the implementation uses `1.413n + 2.4*sqrt(n)`, rounded to a multiple of 3.

Reference implementation constants:

```text
ITERATIONS_VAR = 2.4
U_PAD_VAR = 2.3
TRUNCATE = 40
STEP = 2
```

`gcd_stats.py` empirically checks the iteration distribution and register
padding. `gcd_functions.py` implements the classical version. `gcd.py` implements
the reversible circuit.

### Register Sharing During GCD

At iteration `i`, the active widths of `u` and `v` are bounded by:

```text
n - 0.5 * log2(8/3) * i + c_pad*sqrt(n)
```

The high bits freed by this shrink are reused to store transcript bits. This is
the space-saving move. It is not merely "use fewer bits for u and v"; it is
"move the transcript into the holes opened by shrinking u and v".

For ECDSA Fail route design, the equivalent move is to prove that a high limb,
carry slice, compare suffix, or future transcript slot is clean at a particular
iteration and reuse that specific qubit range, rather than adding a separate
sidecar.

### Transcript Encoding

Each iteration produces a pair `(b0, b0&b1)`. Only three states are valid:

```text
(0,0), (1,0), (1,1)
```

The paper groups three iterations at a time:

```text
3 valid ternary symbols = 3^3 = 27 states < 2^5
```

So six raw bits become five stored bits. The compressor is an ad hoc in-place
5-Toffoli circuit whose last input bit is released on valid inputs.

Consequences:

- fixed transcript size avoids an extra O(sqrt n) variation buffer;
- compressor cost is negligible compared with arithmetic;
- transcript density is `5/3` bits per GCD iteration;
- for n=256, the fixed transcript is 670 bits.

The reference implementation source is `point_add/compressor.py`.

### Algorithm 3: Bezout Reconstruction

The transcript is read in reverse. The modular pair `(r,s)` is updated with:

```text
s <- 2s mod q
if b0: s <- s + r mod q
if b0 & b1: swap(r,s)
```

The load-bearing observation is linearity. If the usual Bezout reconstruction
starts from `(1,0)` and yields `(0,x^-1)`, then starting from `(y,0)` yields
`(0, y*x^-1)` or, depending on transcript direction, the corresponding product
variant. This means the same transcript performs inversion and multiplication
of a second register without materializing an explicit inverse.

This is the key reason the circuit avoids the older pattern:

```text
compute inverse -> multiply -> uncompute inverse
```

Instead it uses:

```text
consume x into transcript -> apply transcript to y -> restore x from transcript
```

Only the GCD construction runs forward and backward. The modular Bezout
reconstruction runs once.

### Algorithm 4: In-Place Modular Multiplication

On input `(x,y)`:

1. Convert `x` to transcript `g` using Algorithm 2.
2. Apply Algorithm 3 to `(y,0)` using `g`.
3. Swap/clean the temporary zero register.
4. Reverse Algorithm 2 to restore `x` and erase `g`.

Reference implementation:

- `point_add/gcd.py::ToBitVector`
- `point_add/gcd.py::ApplyBitVector`
- `point_add/gcd.py::IPModMul`

## Space-Optimized Vs Gate-Optimized Variant

The paper's two main variants differ mostly in which adder family is used where
the peak allows it.

Space-optimized:

- During Bezout reconstruction, use low-space CDKM-style controlled adders and
  Gidney constant adders with dirty ancilla.
- During GCD construction, exploit the fact that about `n` qubits of headroom
  are available and use Gidney/hybrid adders for subtraction.
- Peak stays at about 1192 qubits for secp256k1.

Gate-optimized:

- Spend roughly `n` additional ancillas during reconstruction.
- Use Gidney adders/comparators more aggressively.
- Peak rises to 1446 qubits, while Toffoli drops from `2^21.19` to `2^20.83`.

In the reference implementation this is controlled by `--gate_efficient`, which
sets `gate_efficient=True` and switches the backends in `ApplyBitVector`.

ECDSA Fail lesson:

- Do not call every Gidney/vented/measurement-assisted adder "free". It is free
  only in non-peak phases such as GCD construction.
- During the peak-binding reconstruction/apply phase, every extra carry ancilla
  must be charged against score.

## Approximate Arithmetic And Failure Probability

The circuits are intentionally approximate. They only need a large constant
success probability on random inputs; exact arithmetic on all possible inputs is
not required.

The paper and code expose three main failure-probability knobs:

```text
ITERATIONS_VAR = 2.4      # GCD iteration tail
U_PAD_VAR = 2.3           # shrinking u/v register padding
TRUNCATE = 40             # MSB comparison width in GCD/apply
PADDING = 40              # low-limb pseudo-Mersenne carry padding
PADDING2 = 50             # square path padding
ITER_CAN_BE_Q = 50        # early apply iterations needing x+y=q handling
```

The paper reports all Table 1 circuits as having failure probability at most
`2^-13.3`, based on 10,000 random-input tests.

For ECDSA Fail, these knobs map directly to island-hunting intuition:

- Smaller iteration/padding/truncation values reduce qubits or Toffoli but make
  correctness nonce-dependent.
- A route can look structurally elegant yet fail uniformly if one approximate
  comparison or carry pad is too aggressive.
- Before large island search, run a short triage scan and validate candidate
  `cls / pha / anc` distributions.

## Pseudo-Mersenne Arithmetic

The generic-prime and secp256k1 rows have the same qubit counts but very
different Toffoli counts. The difference comes from secp256k1's prime:

```text
q = 2^256 - f
f = 2^32 + 977
```

The paper does not use Montgomery representation. It keeps standard integer
representation and exploits the pseudo-Mersenne form directly.

### Modular Doubling

The exact modular double would shift, subtract `q`, and conditionally add `q`
back. For a pseudo-Mersenne prime, if the high overflow bit is set, reduction by
`q = 2^256 - f` can be implemented as adding small `f` into low limbs.

Reference code:

- `point_add/special_mod_arithmetic.py::SpecialPrimeModularDouble`

The low-limb window is:

```text
lsbs = padding + bitlen(f)
```

Since `bitlen(f)=33`, `padding=40` means a 73-bit low-limb add.

### Controlled Modular Addition

The exact controlled modular add performs a controlled add, subtracts `q`, adds
`q` back if needed, and erases an overflow bit with a comparison. The
pseudo-Mersenne version:

1. performs the controlled add,
2. if overflow occurred, adds `f` into low limbs,
3. erases the overflow with a truncated MSB comparison.

There are two variants:

- one handles the rare but relevant `x+y=q` case;
- one assumes that case does not occur and is cheaper.

The `x+y=q` case appears in early empty/padding iterations of Bezout
reconstruction, so the implementation uses the expensive handler only for:

```text
ITER_CAN_BE_Q = 50
```

Reference code:

- `SpecialPrimeHandlePControlledModularAdder`
- `SpecialPrimeControlledModularAdder`

### Cost Breakdown

The paper's Table 3 attributes the secp256k1 space-optimized CCX cost roughly
as:

| component | secp256k1 | generic prime |
|---|---:|---:|
| modular squaring | 9% | 10% |
| in-place multiplier and inverse | 90% | 90% |
| Bezout reconstruction | 54% | 64% |
| GCD construction | 36% | 24% |
| controlled swap | 19% | 12% |
| hybrid adder | 22% | 14% |
| controlled modular adder | 39% | 45% |
| modular double | 8% | 24% |
| Gidney constant adder | 15% | 34% |

The secp256k1 gain is therefore mostly from replacing full-width add/subtract of
`q` with low-limb addition of `f`.

ECDSA Fail lesson:

- For secp256k1, pseudo-Mersenne folding is not an optional local cleanup; it is
  one of the dominant Toffoli levers.
- Any proposed carry truncation should be described as a probability/failure knob
  over low-limb `+f` carry propagation, not as an exact arithmetic identity unless
  the proof is explicit.

## What Transfers To ECDSA Fail

Use these as route-design patterns:

1. **Transcript/apply split**
   - Consume an input register into a compact transcript.
   - Apply the transcript to the second register.
   - Restore the input by reversing only the cheap construction.
   - Avoid materializing an explicit inverse.

2. **Register sharing with shrink certificates**
   - Use mathematical width bounds to reuse high bits of shrinking registers.
   - Document the invariant and live interval for each borrowed region.
   - Prefer clean reuse to dirty-scratch guessing.

3. **Peak-owner accounting**
   - The peak is usually reconstruction/apply, not GCD construction.
   - Optimize transcript width, decoded-window lifetime, and modular pair
     co-residence before shaving non-peak arithmetic.

4. **Use high-ancilla adders off peak**
   - GCD construction has headroom.
   - Reconstruction usually does not.
   - Treat adder choice as a global peak-budget decision.

5. **Exploit pseudo-Mersenne structure directly**
   - Replace add/subtract `q` with low-limb `+f`.
   - Tune MSB compare width and low-limb carry width as explicit failure knobs.
   - Validate phase and ancilla cleanliness; value-only tests are insufficient.

6. **Separate Shor-window accounting from point-add accounting**
   - Do not compare 1208 against a challenge route if the challenge measures only
     the point-add circuit.
   - Add the 16-bit window only when analyzing the full Shor resource estimate.

## What Does Not Transfer Directly

Be careful with these mismatches:

- The paper's circuit is a full windowed Shor point-addition architecture, while
  ECDSA Fail submissions may have extra benchmark scaffolding, Fiat-Shamir shots,
  or challenge-specific tail logic.
- The paper validates random-input success probability, not a nonce-island search
  with `cls / pha / anc` triage.
- The paper's Qarton simulator replaces exact arithmetic blocks with classical
  dummy functions during large random tests; ECDSA Fail validation must evaluate
  the actual challenge circuit semantics.
- The 1192/1208 numbers are published logical qubit counts, not automatic proof
  that a Codex route with similar ideas will land below 1211 without a fresh
  benchmark and island validation.

## Source Map

Use this map when verifying or extending the analysis:

- Paper overview and tables: `research/papers/2606.02235v1.clean.txt`
- Local paper PDF: `readings/Schrottenloher_EC_point_addition.pdf`
- Reference repo README: `repos/ec-point-addition/README.md`
- Build/reproduce counts: `repos/ec-point-addition/build_circuit.py`
- GCD statistics: `repos/ec-point-addition/gcd_stats.py`
- Euclidean transcript functions: `repos/ec-point-addition/point_add/gcd_functions.py`
- Reversible GCD/apply/IPModMul circuits: `repos/ec-point-addition/point_add/gcd.py`
- 3-iteration to 5-bit compressor: `repos/ec-point-addition/point_add/compressor.py`
- Generic approximate modular arithmetic:
  `repos/ec-point-addition/point_add/efficient_mod_arithmetic.py`
- Pseudo-Mersenne arithmetic:
  `repos/ec-point-addition/point_add/special_mod_arithmetic.py`
- Affine windowed point addition:
  `repos/ec-point-addition/point_add/point_add.py`

## Decision Guidance

When asked "what should we try next from Andre's paper?", prioritize:

1. **Peak-owner accounting around apply/Bezout reconstruction**
   - Identify which registers co-reside at the measured peak.
   - Shrink or retime the transcript/apply sidecar before spending effort on
     non-peak GCD details.

2. **Transcript density and decoded-window lifetime**
   - The paper's 3-to-5 compressor is simple and cheap.
   - A tighter radix encoding may save qubits only if the transcript is a peak
     owner and decoder lifetime is short.

3. **Clean high-bit reuse**
   - Mirror the paper's shrinking `(u,v)` register-sharing logic.
   - Apply it to carry pools, compare suffixes, future transcript slots, or square
     row buffers only with an explicit width invariant.

4. **Pseudo-Mersenne carry-width ladders**
   - Tune low-limb `+f` width and MSB compare width one notch at a time.
   - Treat every narrowing as a failure-probability change requiring triage.

5. **Gate-efficient adders only with spare peak budget**
   - Use Gidney/hybrid adders during non-peak phases.
   - Avoid spending an extra `n` qubits during reconstruction unless score math
     says the Toffoli reduction is worth it.

6. **Do not chase the wrong number**
   - For point-addition challenge work, reason from the 1192 point-add count.
   - For full Shor estimates, reason from the 1208 count.
   - If a source says 1193 or 1195, reproduce the count before using it as a
     target.

Always score-gate before island search. A Schrottenloher-inspired route is
useful only if measured/estimated `qubits * Toffoli` beats current SOTA and early
candidate triage does not show a uniform dirty fingerprint.
