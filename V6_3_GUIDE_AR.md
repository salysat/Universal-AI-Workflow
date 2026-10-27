# Universal AI Workflow V6.3 — P1 follow-up

- Agent runner: optional `prompt_transport: "stdin"`, with worktree-local prompt files ignored via local `.git/info/exclude`.
- V6 LLM sessions: support stdin; create their short-lived prompt inside the worktree, not the system-wide temp directory.
- Agent role configuration examples provided for Codex, Claude and Gemini. **Unverified examples; check installed versions and CLI help.**
- Environment allowlist retained; no arbitrary shell execution.
- Important: stdin might not be supported by all provider CLI versions; use a verified profile.
- Not delivered: project-specific hashed Gate policies, Audit Scanner integration (original PowerShell source needed), real-agent end-to-end test.
