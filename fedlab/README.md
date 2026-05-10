# FedLab

## What is FedLab

FedLab is an open, federated training network for small language models. Anyone can fine-tune a shared base model (Phi-3-mini) on their own hardware using their own data, then contribute a LoRA adapter back to the network. The aggregator runs a rotating, deterministic benchmark and only merges adapters that improve the model — contributors earn $FZIQ tokens proportional to the improvement they deliver.

## How it works

```
+----------+      +---------+     +-------------+      +--------------+
| Download | -->  |  Train  | --> | Contribute  | -->  |   Evaluate   |
| (IPFS)   |      | (local) |     | (LoRA only) |      | (weekly seed)|
+----------+      +---------+     +-------------+      +--------------+
                                                              |
                                                   merge / return / burn
                                                              |
                                                +-----------------------+
                                                | Trimmed-mean adapter  |
                                                |   published to IPFS   |
                                                +-----------------------+
```

Raw training data never leaves a contributor's machine. Only the LoRA adapter (a few MB) is submitted, evaluated, and merged.

## Quickstart

```bash
# Install
git clone https://github.com/k-abai/FedLab.git
cd FedLab/fedlab
pip install -r requirements.txt

# Download the latest community-trained adapter
python -m cli.fedlab download

# Train on your own JSONL data
python -m cli.fedlab train --data ./my_data.jsonl

# Contribute back
python -m cli.fedlab contribute --wallet <your-solana-address>
```

## Benchmark integrity

The benchmark uses a rotating weekly seed:

```python
week_number = int(time.time()) // (7 * 24 * 3600)
week_seed   = sha256(f"fedlab-{week_number}".encode()).hexdigest()
```

Every node — aggregator and contributors alike — derives the same seed, samples the same 200 questions from the eval pool, and computes the same Brier score. This makes scores reproducible across the network and prevents overfitting to a fixed eval set: the scoring distribution shifts every Monday at 00:00 UTC.

The full benchmark registry lives in `benchmarks/registry.json`. New domains can be added without changing the aggregator.

## Token mechanics

**Stake.** Contributors put a small amount of $FZIQ at risk when they submit an adapter. This raises the cost of spamming the aggregator with random adapters and gives the network a way to slash bad actors.

**Reward.** When an adapter clears the improvement threshold, the contributor receives $FZIQ proportional to the score delta they produced. Better adapters get larger rewards, and rewards stack with cumulative improvements over time — visible on the public leaderboard.

**Burn.** Adapters that materially degrade the model (delta below the negative threshold) cost the contributor their stake. Adapters within the noise band are returned with no penalty and no reward — neither the network nor the contributor gains from churn.

Chain: **Solana devnet** for the hackathon, **mainnet** after. Token symbol: **$FZIQ** — contract address provided separately. *This repository does not implement the on-chain token contract.*

## Architecture

```
                       +-----------------------+
                       |     Contributors      |
                       |  (RTX 3050+, local)   |
                       +-----------+-----------+
                                   |
                          LoRA adapter (IPFS)
                                   |
                                   v
+---------+         +--------------------------+         +------------+
| Frontend|<------->|       Aggregator         |<------->|    IPFS    |
| (Vercel)|  REST   |  FastAPI (Railway)       |  pin    |            |
+---------+         |  - eval (weekly seed)    |         +------------+
                    |  - trimmed-mean merge    |
                    |  - leaderboard / state   |
                    +------------+-------------+
                                 |
                          benchmarks/*
                       (registry-driven)
```

## Contributing

Pull requests are welcome. Please:
1. Open an issue describing the change first.
2. Match the existing code style — small, focused modules; no speculative abstractions.
3. Run `python -m compileall fedlab` and `npm run build` (in `frontend/`) before submitting.

Bug reports, benchmark domain proposals, and adapter-quality experiments are all in scope.

## License

MIT — see the repository root `LICENSE`.
