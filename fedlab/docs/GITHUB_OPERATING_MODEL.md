# FedLab GitHub Operating Model

How work flows through GitHub for the FedLab launch, and the hard line between what
**autonomous agents may do** (advise) and what the **human owner must do**
(implement anything sensitive). Pair this with `../agents/README.md`.

## Principles

1. **Agents advise; the owner decides and implements sensitive code.** Agents
   produce issues, plans, drafts, copy, and findings — never direct changes to
   auth, wallets, tokens, financial logic, private Bags calls, or secrets.
2. **Honest by default.** No commit or PR claims a score is measured or an
   integration is live unless it truly is.
3. **Small, reviewable changes.** Short-lived branches, focused PRs.

## Branch strategy

- `main` is **protected**: no direct pushes; changes land via PR.
- Short-lived feature branches off `main`, named `type/scope-short-desc`, e.g.
  `docs/agents-operating-model`, `backend/registry-submit-writeback`,
  `validation/tabpfn-fixture`.
- Delete branches after merge. Rebase or squash to keep history readable.
- Recommended branch protection on `main`: require PR, require the build check to
  pass, require owner approval for sensitive paths (see review gates).

## Pull request expectations

- One logical change per PR; keep diffs small.
- PR description: what changed, why, how to verify, and an explicit
  **Owner-only?** line for any sensitive surface touched.
- Link the issue(s) the PR closes.
- A lightweight PR template is recommended (`.github/pull_request_template.md`); if
  absent, include the same sections in the description by hand.

## Issue labels

Create these labels (Settings → Labels):

| Label | Use for |
|-------|---------|
| `security` | Threat-model findings, secrets, auth/permission concerns. |
| `owner-only` | Sensitive work only the human owner may implement (see below). |
| `validation` | Validation packets, leakage checks, reproducibility, evaluators. |
| `frontend` | UI copy, flows, status labels, Next.js pages/components. |
| `backend` | API endpoints, contracts, registry persistence. |
| `bags` | Bags API mapping, integration seams, env vars. |
| `growth` | Launch, outreach, community, user interviews. |
| `docs` | Documentation, handoff, operating model, READMEs. |
| `good-first-packet` | Small, well-scoped validation packet starter tasks. |

## Commit rules

- Small, logical commits with imperative messages (e.g. "Add validation packet
  fixture", not "wip").
- **No secrets, ever.** No API keys, tokens, private keys, or `.env` values.
  `.env*` is gitignored — keep it that way.
- **No generated model artifacts** beyond a small size threshold (suggest **>5 MB**
  blocked by review). Weights, adapters, datasets, and large parquet/checkpoints
  stay out of git (use the existing `.gitignore` entries; add more as needed).
- Don't commit `agents/out/` contents (advisory outputs) — only the `.gitkeep`.

## PR review gates

Every PR must pass, in order:

1. **Build / compile.** Python: `python -m compileall fedlab`. Frontend:
   `cd fedlab/frontend && npm run build`. (No CI requiring external secrets.)
2. **Security review** — required for any change touching: auth/sessions, admin
   endpoints, wallet/signature verification, Solana proof/anchoring, token or
   financial logic, Bags credential handling, or user-facing financial language.
   The Security Reviewer agent may produce findings; the **owner** signs off.
3. **Owner approval** — required to merge anything in the owner-only list.

Agents are **not authorized to approve PRs.** Approval is owner-only.

## What agents may do vs. what the owner must do

**Agents may:**
- Draft issue text, PR plans, roadmaps, and decision-log entries.
- Write docs, UI copy, outreach, application answers, demo scripts.
- Design endpoints, OpenAPI contracts, packet specs, and leakage checklists.
- Provide non-sensitive draft code as *suggestions* for the owner to review/apply.
- Produce security findings and threat models.

**Owner-only (never delegated to agents):**
1. Authentication, authorization, sessions, and admin endpoints.
2. Wallet signature verification and Solana proof verification.
3. Token mechanics, mint, transfers, and financial model logic.
4. Private Bags API calls and production secret handling.
5. Arbitrary / untrusted model execution and submission sandboxing.
6. Merging/approving PRs and configuring branch protection.

## Recommended GitHub issues to create next

Paste these as issues with the listed labels (titles are starters):

1. `docs` — "Adopt autonomous agent operating model" (link `agents/README.md`).
2. `validation` `good-first-packet` — "Add a real predictions fixture and measure
   one packet score (tabpfn or reservoir)."
3. `backend` `owner-only` — "Design `/registry/submit` validation-hash write-back"
   (design by agent; implementation owner-reviewed).
4. `bags` — "Map confirmed Bags public API paths and finalize env-var contract."
5. `security` `owner-only` — "Threat model + secrets/auth-boundary review for the
   registry API."
6. `frontend` — "Honest status-label spec for demo/candidate/verified and
   mock/live integration badges."
7. `growth` — "Draft launch sequence + Discord/X intro posts (advisory drafts)."
8. `docs` `growth` — "Draft Bags application answers and 60–90s demo script."
