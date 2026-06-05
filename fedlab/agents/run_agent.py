#!/usr/bin/env python3
"""Advisory-only FedLab agent runner.

Calls a LOCAL Ollama instance with a selected role prompt and a task, then writes
the model's response to `agents/out/`. That is the entire scope.

This tool is deliberately constrained. It does NOT, and must not be extended to:

  - modify, stage, commit, or push any repository file,
  - run shell commands or arbitrary code,
  - call GitHub or any remote service other than the local Ollama daemon,
  - read or emit secrets.

It only reads role-prompt / context files you point it at and writes one Markdown
output file. Every run prepends a hard guardrail block restating the forbidden
actions so the model is steered toward advisory output.

Usage:
    python agents/run_agent.py --role cto_architect --task "Cut scope for Bags demo."
    python agents/run_agent.py --role security_reviewer --task-file notes.md \
        --context-file docs/HANDOFF_2026-05-29.md --model qwen2.5:14b
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent
ROLES_FILE = AGENTS_DIR / "roles.yaml"
DEFAULT_OUT_DIR = AGENTS_DIR / "out"
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

# Restated on every run, regardless of role-prompt content.
HARD_GUARDRAILS = """\
[HARD GUARDRAILS — ALWAYS APPLY]
You are an ADVISORY agent. Produce suggestions, plans, drafts, and findings only.
You MUST NOT:
  - implement authentication, authorization, or admin endpoints;
  - implement or verify wallet signatures or Solana proofs;
  - write smart contracts, mint tokens, or build token/financial mechanics;
  - call private Bags APIs or handle production secrets/keys;
  - execute untrusted code or load untrusted model weights;
  - commit, push, open PRs, or modify any repository directly.
For any sensitive task, output a clearly-labeled OWNER-ONLY plan instead of code.
If a task crosses a forbidden boundary, ESCALATE to the human owner and stop.
[END HARD GUARDRAILS]
"""


def _load_roles() -> dict[str, dict]:
    """Map role id -> {name, prompt, summary} from roles.yaml.

    Uses PyYAML if available; otherwise falls back to a small regex parse of the
    `roles:` list (the only structure this tool needs). Kept dependency-light on
    purpose so the runner works in a bare Python environment.
    """
    text = ROLES_FILE.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        roles = {}
        for entry in data.get("roles", []):
            if "id" in entry and "prompt" in entry:
                roles[entry["id"]] = {
                    "name": entry.get("name", entry["id"]),
                    "prompt": entry["prompt"],
                    "summary": entry.get("summary", ""),
                }
        if roles:
            return roles
    except Exception:
        pass

    # Fallback: scan list items for id/prompt/name pairs.
    roles = {}
    blocks = re.split(r"\n\s*-\s+id:\s*", text)
    for block in blocks[1:]:
        rid = block.splitlines()[0].strip()
        m_prompt = re.search(r"\n\s*prompt:\s*(\S+)", block)
        m_name = re.search(r"\n\s*name:\s*(.+)", block)
        m_sum = re.search(r"\n\s*summary:\s*(.+)", block)
        if rid and m_prompt:
            roles[rid] = {
                "name": m_name.group(1).strip() if m_name else rid,
                "prompt": m_prompt.group(1).strip(),
                "summary": m_sum.group(1).strip() if m_sum else "",
            }
    return roles


def _read_file_safe(path: Path) -> str:
    if not path.exists():
        sys.exit(f"error: file not found: {path}")
    return path.read_text(encoding="utf-8")


def _call_ollama(model: str, system: str, user: str) -> str:
    """POST to the local Ollama /api/chat endpoint. Local daemon only."""
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        sys.exit(
            f"error: could not reach Ollama at {OLLAMA_HOST} ({exc}).\n"
            "Is the daemon running? Try: ollama serve / ollama pull <model>."
        )
    return (body.get("message") or {}).get("content", "").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Advisory-only FedLab agent runner (local Ollama). "
        "Writes suggestions to agents/out/. Never modifies the repo."
    )
    parser.add_argument("--role", required=True, help="Role id from roles.yaml.")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--task", help="Task text.")
    g.add_argument("--task-file", help="Path to a file containing the task text.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model tag.")
    parser.add_argument(
        "--context-file",
        action="append",
        default=[],
        help="Optional read-only context file (repeatable).",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the prompt without calling Ollama.",
    )
    args = parser.parse_args(argv)

    roles = _load_roles()
    if args.role not in roles:
        sys.exit(
            f"error: unknown role '{args.role}'. "
            f"Known roles: {', '.join(sorted(roles))}"
        )

    role = roles[args.role]
    prompt_path = (AGENTS_DIR / role["prompt"]).resolve()
    role_prompt = _read_file_safe(prompt_path)

    task = args.task if args.task is not None else _read_file_safe(Path(args.task_file))

    context_blocks = []
    for cf in args.context_file:
        p = Path(cf)
        context_blocks.append(f"### Context file: {p.name}\n\n{_read_file_safe(p)}")
    context = "\n\n".join(context_blocks)

    system_prompt = f"{HARD_GUARDRAILS}\n\n{role_prompt}"
    user_prompt = task if not context else f"{context}\n\n---\n\n## Task\n\n{task}"

    if args.dry_run:
        print("=== SYSTEM ===\n" + system_prompt)
        print("\n=== USER ===\n" + user_prompt)
        return 0

    print(f"[run_agent] role={args.role} model={args.model} host={OLLAMA_HOST}")
    output = _call_ollama(args.model, system_prompt, user_prompt)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    out_path = out_dir / f"{args.role}-{ts}.md"
    header = (
        f"# {role['name']} — advisory output\n\n"
        f"- role: `{args.role}`\n- model: `{args.model}`\n- generated: {ts}\n\n"
        "> Advisory only. Review before acting. Sensitive items are owner-only.\n\n---\n\n"
    )
    out_path.write_text(header + output + "\n", encoding="utf-8")

    print(f"[run_agent] wrote {out_path}")
    print("\n" + output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
