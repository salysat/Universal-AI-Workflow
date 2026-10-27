# Context selection policy

1. Read `.ai/HANDOFF.md` (target: <= 500 words). In Full mode also `.ai/STATE.md` (<= 700 words).
2. Run the staleness check (see `AI_INSTRUCTIONS.md`). Stale records → verify against sources first.
3. In Full mode read current `.ai/TASKS.md`, relevant decision entries, and `.ai/MANIFEST.md`.
4. Use filenames and search to identify 1–10 likely relevant sources; inspect those, widening only if evidence requires.
5. Avoid pasting large generated files in chat. Use diffs/artifacts; summarize lengthy tool output.
6. A summary does not replace verifying relevant original sources.
7. Never assert numerical token savings without measurement; provider usage limits are independent.
8. When crossing assistants, carry files plus handoff, tool/permissions assumptions, and outstanding validation. Use Full mode.
9. Do not read `.ai/archive/` unless investigating history.
10. For run-based work, use `scripts/uw_context_guard.py brief` instead of full run state, run `check` before each task/role, and on `over_budget` stop and hand off to a NEW chat via `prompt`. One task (or one 4-role cycle) per chat unless genuinely separate external CLI agents are launched. Task partitioning is file-ownership partitioning, not context partitioning.
