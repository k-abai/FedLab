"""Format resolved Polymarket data as instruction-tuning JSONL with deterministic 80/20 split."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent
PARQUET = DATA_DIR / "polymarket_resolved.parquet"
TRAIN_OUT = DATA_DIR / "train.jsonl"
EVAL_OUT = DATA_DIR / "eval.jsonl"


def _to_example(row: pd.Series) -> dict:
    question = str(row["question"]).strip()
    description = str(row.get("description", "") or "").strip()
    resolution = float(row["resolution"])
    return {
        "instruction": f"Will {question}?" if not question.lower().startswith("will ") else f"{question}?".replace("??", "?"),
        "input": description,
        "output": (
            f"Probability: {resolution:.2f}. "
            "Reasoning: Based on the resolution of this market, "
            f"the outcome was {'YES' if resolution >= 0.5 else 'NO'}."
        ),
    }


def _split_idx(key: str, ratio: float = 0.8) -> bool:
    """Deterministic split: True -> train, False -> eval. Hashed by question text."""
    h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return (h % 1000) / 1000.0 < ratio


def main() -> int:
    if not PARQUET.exists():
        print(f"Missing {PARQUET}. Run fetch_polymarket.py first.", file=sys.stderr)
        return 1

    df = pd.read_parquet(PARQUET)
    train, eval_ = [], []
    for _, row in df.iterrows():
        ex = _to_example(row)
        (train if _split_idx(ex["instruction"]) else eval_).append(ex)

    for path, rows in [(TRAIN_OUT, train), (EVAL_OUT, eval_)]:
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"Wrote {len(rows)} examples to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
