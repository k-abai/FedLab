"""Solana / Web3 integration scaffold.

The product story: each verified model carries an on-chain *proof of validation*
(a hash anchored on Solana) so the registry is auditable beyond FedLab's own
database. This module is the seam for that.

Scope guardrails (intentional):
- NO smart contract implementation.
- NO token minting or transfers.
- Wallet checks are dependency-light sanity checks, not full base58 verification.
- On-chain proof status is mock/not_configured until an RPC + anchoring program
  are wired.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "")
FZIQ_TOKEN_ADDRESS = os.getenv("FZIQ_TOKEN_ADDRESS", "")

# Solana base58 addresses are 32-44 chars from the base58 alphabet (no 0 O I l).
_BASE58_ADDR = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def is_configured() -> bool:
    return bool(SOLANA_RPC_URL)


def is_valid_wallet(address: str) -> bool:
    """Sanity-check a Solana wallet address shape. Not a full on-curve check."""
    return bool(_BASE58_ADDR.match(address or ""))


def build_validation_proof(model: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic, anchorable proof payload for a validated model.

    The `validation_hash` is a sha256 over the fields that define the validation
    event. Anchoring this hash on-chain is the future step; here we just produce
    the payload and the hash.
    """
    canonical = json.dumps(
        {
            "id": model.get("id"),
            "name": model.get("name"),
            "domain": model.get("domain"),
            "benchmark": model.get("benchmark"),
            "score": model.get("score"),
            "metric": model.get("metric"),
            "version": model.get("version"),
            "validation_date": model.get("validation_date"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    validation_hash = hashlib.sha256(canonical.encode()).hexdigest()
    return {
        "model_id": model.get("id"),
        "validation_hash": validation_hash,
        "canonical_payload": canonical,
        "anchor_status": "not_anchored",
        "note": "Anchor this hash on Solana to produce a public proof of validation.",
    }


def check_onchain_proof(validation_hash: str) -> dict[str, Any]:
    """Check whether a validation hash is anchored on-chain.

    Mock/not_configured until an RPC endpoint and anchoring program exist.
    """
    if not is_configured():
        return {
            "configured": False,
            "mode": "not_configured",
            "validation_hash": validation_hash,
            "anchored": None,
            "note": "Set SOLANA_RPC_URL (and wire an anchoring program) to verify proofs on-chain.",
        }
    # Placeholder: a real implementation would query the anchoring program/account.
    return {
        "configured": True,
        "mode": "mock",
        "validation_hash": validation_hash,
        "anchored": False,
        "note": "RPC configured but no anchoring program wired yet.",
    }


def get_integration_status() -> dict[str, Any]:
    return {
        "service": "solana",
        "configured": is_configured(),
        "mode": "live" if is_configured() else "not_configured",
        "rpc_url_set": bool(SOLANA_RPC_URL),
        "token_address_set": bool(FZIQ_TOKEN_ADDRESS),
        "required_env": ["SOLANA_RPC_URL", "FZIQ_TOKEN_ADDRESS"],
        "capabilities": {
            "wallet_sanity_check": True,
            "build_validation_proof": True,
            "onchain_anchor": False,
            "token_mint_or_transfer": False,
        },
    }
