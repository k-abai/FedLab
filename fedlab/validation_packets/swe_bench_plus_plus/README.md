# SWE-bench++ Validation Packet

A validation packet is a self-contained, standardized definition of *how a model
in a given domain gets verified*. For software-engineering models, that packet is
**SWE-bench++**.

## Concept

A SWE model is given a real GitHub issue and the repository snapshot at the time
the issue was opened. It must produce a **patch** that:

1. makes the previously failing test(s) pass, and
2. does not break any test that was already passing.

A task is *resolved* when both conditions hold. The headline metric is the
**resolved rate** — the fraction of held-out tasks resolved.

## Why "++"

The public SWE-bench task format is the starting point. SWE-bench++ adds:

- **A private held-out split** — tasks not present in any public training set, to
  reduce contamination of the reported score.
- **Issue-hash blocklist** — known-leaked issues are excluded.
- **In-repo-only patches** — a submitted patch may only modify files that exist in
  the repository snapshot, so a model can't "cheat" by writing to the test runner.

These are the `leakage_checks` listed in `packet.json`.

## Evaluation (scaffold)

```bash
python -m validation_packets.swe_bench_plus_plus.evaluate --predictions preds.jsonl
```

The packet ships as a definition (`packet.json`). The live harness — container
build, patch application, and test execution — is intentionally **not** included
in this scaffold. Wiring it to a real runner is a "tomorrow" task.

## Honesty note

The `current_best_score` of `18.4% pass` is an **illustrative target** for the
demo registry row `swe-model-v0`. It is labeled `demo` in `packet.json` and is not
a measured result.
