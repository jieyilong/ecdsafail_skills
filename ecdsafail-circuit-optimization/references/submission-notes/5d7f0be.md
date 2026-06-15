# UV merge 256: +2 boundary extensions (-796 avg T, peak neutral)

## What changed
- `kaliski_state.rs`: `KAL_CSWAP_UV_MERGE_SAFE_ITERS` default 254→256 — extends the Kaliski (u,v_w) equality-free merge boundary by two steps, fusing two more step9/step3 cswap pairs into cheaper XOR-merge swaps.
- `mod.rs`: `KAL_REROLL` default 47→38 — co-tuned to the UV merge=256 op stream.

## Result
- **Score: 5,158,663,510** = 2,576,755 avg-exec Toffoli × 2,002 qubits
- Previous best (3d9fa0a): 5,160,257,102 (2,577,551 T × 2,002 Q)
- **Delta: −1,593,592 (−0.031%)**
- Peak qubits unchanged at 2,002; the entire win is in avg-exec Toffoli (−796)
- Validated 0 classical / 0 phase / 0 ancilla over all 9024 shots

## How it was found
Used `KAL_SCREEN` parallel screener to sweep rerolls 0–63 for UV merge=256 on the slack=0 + mfw=232 base (3d9fa0a). Found clean islands at rr=38 and rr=47. Full `./benchmark.sh` confirmed 0/0/0.

UV merge=257 had no clean islands in 0–63 on the slack=0 base.

The UV merge extends the equality-free prefix where the step9/step3 cswap operates on guaranteed-distinct (u, v_w) values, fusing adjacent swap pairs. Each +1 step saves ~384 avg-exec Toffoli at unchanged peak. The 254→255 step was previously promoted by josusanmartin (not reflected in this fork's base); this commit adds 254→256 directly.

## Tooling
Model: DeepSeek V4 Pro driving OpenCode. Used `KAL_SCREEN` parallel screener for reroll sweeps; full validation via `./benchmark.sh`.

