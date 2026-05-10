"""Trimmed-mean aggregation of LoRA adapters that passed evaluation this round."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable, Sequence

TRIM_FRACTION = 0.10


def trimmed_mean(values: Sequence[float], trim: float = TRIM_FRACTION) -> float:
    if not values:
        return 0.0
    n = len(values)
    k = int(n * trim)
    sorted_vals = sorted(values)
    kept = sorted_vals[k : n - k] if n - 2 * k > 0 else sorted_vals
    return sum(kept) / len(kept)


def trimmed_mean_tensors(tensors: Sequence["torch.Tensor"], trim: float = TRIM_FRACTION):  # noqa: F821
    """Stack tensors along a new leading axis, drop top/bottom `trim` per-element, mean."""
    import torch
    if not tensors:
        raise ValueError("no tensors to aggregate")
    stacked = torch.stack(list(tensors), dim=0)
    n = stacked.shape[0]
    k = int(n * trim)
    if n - 2 * k <= 0:
        return stacked.mean(dim=0)
    sorted_vals, _ = torch.sort(stacked, dim=0)
    return sorted_vals[k : n - k].mean(dim=0)


def aggregate_adapters(adapter_paths: Iterable[Path], output_dir: Path) -> Path:
    """Trimmed-mean merge of LoRA adapter weight files (.safetensors / .bin) into output_dir."""
    import torch
    from safetensors.torch import load_file, save_file

    paths = [Path(p) for p in adapter_paths]
    if not paths:
        raise ValueError("no adapters to aggregate")

    state_dicts = []
    for p in paths:
        st = p / "adapter_model.safetensors"
        bn = p / "adapter_model.bin"
        if st.exists():
            state_dicts.append(load_file(str(st)))
        elif bn.exists():
            state_dicts.append(torch.load(str(bn), map_location="cpu"))
        else:
            raise FileNotFoundError(f"no adapter weights in {p}")

    keys = set(state_dicts[0].keys())
    merged = {}
    for k in keys:
        if not all(k in sd for sd in state_dicts):
            continue
        merged[k] = trimmed_mean_tensors([sd[k].float() for sd in state_dicts])

    output_dir.mkdir(parents=True, exist_ok=True)
    save_file(merged, str(output_dir / "adapter_model.safetensors"))
    cfg_src = paths[0] / "adapter_config.json"
    if cfg_src.exists():
        (output_dir / "adapter_config.json").write_bytes(cfg_src.read_bytes())
    return output_dir


def publish_to_ipfs(adapter_dir: Path) -> str:
    """Publish adapter dir to IPFS. Falls back to a deterministic mock CID if daemon unavailable."""
    api = os.getenv("IPFS_API", "/ip4/127.0.0.1/tcp/5001")
    try:
        import ipfshttpclient
        with ipfshttpclient.connect(api) as client:
            res = client.add(str(adapter_dir), recursive=True)
            top = res[-1] if isinstance(res, list) else res
            return top["Hash"]
    except Exception:
        h = hashlib.sha256()
        for p in sorted(adapter_dir.rglob("*")):
            if p.is_file():
                h.update(p.read_bytes())
        return f"Qm{h.hexdigest()[:44]}"
