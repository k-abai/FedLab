"""Loader/index for validation packet metadata.

Each packet lives in its own directory with a `packet.json`. This module
discovers them so the API can list packets and serve one by id without a
hardcoded registry.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PACKETS_DIR = Path(__file__).parent


def list_packets() -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for packet_file in sorted(PACKETS_DIR.glob("*/packet.json")):
        try:
            packets.append(json.loads(packet_file.read_text()))
        except json.JSONDecodeError:
            continue
    return packets


def get_packet(packet_id: str) -> dict[str, Any] | None:
    for packet in list_packets():
        if packet.get("id") == packet_id:
            return packet
    return None
