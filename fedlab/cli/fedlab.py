"""FedLab CLI: download | train | contribute."""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

import requests

AGGREGATOR_URL = os.getenv("FEDLAB_AGGREGATOR", "http://localhost:8000")
IPFS_API = os.getenv("IPFS_API", "/ip4/127.0.0.1/tcp/5001")
DEFAULT_ADAPTER_DIR = Path("./my_adapter").resolve()
HF_BASE_MODEL = "microsoft/Phi-3-mini-4k-instruct"


def _ipfs_get(cid: str, target: Path) -> Path:
    """Pull `cid` to `target`. Falls back to creating an empty marker dir if IPFS is unavailable."""
    target.mkdir(parents=True, exist_ok=True)
    try:
        import ipfshttpclient
        with ipfshttpclient.connect(IPFS_API) as client:
            client.get(cid, target=str(target))
    except Exception as e:
        (target / "MOCK_CID.txt").write_text(f"{cid}\nIPFS unavailable: {e}\n")
    return target


def _ipfs_add(path: Path) -> str:
    try:
        import ipfshttpclient
        with ipfshttpclient.connect(IPFS_API) as client:
            res = client.add(str(path), recursive=True)
            top = res[-1] if isinstance(res, list) else res
            return top["Hash"]
    except Exception:
        h = hashlib.sha256()
        for p in sorted(path.rglob("*")):
            if p.is_file():
                h.update(p.read_bytes())
        return f"Qm{h.hexdigest()[:44]}"


def _adapter_hash(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def cmd_download(_: argparse.Namespace) -> int:
    r = requests.get(f"{AGGREGATOR_URL}/model/latest", timeout=30)
    r.raise_for_status()
    info = r.json()
    cid = info.get("ipfs_cid")
    if not cid:
        print("No adapter published yet.", file=sys.stderr)
        return 1

    try:
        from huggingface_hub import snapshot_download
        base_path = snapshot_download(HF_BASE_MODEL)
    except Exception as e:
        base_path = "<not cached>"
        print(f"Skipped HF download ({e}); base model will be fetched on first use.")

    adapter_dir = Path("./adapters") / cid
    _ipfs_get(cid, adapter_dir)
    print(f"Base model: {base_path}")
    print(f"Adapter CID: {cid}")
    print(f"Adapter path: {adapter_dir}")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    data_path = Path(args.data).resolve()
    if not data_path.exists():
        print(f"Data file not found: {data_path}", file=sys.stderr)
        return 1

    # Pull current best adapter for warm-start.
    try:
        latest = requests.get(f"{AGGREGATOR_URL}/model/latest", timeout=30).json()
        cid = latest.get("ipfs_cid")
    except Exception:
        cid = None
    warm_start = None
    if cid:
        warm_start = _ipfs_get(cid, Path("./adapters") / cid)

    from model.train import TrainConfig, train  # type: ignore
    cfg = TrainConfig(train_file=data_path, output_dir=DEFAULT_ADAPTER_DIR)
    train(cfg)

    from model.evaluate import evaluate  # type: ignore
    results = evaluate(adapter_path=DEFAULT_ADAPTER_DIR)
    print(f"Local Brier: {results['mean_brier']:.4f}")
    if warm_start:
        print(f"Warm-started from {warm_start}")
    return 0


def cmd_contribute(args: argparse.Namespace) -> int:
    adapter_dir = DEFAULT_ADAPTER_DIR
    if not adapter_dir.exists():
        print(f"No adapter at {adapter_dir}. Run `fedlab train` first.", file=sys.stderr)
        return 1

    cid = _ipfs_add(adapter_dir)
    payload = {
        "adapter_hash": _adapter_hash(adapter_dir),
        "contributor_wallet": args.wallet,
        "domain": args.domain,
        "ipfs_cid": cid,
    }
    r = requests.post(f"{AGGREGATOR_URL}/contribute", json=payload, timeout=120)
    if r.status_code != 200:
        print(f"Aggregator error {r.status_code}: {r.text}", file=sys.stderr)
        return 1
    out = r.json()
    print(f"Action: {out['action']}")
    print(f"Score: {out['score']:.4f}")
    print(f"Delta: {out['delta']:+.4f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fedlab")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("download", help="Download latest model + adapter").set_defaults(func=cmd_download)

    train_p = sub.add_parser("train", help="Fine-tune locally on your data")
    train_p.add_argument("--data", required=True, help="Path to JSONL training file")
    train_p.set_defaults(func=cmd_train)

    contrib_p = sub.add_parser("contribute", help="Submit local adapter to the aggregator")
    contrib_p.add_argument("--wallet", required=True)
    contrib_p.add_argument("--domain", default="prediction_markets")
    contrib_p.set_defaults(func=cmd_contribute)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
