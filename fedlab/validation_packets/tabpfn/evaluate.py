"""TabPFN validation packet evaluator (scaffold).

Dependency-light by design: no TabPFN, no numpy, no sklearn required. It reads a
predictions file and emits JSON metrics. The intent is to standardize *how a
tabular model is scored*, not to ship a full tabular benchmark today.

Predictions file format (JSON):

    {
      "predictions": [
        {"id": "row-0", "y_true": 1, "y_score": 0.92},
        {"id": "row-1", "y_true": 0, "y_score": 0.10},
        ...
      ]
    }

`y_true` is the binary label (0/1). `y_score` is the model's predicted
probability of the positive class.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def roc_auc(pairs: list[tuple[int, float]]) -> float | None:
    """Rank-based ROC-AUC (Mann-Whitney U). Pure Python, ties handled by avg rank."""
    pos = [s for y, s in pairs if y == 1]
    neg = [s for y, s in pairs if y == 0]
    if not pos or not neg:
        return None

    ranked = sorted(pairs, key=lambda p: p[1])
    # Assign average ranks (1-based) to handle ties.
    ranks: dict[int, float] = {}
    i = 0
    n = len(ranked)
    while i < n:
        j = i
        while j < n and ranked[j][1] == ranked[i][1]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0  # average of 1-based positions [i+1, j]
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    sum_pos_ranks = sum(rank for idx, rank in ranks.items() if ranked[idx][0] == 1)
    n_pos, n_neg = len(pos), len(neg)
    u = sum_pos_ranks - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def accuracy(pairs: list[tuple[int, float]], threshold: float = 0.5) -> float | None:
    if not pairs:
        return None
    correct = sum(1 for y, s in pairs if int(s >= threshold) == y)
    return correct / len(pairs)


def run_leakage_checks(records: list[dict[str, Any]]) -> dict[str, bool]:
    ids = [r.get("id") for r in records if "id" in r]
    return {
        "row_ids_present": len(ids) == len(records),
        "row_ids_unique": len(set(ids)) == len(ids),
        "scores_in_unit_interval": all(
            0.0 <= float(r.get("y_score", -1)) <= 1.0 for r in records
        ),
    }


def evaluate_file(predictions_path: Path) -> dict[str, Any]:
    doc = json.loads(predictions_path.read_text())
    records = doc.get("predictions", [])
    pairs = [(int(r["y_true"]), float(r["y_score"])) for r in records]
    return {
        "packet": "tabpfn",
        "metric": "roc_auc",
        "n": len(pairs),
        "roc_auc": roc_auc(pairs),
        "accuracy": accuracy(pairs),
        "leakage_checks": run_leakage_checks(records),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TabPFN validation packet evaluator")
    parser.add_argument(
        "--predictions", required=True, help="Path to predictions JSON file"
    )
    args = parser.parse_args(argv)

    path = Path(args.predictions)
    if not path.exists():
        print(json.dumps({"error": f"file not found: {path}"}))
        return 1

    print(json.dumps(evaluate_file(path), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
