# FedLab

**Verified AI models for real-world domains.**

FedLab is a Bags-powered **verified model registry and validation layer**. It
tracks an array of models, each tied to a standardized *validation packet* — a
held-out benchmark with leakage checks — so a model's reported score is auditable
rather than self-asserted. Verified results carry a validation hash that can be
anchored on-chain.

This is the MVP. It is deliberately bare-bones: a registry, three validation
packets, a small API, and integration seams for Bags and Solana. It is **not** a
decentralized training network today — that federated LoRA contribution loop is
preserved in this repo as a *future direction* (see "Future direction" below).

## Idea outline

1. Start with a curated registry of models, each verified by a benchmark packet.
2. Each domain has a validation packet defining dataset, metric, evaluation
   script, current best score, and leakage checks.
3. Verified models earn a validation hash → a public proof of validation that can
   be anchored on Solana.
4. Bags provides the project/token traction layer on top of the registry.

## Initial model tracks

| Track | Benchmark | Seed model | Status |
|-------|-----------|------------|--------|
| Software Engineering | **SWE-bench++** | SWE-Agent-LoRA-v0 (`18.4% pass`) | demo_verified |
| Tabular Prediction | **TabPFN validation packet** | TabPFN-FedLab-v0 (`0.91 ROC-AUC`) | candidate |
| Financial Forecasting | **Reservoir validation packet** | Reservoir-Fin-v0 (`0.037 RMSE`) | candidate |

> All three rows are **seed/demo** values. Scores are illustrative targets, not
> measured results, and are labeled as such in the registry and packets.

## MVP architecture

```
+------------------+        +-----------------------------+        +-----------------+
|  Next.js frontend|  REST  |   FastAPI aggregator/API    |  read  |  registry/      |
|  (registry,      |<------>|  /registry/* /validation-*  |<------>|  models.json    |
|   packets pages) |        |  /integrations/*            |        |  validation_    |
+------------------+        +--------------+--------------+        |  packets/*      |
                                           |                       +-----------------+
                                           |
                              +------------+------------+
                              | integrations/bags.py    |  (mock until env set)
                              | integrations/solana.py  |  (proof payload, no contract)
                              +-------------------------+
```

- **Registry** (`registry/`): `models.json` + `registry.py` helpers (load, get,
  validate, append).
- **Validation packets** (`validation_packets/`): one dir per domain, each with a
  `packet.json` and (for tabular/finance) a dependency-light `evaluate.py`.
- **API** (`aggregator/server.py`): FastAPI app, file-backed state.
- **Integrations** (`integrations/`): Bags and Solana scaffolds.

## Backend / API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/registry/models` | List registry models |
| GET | `/registry/models/{model_id}` | Get one model |
| POST | `/registry/submit` | Queue a model (returns candidate row; no validation yet) |
| GET | `/validation-packets` | List packet metadata |
| GET | `/validation-packets/{packet_id}` | Get one packet |
| GET | `/integrations/status` | Bags + Solana configuration status |
| GET | `/integrations/bags/project` | Bags project stats (mock if unconfigured) |
| GET | `/integrations/bags/token` | Bags token stats (mock if unconfigured) |

Existing federated endpoints (`/health`, `/model/latest`, `/leaderboard`,
`/contribute`) remain.

```bash
cd fedlab
pip install -r requirements.txt
uvicorn aggregator.server:app --reload
# then: curl localhost:8000/registry/models
```

## Bags API integration plan

`integrations/bags.py` reads env vars and returns live stats when configured, or
clearly-labeled mock data (`configured: false`, `mode: "mock"`) otherwise. No
private APIs are called and no credentials are invented; endpoint paths are
configurable placeholders.

| Env var | Purpose |
|---------|---------|
| `BAGS_API_BASE_URL` | Bags API base URL (placeholder default) |
| `BAGS_API_KEY` | API key/bearer token |
| `FEDLAB_BAGS_PROJECT_ID` | FedLab's Bags project id |
| `FZIQ_TOKEN_ADDRESS` | Token mint address for token stats |

## Web3 / Solana integration plan

`integrations/solana.py` provides wallet sanity checks, builds a deterministic
validation-proof payload (sha256 over the validation event), and reports on-chain
proof status as mock/not-configured. **No smart contract, no token minting, no
transfers.**

| Env var | Purpose |
|---------|---------|
| `SOLANA_RPC_URL` | RPC endpoint used to (future) verify anchored proofs |
| `FZIQ_TOKEN_ADDRESS` | Token mint address |

## What works now vs. demo/candidate

**Works now**
- Registry load/query/validate/append (`registry.py`) — tested.
- Packet metadata + two runnable, dependency-light evaluators (`tabpfn`,
  `reservoir_finance`) that emit JSON metrics from a predictions file.
- All API endpoints (file-backed).
- Integration status/mock responses for Bags and Solana.
- Frontend builds and renders registry, packets, and integration-hooks pages.

**Demo / candidate (not real results)**
- The three seed model scores (`18.4% pass`, `0.91 ROC-AUC`, `0.037 RMSE`).
- SWE-bench++ harness (container build + test execution) is a definition only.
- Live Bags stats and on-chain proof anchoring (require credentials/contracts).

## What remains for tomorrow

See `docs/HANDOFF_2026-05-29.md` for the full handoff, including suggested next
tasks and Bags submission language.

## Future direction (federated training)

The original federated LoRA contribution loop — local training, IPFS adapter
submission, trimmed-mean aggregation, weekly-seed benchmark, token rewards — lives
in `aggregator/aggregate.py`, `model/`, `cli/`, and `benchmarks/`. It is retained
as a future direction layered on top of the verified registry, not the primary
MVP story.

## License

MIT — see the repository root `LICENSE`.
