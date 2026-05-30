"""Verified model registry: load, query, validate, and append models.

File-backed and dependency-light on purpose. The registry is the core of the
FedLab MVP: an array of models, each tied to a benchmark validation packet and a
status (candidate / demo_verified / verified).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).parent / "models.json"

# Fields every registry row carries. None is allowed for the proof/token fields
# until live validation and Bags/Web3 wiring fill them in.
REQUIRED_FIELDS = (
    "id",
    "name",
    "domain",
    "benchmark",
    "score",
    "metric",
    "version",
    "status",
    "contributor_wallet",
    "validation_date",
    "validation_hash",
    "bags_token",
    "onchain_proof",
    "notes",
)

VALID_STATUSES = ("candidate", "demo_verified", "candidate_verified", "verified")

_LOCK = threading.Lock()


def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Return the full registry document ({"schema_version", "models": [...]})."""
    p = path or REGISTRY_PATH
    if not p.exists():
        return {"schema_version": 1, "models": []}
    return json.loads(p.read_text())


def list_models(path: Path | None = None) -> list[dict[str, Any]]:
    return load_registry(path).get("models", [])


def get_model(model_id: str, path: Path | None = None) -> dict[str, Any] | None:
    for model in list_models(path):
        if model.get("id") == model_id:
            return model
    return None


def validate_model(model: dict[str, Any]) -> list[str]:
    """Minimal schema check. Returns a list of human-readable errors (empty == ok)."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in model:
            errors.append(f"missing field: {field}")
    if not model.get("id"):
        errors.append("id must be non-empty")
    if not model.get("name"):
        errors.append("name must be non-empty")
    status = model.get("status")
    if status is not None and status not in VALID_STATUSES:
        errors.append(f"status must be one of {VALID_STATUSES}")
    return errors


def append_model(model: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    """Validate and append a model row to the registry file.

    Raises ValueError on schema failure or duplicate id. Thread-safe for the
    single-process file-backed MVP.
    """
    errors = validate_model(model)
    if errors:
        raise ValueError("; ".join(errors))

    p = path or REGISTRY_PATH
    with _LOCK:
        doc = load_registry(p)
        models = doc.setdefault("models", [])
        if any(m.get("id") == model["id"] for m in models):
            raise ValueError(f"duplicate id: {model['id']}")
        models.append(model)
        p.write_text(json.dumps(doc, indent=2) + "\n")
    return model


def new_model_row(
    *,
    model_id: str,
    name: str,
    domain: str,
    benchmark: str,
    score: str = "pending",
    metric: str = "",
    version: str = "0.1.0",
    status: str = "candidate",
    contributor_wallet: str = "",
    validation_date: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Build a full registry row with proof/token fields nulled out."""
    return {
        "id": model_id,
        "name": name,
        "domain": domain,
        "benchmark": benchmark,
        "score": score,
        "metric": metric,
        "version": version,
        "status": status,
        "contributor_wallet": contributor_wallet,
        "validation_date": validation_date,
        "validation_hash": None,
        "bags_token": None,
        "onchain_proof": None,
        "notes": notes,
    }
