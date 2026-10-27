---
name: uw-team
description: Run same-host internal AI team roles (not external model CLIs)
---
Use the SAME current AI assistant to carry out architect, developer, tester, reviewer sequentially. If platform supports native subagents you may use them only within host permissions; don't claim parallel execution otherwise. Read AGENTS.md, INTERNAL_AI_TEAM_AR.md and .ai/STATE.md when available. If local Python execution is available, create task with `python scripts/uw_internal_team.py start TASK_ID "GOAL" --files FILES`, follow `next TASK_ID`, and record each role with real evidence. Do not invent reports or test results. `uw_internal_team.py` manages state only, it never invokes AI. If tool execution is unavailable, use the same role sequence conversationally and update available state files. No external AI CLI or network operation required. Ask before destructive operations or committing/pushing.

User request: $ARGUMENTS

Context: before and during the four roles run `python scripts/uw_context_guard.py --root . check --run RUN_ID --max-tokens 12000` and use `brief` instead of full state. On `over_budget: true`, stop and hand off to a NEW chat with `prompt`. All four roles share ONE context window; do not describe them as independent agents.
