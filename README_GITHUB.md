# Universal AI Workflow v6.11.0

Portable workflow and same-AI role protocol for software projects and general file tasks. Includes native command templates for Claude, Cursor, Gemini, OpenCode, Copilot and skills for Codex (19 commands). Installation is local (Python standard library). Does not invoke external AI providers by default.

**New in 6.11 — no external assistants:** `uw-auto` now instantiates the SAME assistant repeatedly. `spawn` writes self-contained `SESSION-*.md` packets; `self` mode uses native subagents (one copy per packet, each with its own context), `sessions` mode uses successive fresh chats. External CLI is strictly opt-in. See [V6_11_GUIDE_AR.md](V6_11_GUIDE_AR.md) and [docs/SELF_SESSIONS.md](docs/SELF_SESSIONS.md).

**From 6.10 — just type `uw-auto`:** `scripts/uw_autopilot.py` + `scripts/uw_skill_router.py` turn `uw-auto` into a single entry point that auto-plans from the repository, routes reviewed local skills, measures the context budget and runs each task in its own CLI process/context/worktree (external mode) or hands off to a fresh chat (inhost mode). See [V6_10_GUIDE_AR.md](V6_10_GUIDE_AR.md) and [docs/AUTOPILOT.md](docs/AUTOPILOT.md).

**From 6.9.1 — hard context guard:** `uw-context` + `scripts/uw_context_guard.py` (`brief` / `check` / `prompt` / `trim`). Task partitioning splits file ownership, not the context window; the guard enforces compact state views, a stop signal on context budget overrun, and a fresh-session handoff. See [V6_9_1_GUIDE_AR.md](V6_9_1_GUIDE_AR.md).

**Read [PUBLISH_GITHUB_AR.md](PUBLISH_GITHUB_AR.md) for GitHub publishing, installing and invoking `/`, `@`, `$` commands.**

```bash
python scripts/install_ai.py --source . --target /path/to/existing/project --platforms all --dry-run
python scripts/install_ai.py --source . --target /path/to/existing/project --platforms all
```

Install only the platform you actually use (e.g. `--platforms codex`) to avoid loading 19 command files across six hosts.

Within a supported assistant call `uw-team` to work sequentially as architect, developer, tester, reviewer. Actual AI invocation depends on host support. No automatic multi-model execution.
