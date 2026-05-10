"""Evaluate a trained adapter against eval.jsonl using Brier score."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `benchmarks` importable when running from repo root or model/ dir.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.evaluate import current_week_seed  # noqa: E402

ADAPTER_DIR = Path(__file__).parent / "adapters" / "v0"
EVAL_FILE = Path(__file__).resolve().parents[1] / "data" / "eval.jsonl"
RESULTS_FILE = Path(__file__).parent / "eval_results.json"

# Brier score for an always-0.5 baseline on a balanced eval set is 0.25.
BASELINE_BRIER = 0.25
IMPROVEMENT_THRESHOLD = 0.05


def load_eval(path: Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def parse_truth(output: str) -> float | None:
    import re
    m = re.search(r"probability[^0-9]*([0-9]*\.?[0-9]+)", output, re.IGNORECASE)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return max(0.0, min(1.0, v))


def evaluate(adapter_path: Path = ADAPTER_DIR, eval_file: Path = EVAL_FILE) -> dict:
    from .inference import PhiPredictor, load_model_and_tokenizer

    model, tokenizer = load_model_and_tokenizer(adapter_path=adapter_path if adapter_path.exists() else None)
    predictor = PhiPredictor(model, tokenizer)

    rows = load_eval(eval_file)
    scores = []
    for ex in rows:
        truth = parse_truth(ex.get("output", ""))
        if truth is None:
            continue
        prob = predictor.predict_probability(ex.get("instruction", ""), ex.get("input", ""))
        scores.append((prob - truth) ** 2)

    mean = sum(scores) / len(scores) if scores else float("nan")
    seed = current_week_seed()
    delta = BASELINE_BRIER - mean
    passed = bool(delta >= IMPROVEMENT_THRESHOLD)

    results = {
        "mean_brier": mean,
        "baseline_brier": BASELINE_BRIER,
        "delta": delta,
        "improvement_threshold": IMPROVEMENT_THRESHOLD,
        "passed": passed,
        "week_seed": seed,
        "n_questions": len(scores),
    }
    RESULTS_FILE.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    return results


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--adapter", type=Path, default=ADAPTER_DIR)
    p.add_argument("--eval-file", type=Path, default=EVAL_FILE)
    args = p.parse_args()
    evaluate(args.adapter, args.eval_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
