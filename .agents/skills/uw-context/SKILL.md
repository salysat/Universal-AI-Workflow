---
name: uw-context
description: Context budget and fresh-session handoff
---
Follow AGENTS.md. Task partitioning splits FILE OWNERSHIP, not the context window. Use the context guard for every in-host run:

- `python scripts/uw_context_guard.py --root . brief --run RUN_ID` — the only run-state view allowed in chat.
- `python scripts/uw_context_guard.py --root . check --run RUN_ID --max-tokens 12000` — before each task/role.
- `python scripts/uw_context_guard.py --root . prompt --run RUN_ID` — writes FRESH_PROMPT.md for a NEW chat.
- `python scripts/uw_context_guard.py --root . trim --run RUN_ID --max-chars 800` — preview; add `--apply` only after review (full evidence kept in internal-auto.full.json).

If `check` prints `over_budget: true` (exit 2), STOP: hand FRESH_PROMPT.md to a new chat instead of continuing. Never read internal-auto.json, internal-auto-report.md, auto/report.json, auto_v5/report.json or any `*.log` in full. Redirect build/test output to a file; report command + exit code + counts + last 5 lines only. Keep evidence under 200 words plus a log path. One task (or one architect/developer/tester/reviewer cycle) per chat unless separate external CLI agents are launched with explicit approval. Estimates are bytes/4 approximations, not provider billing or real context usage. Never claim external agents ran or tests passed without observed evidence.

User arguments / request: $ARGUMENTS
