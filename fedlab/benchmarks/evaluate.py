"""Generic benchmark dispatcher with rotating weekly seeds."""
from __future__ import annotations

import hashlib
import importlib
import json
import time
from pathlib import Path
from typing import Any, Callable

REGISTRY_PATH = Path(__file__).parent / "registry.json"


def current_week_seed(now: float | None = None) -> str:
    week_number = int(now if now is not None else time.time()) // (7 * 24 * 3600)
    return hashlib.sha256(f"fedlab-{week_number}".encode()).hexdigest()


def load_registry() -> dict[str, dict[str, Any]]:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def _resolve_module(domain: str) -> Any:
    registry = load_registry()
    if domain not in registry:
        raise KeyError(f"Unknown benchmark domain: {domain}")
    return importlib.import_module(registry[domain]["module"])


def evaluate(model: Any, domain: str, week_seed: str | None = None) -> dict[str, Any]:
    """Evaluate `model` on `domain` using `week_seed`. Returns dict with mean_score etc."""
    seed = week_seed or current_week_seed()
    mod = _resolve_module(domain)
    fn: Callable = getattr(mod, "run")
    result = fn(model, seed)
    result.setdefault("domain", domain)
    result.setdefault("week_seed", seed)
    return result
