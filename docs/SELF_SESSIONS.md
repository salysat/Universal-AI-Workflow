# Self-instantiation / session packets (V6.11)

## Requirement

The user does not want external assistants. They want the **same assistant instantiated more than once**, each instance with a fresh context, so a long migration does not exhaust one conversation's tokens.

## Design

`external_enabled` defaults to `False`. `environment(cfg)` now returns one of:

| Mode | When | Mechanism |
|---|---|---|
| `self` | `host_subagents: true` (or `mode_override: self`) | Host-native subagents. `spawn` writes N self-contained `SESSION-*.md` packets; the orchestrator creates one copy of itself per packet, passes only that packet, and receives ≤ 10 lines back. |
| `sessions` | default when no subagent support | One NEW chat per packet. `tick` regenerates the next packet automatically. Typing `uw-auto` in each new chat selects the next session. |
| `external` | only if `external_enabled` **and** `approve_agents` **and** `approve_worktrees` **and** a configured executable | Legacy CLI/worktree path from V6.10. Never the default; never implied by typing `uw-auto`. |

`mode_override` accepts `'' | 'self' | 'sessions' | 'external'` for testing. `parallel_sessions` is 1–8.

## Files produced

```
.ai/runs/<run>/
├── plan.json / plan.md          auto-generated ownership plan
├── autopilot.json               compact per-task state
├── MISSION.md                   ≤ 450 words for the orchestrator
├── SPAWN.md                     how to instantiate copies of yourself
└── sessions/
    ├── SESSION-01-T01.md        self-contained prompt for a fresh instance
    ├── SESSION-02-T02.md
    └── ...
```

`session_packet(run, task, rec, index)` writes a ≤ 450-word Arabic/English prompt containing: task id, role, goal, owned `paths`, acceptance criteria, routed local skill paths, an explicit read-list and do-not-read-list, the exact `tick` command, an instruction to STOP after one task, and prohibitions (no external CLI, no skill install, no commit/push, no invented tests). It raises if the packet exceeds 450 words.

`spawn_packets(run, cfg, plan, state, env)` selects ready tasks with `ready_all()` — dependencies satisfied, status not terminal — up to `parallel_sessions` in `self` mode, 1 in `sessions` mode. `spawn(cfg, run)` returns compact JSON: mode, session list, `SPAWN.md` path, budget, instruction, `tick` template and next-wave command.

`tick` now regenerates the session packets after every completion, so the next fresh instance always has a current packet. It returns `sessions`, `spawn_file`, `spawn_again`, and `next_chat_required` (true for `sessions` mode whenever another task exists, and on budget overrun).

## Why this fixes the token problem

Every instance starts with only its ≤ 450-word packet plus 1–10 source files. There is no accumulation of prior roles, reports, evidence or test logs in one window. The orchestrator sees only the compact `boot`/`spawn` JSON and ≤ 10 lines per returned copy.

## Honest platform limit

A repository script cannot open chat sessions inside a web UI or force a host to expose a subagent API. If the platform supports native subagents → `self` works. If it allows new chats → `sessions` works (one click per chat). If neither exists, independent contexts are impossible; the tool reports that rather than pretending. This is a platform constraint, not a missing setting.

## Security

- No external CLI/API/network calls in `self` or `sessions` mode.
- Skills: local files only; third-party skills require pinned SHA-256, valid review, unexpired date and explicit approval (`uw_skill_router.py`).
- No commit, merge, push or deploy.
- `uw-auto.config.json`, `agents.local.json`, `validation.local.json`, `.ai/runs/` and `.ai/worktrees/` are gitignored.

## Verification

- `workflow.py validate` → PASS
- `generate_commands.py --check` → 0 out-of-sync
- 101 unit tests OK (6 new tests: self-mode packets, spawn compactness, external disabled by default, mode override, tick regeneration, oversized packet rejection)
- Manual smoke: `boot` → `spawn` → `tick` → next packet generated; pure JSON stdout.
