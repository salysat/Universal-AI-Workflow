# Autopilot technical notes (V6.10, updated V6.11)

> **V6.11 change — no external assistants by default.** `external_enabled` is `false`. `environment()` now returns `self` (native subagents) or `sessions` (fresh chats) unless an operator explicitly enables the external path. `spawn` writes self-contained `SESSION-*.md` packets (≤ 450 words) plus `SPAWN.md`; `tick` regenerates them. See [SELF_SESSIONS.md](SELF_SESSIONS.md). The external-mode details below remain valid but are opt-in.

## Contract

`uw-auto` is a single entry point. The command body in `commands/registry.json` instructs the host to run `python scripts/uw_autopilot.py boot` first and then act on the returned `mode`. The host never asks the user for a plan, mode, run ID or skill choice.

`boot` output is a compact JSON object (< 2.5 KB): `run_id`, `mode`, `plan_created`, `tasks`, `done`, `current`, `current_paths`, `skills`, `budget`, `mission`, `cli`, `approvals`, `next_command` and (inhost only) `one_time_setup`. It writes `.ai/runs/<run>/MISSION.md` (≤ 450 words).

## Files

| File | Role |
|---|---|
| `scripts/uw_autopilot.py` | boot / run / tick / status / init-config. Stdlib only. |
| `scripts/uw_skill_router.py` | Local-only skill routing with SHA-256 trust checks. |
| `scripts/uw_context_guard.py` | brief / check / prompt / trim (from V6.9.1), reused by `boot`/`tick`. |
| `scripts/agent_runner.py` | `prompt_for(task, run, tid, extra='')` and `run_one(..., extra_prompt=None)` — optional extra prompt lets the autopilot inject routed skills without changing existing callers. |
| `uw-auto.config.json` | Local, gitignored config holding explicit approvals. |
| `.ai/runs/<run>/autopilot.json` | Compact per-task state (status, attempts, skills, evidence). |
| `.ai/runs/<run>/MISSION.md` | The only long-form document the host reads. |
| `.ai/runs/<run>/autopilot-report.md` | Compact final table; no logs. |

## Planning

`heuristic_plan(run, description, max_tasks)` scans top-level directories for code files (`.cs`, `.py`, `.js`, `.ts`, `.go`, `.rs`, `.sql`, …), skips hidden/generated directories, and creates one task per directory with exclusive `paths`, acceptance `['Project build passes', 'Targeted tests or checks pass', 'No edits outside the owned paths']`, plus a final `VERIFY` task depending on all of them. It is deterministic, makes no LLM call, and writes an editable `plan.md`. `workflow.validate_plan` enforces non-overlapping ownership.

If a plan already exists at `.ai/runs/<run>/plan.json`, `boot` reuses it and is idempotent.

## Modes

`environment(cfg)` calls `ai_discovery.discover()` and `agent_ready(cfg)`. External mode requires **all** of: `approve_agents`, `approve_worktrees`, a valid `agents_config`, the named agent present in it, and its executable resolvable on PATH. Detection explicitly does **not** verify authentication.

### external `run`

For each ready task (up to `max_tasks_per_run`):

1. `git worktree add -b ai/<run>/<task> .ai/worktrees/<run>-<task> HEAD`.
2. Mark the plan task `ACTIVE` with `branch`, `worktree`, `base`.
3. Call `agent_runner.run_one(..., extra_prompt=...)`. Its human one-line print is captured with `contextlib.redirect_stdout` so autopilot stdout stays valid JSON. The extra prompt contains routed local skill paths, context rules and the "no commit/install/network" constraints.
4. `run_one` enforces task ownership via `git status --porcelain`, writes full logs to `.ai/runs/<run>/agents/<task>/`, and returns `FINISHED_UNVERIFIED` / `BLOCKED` / `FAILED`.
5. Optional validation: one command from `workflow.SAFE_COMMANDS` selected by `validation_command_id`, 180 s timeout, only exit code + last 5 lines retained.
6. Optional integration (two explicit approvals): `git add -N .` in the worktree, `git diff --binary HEAD`, then `git apply --check` and `git apply` in the main tree. Conflicts are reported, never forced.
7. State becomes `FINISHED_UNVERIFIED` (agent exit 0, no ownership violations) or `BLOCKED`. `TERMINAL_OK = ('DONE', 'FINISHED_UNVERIFIED')` unblocks dependants; the report states clearly that acceptance criteria were not independently verified.
8. One short line is appended to `autopilot.log.md` (capped at 40 lines). A compact `autopilot-report.md` is written.

### inhost `tick`

Records `done` / `blocked` for one task, recomputes `uw_context_guard.check`, and returns the next task. On `over_budget` (or when no task remains) it calls `uw_context_guard.fresh_prompt` and sets `next_chat_required: true` with the path to `FRESH_PROMPT.md`.

**Hard limit:** a script cannot create independent context windows inside a single web chat session. Inhost mode therefore enforces one bounded task per chat and an explicit handoff.

## Skill routing trust model

`uw_skill_router.route(root, task, extra_skills)` scores a task's id/description/acceptance/paths against curated trigger keywords and returns at most 3 **local** files:

- Built-in `uw-*` commands: any installed platform path (`.agents/skills/<name>/SKILL.md`, `.claude/commands/<name>.md`, …). `trust: repo-owned`.
- Vendored third-party skills from `.ai/skills/REGISTRY.json`: require `approved_for_execution`, `review_status == approved`, unexpired `review_expires`, path inside root, and a matching SHA-256. `trust: pinned-sha256-reviewed`.
- Config `extra_skills`: require `approved: true`, a 64-char hash that matches, and a path inside root. `trust: config-pinned-sha256`.

All results carry `network_used: false` and `auto_install: false`. "Loading a skill" means telling the executing agent to READ a reviewed local file — never copying its body into the host context, never installing, never executing.

## Verification performed

- `python scripts/workflow.py validate` → PASS
- `python scripts/generate_commands.py --check` → 0 out-of-sync
- `python -m unittest discover -s tests -q` → 95 tests OK (10 new autopilot/router tests)
- End-to-end external smoke test with a local demo agent: 3/3 tasks, 3 separate worktrees/processes, ownership checks passed, validation exit 0, pure-JSON stdout.
- Inhost smoke test on the real repository: `boot` created config + plan + MISSION.md, `run` correctly refused external execution, `tick` advanced to the next task.

No real provider CLI was invoked; no push was performed by the tool.

## Limits

- Estimates are UTF-8 bytes/4 of file sizes, not provider billing or live context usage.
- `FINISHED_UNVERIFIED` is not DONE. Run the project gate and review every diff.
- No commit, merge, push or deploy is automatic.
- CLI detection is not authentication; each external task costs separately at the provider.
- `generate_commands.py --check` on a partial `--platforms` install reports other platforms as out-of-sync (unchanged original behaviour).
