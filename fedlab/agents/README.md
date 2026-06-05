# FedLab Autonomous Agent Operating Model

This directory defines a set of **advisory** autonomous agent roles used to drive
the FedLab Bags-backed launch. Agents run locally against [Ollama](https://ollama.com)
and produce **suggestions, plans, drafts, and findings** — never direct changes to
sensitive code or infrastructure.

The single guiding rule: **agents advise, the human owner decides and implements
anything sensitive.** Agents are a force multiplier for design, copy, research, and
review, not an autopilot for security, wallets, tokens, or money.

## What this is

- A library of role prompts (`prompts/`) — one per role, each with a strict
  mission, allowed inputs, expected outputs, forbidden actions, escalation rules,
  and a GitHub interaction model.
- A machine-readable role manifest (`roles.yaml`).
- An optional, advisory-only runner (`run_agent.py`) that calls the local Ollama
  API with a chosen role prompt + a task, and writes the result to `out/`.

## What this is NOT

Agents in this model **cannot and must not**:

- Implement authentication, authorization, or admin endpoints.
- Implement or verify wallet signatures / Solana proofs.
- Write smart contracts, mint tokens, or build token/financial mechanics.
- Call private Bags APIs or handle production secrets.
- Execute untrusted model code or load untrusted model weights.
- Commit, push, open PRs, or modify the repository directly.
- Make any on-chain transaction.

All of the above are **owner-only** tasks. Agents may *draft a plan or issue text*
for them, clearly labeled as requiring owner implementation and review.

## Roles

| Role | File | One-liner |
|------|------|-----------|
| CTO Architect | `prompts/cto_architect.md` | Scope control, decision log, ruthless feature cuts. |
| Security Reviewer | `prompts/security_reviewer.md` | Threat model + findings; never implements auth/crypto. |
| Backend API | `prompts/backend_api.md` | Endpoint + OpenAPI design, registry persistence plan. |
| Validation Engineer | `prompts/validation_engineer.md` | Packet design, leakage/reproducibility; no untrusted code. |
| Frontend Product | `prompts/frontend_product.md` | UI copy, submit-flow wireframes, honest status labels. |
| Growth Operator | `prompts/growth_operator.md` | Launch plan, Discord/X/GitHub outreach, interview scripts. |
| Bags/Web3 Researcher | `prompts/bags_web3_researcher.md` | Maps Bags/Solana docs + env vars; no contracts or txns. |
| Fundraising / Applications | `prompts/fundraising_applications.md` | Bags application answers, traction narrative, demo script. |

## Local Ollama setup

```bash
# 1. Install Ollama (https://ollama.com) and start the daemon.
ollama serve            # usually already running as a service

# 2. Pull a capable local model. Any of these work; pick by your hardware:
ollama pull llama3.1:8b         # lighter
ollama pull qwen2.5:14b         # stronger reasoning, more RAM
ollama pull deepseek-r1:14b     # reasoning-heavy tasks (architect/security)

# 3. Confirm it responds.
ollama run llama3.1:8b "Say hello in one sentence."
```

The runner talks to the default Ollama endpoint at `http://localhost:11434`.
Override with `OLLAMA_HOST` if your daemon is elsewhere.

## Running an agent (advisory only)

`run_agent.py` is intentionally minimal and **read-only with respect to the repo**.
It only: reads a role prompt + your task text, calls Ollama, and writes the model
output to `agents/out/`. It does **not** run shell commands, edit repo files, or
touch git/GitHub.

```bash
cd fedlab

# Task from a string:
python agents/run_agent.py --role cto_architect \
  --task "Cut FedLab's scope to what we can demo for Bags in 3 days."

# Task from a file (e.g. paste in current handoff or an issue body):
python agents/run_agent.py --role security_reviewer \
  --task-file ../some_notes.md \
  --model qwen2.5:14b

# Output is written to agents/out/<role>-<timestamp>.md and printed to stdout.
```

Flags:

- `--role` — required; one of the role ids in `roles.yaml`.
- `--task` / `--task-file` — the task text (one required).
- `--model` — Ollama model tag (default `llama3.1:8b`, or `OLLAMA_MODEL` env).
- `--context-file` — optional extra file to include as read-only context
  (e.g. the handoff doc). Repeatable.
- `--out-dir` — defaults to `agents/out/`.

Every run prepends a hard guardrail block to the role prompt restating the
forbidden actions, so even a misconfigured model is steered toward advisory output.

## Owner-only handoff (never delegated)

These are flagged throughout the prompts and must be done by the human owner:

1. Auth / session / admin endpoints.
2. Wallet signature verification and Solana proof verification.
3. Token mechanics, mint, transfers, financial model logic.
4. Private Bags API calls and production secret handling.
5. Arbitrary / untrusted model execution.

See `../docs/GITHUB_OPERATING_MODEL.md` for the branch/PR/issue workflow that wraps
all of this.
