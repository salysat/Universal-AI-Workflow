# Native Slash Commands & Skills — V6.11.0

This release ships **19 reusable actions** with discoverable entry points per supported host (V4.2 had 12).

| Host | Location | Invocation |
|---|---|---|
| Claude Code | `.claude/commands/uw-*.md` | `/uw-plan` |
| Cursor | `.cursor/commands/uw-*.md` | `/uw-plan` (beta; may vary by build) |
| Gemini CLI | `.gemini/commands/uw-*.toml` | `/uw-plan` then `/commands reload` |
| OpenCode | `.opencode/commands/uw-*.md` | `/uw-plan` |
| VS Code Copilot Local | `.github/prompts/uw-*.prompt.md` | `/uw-plan` |
| Codex CLI / IDE | `.agents/skills/uw-*/SKILL.md` | `$uw-plan` or `/skills` |
| ChatGPT skills (where supported) | imported SKILL.md | `@` skill selection (not via git alone) |

Commands: `uw-help`, `uw-recon`, `uw-plan`, `uw-build`, `uw-review`, `uw-test`, `uw-handoff`, `uw-resume`, `uw-status`, `uw-security`, `uw-ship`, `uw-agents`, `uw-audit`, `uw-auto`, `uw-auto-v5`, `uw-team`, `uw-v6`, `uw-init`, **`uw-context`**.

All command bodies live in `commands/registry.json`; run `python scripts/generate_commands.py` after editing it, then `python scripts/generate_commands.py --check` before publishing. Never hand-edit a single platform's copy.

## `uw-context` (V6.9.1)

Task partitioning splits file ownership, **not** the context window. `uw-context` points the host at `scripts/uw_context_guard.py`:

```bash
python scripts/uw_context_guard.py --root . brief  --run RUN
python scripts/uw_context_guard.py --root . check  --run RUN --max-tokens 12000
python scripts/uw_context_guard.py --root . prompt --run RUN
python scripts/uw_context_guard.py --root . trim   --run RUN --max-chars 800 --apply
```

`uw-auto`, `uw-team`, `uw-resume` and `AGENTS.md` now reference the same guard. See [CONTEXT_GUARD.md](CONTEXT_GUARD.md).

## `uw-auto` is the autopilot (V6.10)

Typing `uw-auto` alone now runs `scripts/uw_autopilot.py boot`: it auto-creates a safe config, auto-generates a plan from the repository layout, routes reviewed local skills (`scripts/uw_skill_router.py`), measures the context budget and writes a ≤ 450-word `MISSION.md`. In **external** mode (strictly opt-in since V6.11) each task runs in a separate CLI process/context/worktree; in **self** mode it spawns native subagent copies of itself; in **sessions** mode it uses successive fresh chats. No plan/mode/skill questions are asked. See [AUTOPILOT.md](AUTOPILOT.md) and [SELF_SESSIONS.md](SELF_SESSIONS.md).

## Project-local installation (safe by default)

From the workflow repository, for a *different* project:

```powershell
py -3 scripts\install_commands.py --target "E:\Projects\MyApp" --platforms all --dry-run
py -3 scripts\install_commands.py --target "E:\Projects\MyApp" --platforms all
```

Existing files are skipped; use `--overwrite` only after reviewing. This installer only copies command/skill files. To install the full runtime including `uw_context_guard.py`, use `scripts/install_ai.py` instead. Avoid overwriting the target's existing `AGENTS.md`.

Install only the platform you use (`--platforms codex`) to avoid injecting 19 command definitions across six hosts.

For personal/global installation, use the host's documented global commands/skills location; this tool deliberately installs project-local only. There is no one universal `/` command API, and not every ChatGPT interface supports repo-local discovery.

## Safety/limits

- Command files are **prompts**, not an automatic scheduler/agent runner.
- Running multiple agents requires the existing worktree + agent CLI orchestration tools and real host access.
- Do not run unknown code, dependencies, deploys, commits or pushes without approval.
- Built-in commands take precedence or clash in some clients; the `uw-` prefix avoids common collisions.
- All integrations here are file-format validated, **not** tested inside installed client applications.
- `uw_context_guard.py` estimates file sizes as UTF-8 bytes/4. That is not provider billing or live context usage.
