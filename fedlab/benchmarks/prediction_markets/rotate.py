"""Deterministic weekly subset selection over the prediction-market eval pool."""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path

EVAL_POOL = Path(__file__).resolve().parents[2] / "data" / "eval.jsonl"
SUBSET_SIZE = 200


def current_week_seed(now: float | None = None) -> str:
    week_number = int(now if now is not None else time.time()) // (7 * 24 * 3600)
    return hashlib.sha256(f"fedlab-{week_number}".encode()).hexdigest()


def load_pool(path: Path = EVAL_POOL) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def select_subset(week_seed: str, size: int = SUBSET_SIZE, pool: list[dict] | None = None) -> list[dict]:
    pool = pool if pool is not None else load_pool()
    if not pool:
        return []
    rng = random.Random(int(week_seed, 16))
    indexed = sorted(pool, key=lambda x: x.get("instruction", ""))
    if len(indexed) <= size:
        return indexed
    return rng.sample(indexed, size)
