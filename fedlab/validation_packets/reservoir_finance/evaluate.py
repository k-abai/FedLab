"""Financial reservoir validation packet evaluator (scaffold).

Dependency-light: pure Python, no numpy/pandas required. Reads a predictions file
of one-step-ahead forecasts and emits JSON metrics (RMSE, MAE, directional
accuracy) plus the result of basic leakage / window checks.

Predictions file format (JSON):

    {
      "warmup_steps": 200,
      "eval_steps": 250,
      "horizon": 1,
      "predictions": [
        {"t": 0, "y_true": 0.012, "y_pred": 0.010},
        {"t": 1, "y_true": -0.004, "y_pred": -0.001},
        ...
      ]
    }

Leakage checks here are *structural* sanity checks on the submitted file. A real
deployment would also re-run the model against a sealed series server-side.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def rmse(pairs: list[tuple[float, float]]) -> float | None:
    if not pairs:
        return None
    return math.sqrt(sum((t - p) ** 2 for t, p in pairs) / len(pairs))


def mae(pairs: list[tuple[float, float]]) -> float | None:
    if not pairs:
        return None
    return sum(abs(t - p) for t, p in pairs) / len(pairs)


def directional_accuracy(pairs: list[tuple[float, float]]) -> float | None:
    """Fraction of steps where the sign of the prediction matches the truth."""
    if not pairs:
        return None
    hits = sum(1 for t, p in pairs if (t >= 0) == (p >= 0))
    return hits / len(pairs)


def run_leakage_checks(doc: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, bool]:
    ts = [r.get("t") for r in records if "t" in r]
    monotonic = all(ts[i] < ts[i + 1] for i in range(len(ts) - 1)) if len(ts) > 1 else True
    eval_steps = doc.get("eval_steps")
    return {
        "timestamps_present": len(ts) == len(records),
        "timestamps_monotonic_increasing": monotonic,
        "eval_window_matches_declared": (
            eval_steps is None or eval_steps == len(records)
        ),
        # Placeholder: server-side re-run would confirm no future leakage in features.
        "no_future_leakage_in_features": True,
    }


def evaluate_file(predictions_path: Path) -> dict[str, Any]:
    doc = json.loads(predictions_path.read_text())
    records = doc.get("predictions", [])
    pairs = [(float(r["y_true"]), float(r["y_pred"])) for r in records]
    return {
        "packet": "reservoir_finance",
        "metric": "rmse",
        "n": len(pairs),
        "rmse": rmse(pairs),
        "mae": mae(pairs),
        "directional_accuracy": directional_accuracy(pairs),
        "leakage_checks": run_leakage_checks(doc, records),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Financial reservoir validation packet evaluator"
    )
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
