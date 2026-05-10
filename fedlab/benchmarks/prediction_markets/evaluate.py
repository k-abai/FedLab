"""Brier-score evaluation over rotating Polymarket subset."""
from __future__ import annotations

import re
from typing import Any

from .rotate import select_subset

_PROB_RE = re.compile(r"probability[^0-9]*([0-9]*\.?[0-9]+)", re.IGNORECASE)


def _resolution_from_output(output: str) -> float | None:
    m = _PROB_RE.search(output or "")
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    if v > 1.0:
        v /= 100.0
    return max(0.0, min(1.0, v))


def brier_score(prob: float, truth: float) -> float:
    return (prob - truth) ** 2


def run(model: Any, week_seed: str) -> dict[str, Any]:
    """Run prediction-market eval. `model` must expose .predict_probability(question, context) -> float."""
    subset = select_subset(week_seed)
    if not subset:
        return {
            "mean_score": float("nan"),
            "n_questions": 0,
            "week_seed": week_seed,
            "domain": "prediction_markets",
        }

    scores = []
    for ex in subset:
        truth = _resolution_from_output(ex.get("output", ""))
        if truth is None:
            continue
        question = ex.get("instruction", "")
        context = ex.get("input", "")
        try:
            prob = float(model.predict_probability(question, context))
        except Exception:
            prob = 0.5
        prob = max(0.0, min(1.0, prob))
        scores.append(brier_score(prob, truth))

    mean = sum(scores) / len(scores) if scores else float("nan")
    return {
        "mean_score": mean,
        "n_questions": len(scores),
        "week_seed": week_seed,
        "domain": "prediction_markets",
    }
