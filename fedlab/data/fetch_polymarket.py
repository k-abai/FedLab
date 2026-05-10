"""Fetch resolved binary markets from Polymarket and save as parquet."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import requests

POLYMARKET_API = "https://gamma-api.polymarket.com/markets"
DEFAULT_OUTPUT = Path(__file__).parent / "polymarket_resolved.parquet"


def _coerce_resolution(market: dict) -> float | None:
    """Extract a {0.0, 1.0} resolution from the various Polymarket payload shapes."""
    outcome_prices = market.get("outcomePrices") or market.get("outcome_prices")
    outcomes = market.get("outcomes")

    if isinstance(outcome_prices, str):
        try:
            outcome_prices = json.loads(outcome_prices)
        except json.JSONDecodeError:
            outcome_prices = None
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except json.JSONDecodeError:
            outcomes = None

    if isinstance(outcome_prices, list) and isinstance(outcomes, list) and outcome_prices and outcomes:
        try:
            yes_idx = next(
                (i for i, o in enumerate(outcomes) if str(o).strip().lower() == "yes"),
                0,
            )
            yes_price = float(outcome_prices[yes_idx])
        except (TypeError, ValueError, IndexError):
            return None
        if yes_price >= 0.99:
            return 1.0
        if yes_price <= 0.01:
            return 0.0
        return None

    for key in ("resolvedOutcome", "resolved_outcome", "winningOutcome", "result"):
        val = market.get(key)
        if isinstance(val, str):
            v = val.strip().lower()
            if v in {"yes", "true", "1"}:
                return 1.0
            if v in {"no", "false", "0"}:
                return 0.0
    return None


def fetch_resolved_markets(limit: int = 500) -> pd.DataFrame:
    params = {
        "closed": "true",
        "limit": limit,
        "order": "volume",
        "ascending": "false",
    }
    resp = requests.get(POLYMARKET_API, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    markets = payload if isinstance(payload, list) else payload.get("data", [])

    rows = []
    for m in markets:
        resolution = _coerce_resolution(m)
        if resolution is None:
            continue
        rows.append(
            {
                "question": m.get("question") or m.get("title") or "",
                "resolution": resolution,
                "volume": float(m.get("volume") or 0.0),
                "description": m.get("description") or "",
                "end_date": m.get("endDate") or m.get("end_date") or "",
            }
        )
    return pd.DataFrame(rows)


def main(output: Path = DEFAULT_OUTPUT) -> int:
    try:
        df = fetch_resolved_markets()
    except requests.RequestException as e:
        print(f"Error fetching Polymarket data: {e}", file=sys.stderr)
        return 1

    if df.empty:
        print("No resolved binary markets returned.", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)
    print(f"Wrote {len(df)} markets to {output}")
    print("Resolution distribution:")
    print(df["resolution"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
