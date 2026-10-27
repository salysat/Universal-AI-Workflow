# Change Log

Append-only, newest first. Never edit or delete older entries.
Entry format: `YYYY-MM-DD HH:MM | agent | task ID | changed paths | verification actually performed`.
When over ~50 entries or monthly, move older entries to `.ai/archive/CHANGELOG_YYYY-MM.md`.

2026-10-27 | Arena agent | UW-6.11.0 | scripts/uw_autopilot.py (self/sessions modes, spawn, session packets, external_enabled default false), tests/test_uw_autopilot.py (+6 tests), commands/registry.json (uw-auto = no external assistants, self-instantiation) + 6 generated platform files, VERSION=6.11.0, scripts/workflow.py, AGENTS.md, README*, README_GITHUB.md, START_PROMPT*, UW_AUTO_AR.md, PUBLISH_GITHUB_AR.md, INSTALL_FOR_AI_AR.md, docs/COMMANDS_AND_SKILLS*, docs/AUTOPILOT.md, V6_11_GUIDE_AR.md, docs/SELF_SESSIONS.md | Verified locally: `workflow.py validate` PASS; `generate_commands.py --check` = 0 out-of-sync; 101 tests OK. Smoke: boot -> spawn -> tick regenerates next SESSION packet; external CLI disabled even with approve_agents=true unless external_enabled=true. No external provider CLI was invoked in the new default modes.

2026-10-27 | Arena agent | UW-6.10.0 | scripts/uw_autopilot.py, scripts/uw_skill_router.py, tests/test_uw_autopilot.py, scripts/agent_runner.py (optional extra_prompt), commands/registry.json (uw-auto = one-word autopilot), generated uw-auto command files (6 platforms), scripts/install_ai.py, VERSION, scripts/workflow.py, .gitignore, AGENTS.md, README*, docs/*, V6_10_GUIDE_AR.md, UW_AUTO_AR.md | Verified locally: `workflow.py validate` PASS; `generate_commands.py --check` = 0 out-of-sync; 95 tests OK. End-to-end external-mode smoke test with a local demo agent: 3/3 tasks, separate worktrees/processes, ownership checks and validation exit 0. No real provider CLI was invoked; no commit/merge/push by the tool.

2026-10-27 | Arena agent | UW-6.9.1 | commands/registry.json, scripts/uw_context_guard.py, scripts/workflow.py, scripts/install_ai.py, scripts/generate_commands.py output (6 platforms), tests/test_uw_context_guard.py, AGENTS.md, .ai/CONTEXT_POLICY.md, README*.md, docs/*, V6_9_1_GUIDE_AR.md | Verified locally: `python scripts/workflow.py validate` PASS; `python scripts/generate_commands.py --check` = 0 out-of-sync; `python -m unittest discover -s tests -q` = 85 tests OK. No provider token measurement was available; guard estimates are bytes/4 of file sizes only. No commit/push performed by the tool.

No changes recorded.
