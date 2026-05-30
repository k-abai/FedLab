"""Bags API integration scaffold.

FedLab is positioned as a Bags-powered verified model registry. This module is
the seam where Bags project/token stats flow in. It is intentionally a scaffold:

- It reads configuration from environment variables.
- If credentials are absent, every function returns structured *mock* data that
  clearly states `configured: false` / `mode: "mock"` so nothing is overclaimed.
- Endpoint paths are configurable placeholders. We do not call private APIs or
  invent credentials here.

Wiring real calls (tomorrow) means: set the env vars, fill in the real Bags
endpoint paths, and swap the `_mock_*` helpers for `_request(...)`.
"""
from __future__ import annotations

import os
from typing import Any

# Configurable; defaults are placeholders, not a claim about the real API surface.
BAGS_API_BASE_URL = os.getenv("BAGS_API_BASE_URL", "https://api.bags.fm")
BAGS_API_KEY = os.getenv("BAGS_API_KEY", "")
FEDLAB_BAGS_PROJECT_ID = os.getenv("FEDLAB_BAGS_PROJECT_ID", "")
FZIQ_TOKEN_ADDRESS = os.getenv("FZIQ_TOKEN_ADDRESS", "")

# Placeholder path templates. Real paths come from Bags docs at wiring time.
PROJECT_STATS_PATH = os.getenv("BAGS_PROJECT_STATS_PATH", "/v1/projects/{project_id}/stats")
TOKEN_STATS_PATH = os.getenv("BAGS_TOKEN_STATS_PATH", "/v1/tokens/{token_address}/stats")


def is_configured() -> bool:
    return bool(BAGS_API_KEY and FEDLAB_BAGS_PROJECT_ID)


def _request(path: str) -> dict[str, Any]:
    """Perform a GET against the Bags API. Only used when configured.

    `requests` is imported lazily so the module stays import-safe without it.
    """
    import requests  # local import keeps this module dependency-light to import

    url = BAGS_API_BASE_URL.rstrip("/") + path
    headers = {"Authorization": f"Bearer {BAGS_API_KEY}"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _mock_project_stats() -> dict[str, Any]:
    return {
        "configured": False,
        "mode": "mock",
        "project_id": FEDLAB_BAGS_PROJECT_ID or "not_set",
        "stats": {
            "holders": None,
            "market_cap_usd": None,
            "volume_24h_usd": None,
        },
        "note": "Set BAGS_API_KEY and FEDLAB_BAGS_PROJECT_ID to fetch live project stats.",
    }


def _mock_token_stats() -> dict[str, Any]:
    return {
        "configured": False,
        "mode": "mock",
        "token_address": FZIQ_TOKEN_ADDRESS or "not_set",
        "stats": {
            "price_usd": None,
            "holders": None,
            "supply": None,
        },
        "note": "Set BAGS_API_KEY and FZIQ_TOKEN_ADDRESS to fetch live token stats.",
    }


def get_project_stats() -> dict[str, Any]:
    if not is_configured():
        return _mock_project_stats()
    try:
        path = PROJECT_STATS_PATH.format(project_id=FEDLAB_BAGS_PROJECT_ID)
        data = _request(path)
        return {"configured": True, "mode": "live", "stats": data}
    except Exception as exc:  # network/credential failure -> structured, honest error
        return {"configured": True, "mode": "error", "error": str(exc)}


def get_token_stats() -> dict[str, Any]:
    if not (BAGS_API_KEY and FZIQ_TOKEN_ADDRESS):
        return _mock_token_stats()
    try:
        path = TOKEN_STATS_PATH.format(token_address=FZIQ_TOKEN_ADDRESS)
        data = _request(path)
        return {"configured": True, "mode": "live", "stats": data}
    except Exception as exc:
        return {"configured": True, "mode": "error", "error": str(exc)}


def get_integration_status() -> dict[str, Any]:
    """One-shot status for the API/frontend integration card."""
    return {
        "service": "bags",
        "configured": is_configured(),
        "mode": "live" if is_configured() else "not_configured",
        "base_url": BAGS_API_BASE_URL,
        "project_id_set": bool(FEDLAB_BAGS_PROJECT_ID),
        "api_key_set": bool(BAGS_API_KEY),
        "token_address_set": bool(FZIQ_TOKEN_ADDRESS),
        "required_env": [
            "BAGS_API_BASE_URL",
            "BAGS_API_KEY",
            "FEDLAB_BAGS_PROJECT_ID",
            "FZIQ_TOKEN_ADDRESS",
        ],
    }
