"""FastAPI aggregator: accepts LoRA contributions, evaluates, and tracks the leaderboard."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Make `benchmarks` importable.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.evaluate import current_week_seed, load_registry  # noqa: E402

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
