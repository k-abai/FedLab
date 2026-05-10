"""Input validation, scoring decisions, and adapter hashing helpers."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, Literal

# Threshold below which a delta is considered "noise" (return rather than merge/burn).
NEUTRAL_BAND = 0.005

Action = Literal["merge", "return", "burn"]


def is_valid_hash(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Fa-f0-9]{64}", value or ""))


def is_valid_cid(value: str) -> bool:
    if not value:
        return False
    return bool(re.fullmatch(r"(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[0-9a-z]{50,})", value))


def is_valid_wallet(value: str) -> bool:
    return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", value or ""))


def decide_action(new_score: float, current_best: float, threshold: float) -> tuple[Action, float]:
    """Return (action, delta). Lower scores are better (Brier).

    delta = current_best - new_score (positive => improvement).
    """
    delta = current_best - new_score
    if delta >= threshold:
        return "merge", delta
    if abs(delta) <= NEUTRAL_BAND:
        return "return", delta
    return "burn", delta


def hash_adapter_files(paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def validate_contribution(payload: dict) -> list[str]:
    errors = []
    for field in ("adapter_hash", "contributor_wallet", "domain", "ipfs_cid"):
        if not payload.get(field):
            errors.append(f"missing field: {field}")
    if payload.get("adapter_hash") and not is_valid_hash(payload["adapter_hash"]):
        errors.append("adapter_hash must be 64-char hex sha256")
    if payload.get("contributor_wallet") and not is_valid_wallet(payload["contributor_wallet"]):
        errors.append("contributor_wallet must be a base58 Solana address")
    if payload.get("ipfs_cid") and not is_valid_cid(payload["ipfs_cid"]):
        errors.append("ipfs_cid must be a v0 (Qm...) or v1 (bafy...) CID")
    return errors
