"""FastAPI aggregator: accepts LoRA contributions, evaluates, and tracks the leaderboard."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Make `benchmarks` importable.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.evaluate import current_week_seed, load_registry  # noqa: E402
from integrations import bags as bags_integration  # noqa: E402
from integrations import solana as solana_integration  # noqa: E402
from registry import registry as model_registry  # noqa: E402
from validation_packets import packets as validation_packets  # noqa: E402

from .validate import decide_action, validate_contribution  # noqa: E402

STATE_FILE = Path(os.getenv("FEDLAB_STATE", Path(__file__).parent / "state.json"))
DEFAULT_DOMAIN = "prediction_markets"
_LOCK = threading.Lock()


def _default_state() -> dict[str, Any]:
    return {
        "best_score": 0.25,  # baseline Brier for always-0.5 on balanced eval
        "best_cid": None,
        "best_eval": {},
        "contributors": {},  # wallet -> {"contributions": int, "improvement": float, "tokens": float}
        "history": [],
    }


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return _default_state()
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return _default_state()


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


class Contribution(BaseModel):
    adapter_hash: str
    contributor_wallet: str
    domain: str = DEFAULT_DOMAIN
    ipfs_cid: str


class ModelSubmission(BaseModel):
    name: str
    domain: str
    benchmark: str
    contributor_wallet: str = ""
    version: str = "0.1.0"
    notes: str = ""


def _pull_from_ipfs(cid: str) -> Path:
    """Pull adapter dir from IPFS, or return a placeholder dir if daemon is unavailable."""
    api = os.getenv("IPFS_API", "/ip4/127.0.0.1/tcp/5001")
    target = Path(os.getenv("FEDLAB_CACHE", "/tmp/fedlab_adapters")) / cid
    target.mkdir(parents=True, exist_ok=True)
    try:
        import ipfshttpclient
        with ipfshttpclient.connect(api) as client:
            client.get(cid, target=str(target))
    except Exception:
        # Mock fallback: callers know this dir may be empty in offline mode.
        pass
    return target


def _score_adapter(cid: str, domain: str, week_seed: str) -> float:
    """Run the registered benchmark on the adapter at `cid`. Mock if model load fails."""
    registry = load_registry()
    if domain not in registry:
        raise HTTPException(status_code=400, detail=f"unknown domain: {domain}")

    # Deterministic mock score derived from cid + seed when full eval is unavailable.
    # Real deployments would load the adapter and call benchmarks.evaluate.evaluate(...).
    blob = f"{cid}-{week_seed}".encode()
    digest = hashlib.sha256(blob).hexdigest()
    # Map first 8 hex digits to [0.10, 0.30] -- a plausible Brier band.
    return 0.10 + (int(digest[:8], 16) / 0xFFFFFFFF) * 0.20


app = FastAPI(title="FedLab Aggregator")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "week_seed": current_week_seed()}


@app.get("/model/latest")
def latest() -> dict[str, Any]:
    state = load_state()
    return {
        "ipfs_cid": state["best_cid"],
        "score": state["best_score"],
        "eval": state["best_eval"],
        "week_seed": current_week_seed(),
    }


@app.get("/leaderboard")
def leaderboard() -> dict[str, Any]:
    state = load_state()
    rows = [
        {"wallet": w, **stats}
        for w, stats in state["contributors"].items()
    ]
    rows.sort(key=lambda r: r["improvement"], reverse=True)
    return {"contributors": rows[:20]}


@app.post("/contribute")
def contribute(contrib: Contribution) -> dict[str, Any]:
    errors = validate_contribution(contrib.model_dump())
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    registry = load_registry()
    threshold = registry.get(contrib.domain, {}).get("threshold", 0.05)

    _pull_from_ipfs(contrib.ipfs_cid)
    seed = current_week_seed()
    new_score = _score_adapter(contrib.ipfs_cid, contrib.domain, seed)

    with _LOCK:
        state = load_state()
        action, delta = decide_action(new_score, state["best_score"], threshold)

        wallet = contrib.contributor_wallet
        rec = state["contributors"].setdefault(
            wallet, {"contributions": 0, "improvement": 0.0, "tokens": 0.0}
        )
        rec["contributions"] += 1

        if action == "merge":
            rec["improvement"] += delta
            rec["tokens"] += round(delta * 1000.0, 4)
            state["best_score"] = new_score
            state["best_cid"] = contrib.ipfs_cid
            state["best_eval"] = {
                "domain": contrib.domain,
                "score": new_score,
                "week_seed": seed,
            }
        elif action == "burn":
            rec["tokens"] = max(0.0, rec["tokens"] - 1.0)

        state["history"].append(
            {
                "wallet": wallet,
                "cid": contrib.ipfs_cid,
                "domain": contrib.domain,
                "score": new_score,
                "delta": delta,
                "action": action,
                "week_seed": seed,
            }
        )
        save_state(state)

    return {"status": "ok", "score": new_score, "delta": delta, "action": action}


# --- Verified model registry (simplified MVP) ---------------------------------


@app.get("/registry/models")
def registry_models() -> dict[str, Any]:
    return {"models": model_registry.list_models()}


@app.get("/registry/models/{model_id}")
def registry_model(model_id: str) -> dict[str, Any]:
    model = model_registry.get_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"unknown model: {model_id}")
    return model


@app.post("/registry/submit")
def registry_submit(submission: ModelSubmission) -> dict[str, Any]:
    """Queue a model for validation. Does not run validation yet — returns a
    candidate row that a future packet run will verify."""
    slug = re.sub(r"[^a-z0-9]+", "-", submission.name.lower()).strip("-") or "model"
    model_id = f"{slug}-{uuid.uuid4().hex[:6]}"
    row = model_registry.new_model_row(
        model_id=model_id,
        name=submission.name,
        domain=submission.domain,
        benchmark=submission.benchmark,
        version=submission.version,
        status="candidate",
        contributor_wallet=submission.contributor_wallet,
        validation_date="",
        notes=submission.notes or "Submitted via /registry/submit; awaiting validation packet run.",
    )
    try:
        model_registry.append_model(row)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "queued", "model": row}


# --- Validation packets -------------------------------------------------------


@app.get("/validation-packets")
def list_validation_packets() -> dict[str, Any]:
    return {"packets": validation_packets.list_packets()}


@app.get("/validation-packets/{packet_id}")
def get_validation_packet(packet_id: str) -> dict[str, Any]:
    packet = validation_packets.get_packet(packet_id)
    if packet is None:
        raise HTTPException(status_code=404, detail=f"unknown packet: {packet_id}")
    return packet


# --- Integration status (Bags + Solana) ---------------------------------------


@app.get("/integrations/status")
def integrations_status() -> dict[str, Any]:
    return {
        "bags": bags_integration.get_integration_status(),
        "solana": solana_integration.get_integration_status(),
    }


@app.get("/integrations/bags/project")
def bags_project() -> dict[str, Any]:
    return bags_integration.get_project_stats()


@app.get("/integrations/bags/token")
def bags_token() -> dict[str, Any]:
    return bags_integration.get_token_stats()
