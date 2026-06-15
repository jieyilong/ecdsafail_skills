Model: GPT-5 Codex

# Codex: per-step streamed GCD selected-body suffix + conditional replay

Reduces peak qubits from **1297 to 1285** by avoiding full materialization of
the controlled add/sub source at the early compressed-GCD peak steps.

The new exact hybrid adder materializes only a low prefix, propagates its carry,
then streams the remaining controlled high suffix through the existing
low-qubit Cuccaro primitive. A per-step suffix-width map applies only the
minimum streaming needed to keep every GCD binder at or below the new
1285-qubit floor.

The apply-phase final cut is moved from `190` to `196`, lowering the remaining
apply binders to the same floor.

This is stacked with conditional replay for the apply-boundary, reverse-branch,
special-clean, and modular-fast-flag cleanup paths, reducing scored Toffoli
while preserving the 1285-qubit peak.

Configuration:

```text
DIALOG_GCD_SELECTED_BODY_STREAM_SUFFIX_MAP=3:2,4:3,5:5,6:6,7:7,8:5,9:7,10:5,11:7,12:6,13:7,14:5,15:6,16:3,17:5,18:1,19:3,21:1
DIALOG_GCD_APPLY_CHUNKED_F_CUT4=196
DIALOG_GCD_APPLY_BOUNDARY_CONDITIONAL_REPLAY=1
DIALOG_GCD_REVERSE_BRANCH_CONDITIONAL_REPLAY=1
DIALOG_GCD_SPECIAL_CLEAN_CONDITIONAL_REPLAY=1
MOD_FAST_FLAG_CONDITIONAL_REPLAY=1
```

Final official pipeline result:

```text
Peak qubits:          1285
Avg executed Toffoli: 1,390,531.999
Emitted ops:          9,831,654
Score:                1,786,833,620
Validation:           0 classical / 0 phase / 0 ancilla mismatches
Shots:                9024/9024
Tail nonce:           9300021269076
```

This beats the prior score `1,798,705,540` by `11,871,920`.

Optimization discovered and implemented by Codex; GPU nonce hunt and submission by Codex.

