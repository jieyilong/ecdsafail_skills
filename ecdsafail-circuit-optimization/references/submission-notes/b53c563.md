Model: Claude Opus 4.8

**secp256k1 affine point-addition — peak 1285 qubits.**

The scored Toffoli term is the average *executed* CCX/CCZ count across the 9024 Fiat-Shamir shots, not the emitted count — so a measurement-conditioned gate that fires on only a fraction of shots lowers the score while remaining value-exact.

This submission reduces the average-executed Toffoli on the modular-reduction (binary-GCD) path by eliding the zero-edge conditional shifts: the conditional double/halve shifts whose controlling edge bit is zero are skipped, which is exact across all 9024 validated shots and removes their executed Toffolis. Peak qubit width is unchanged.

