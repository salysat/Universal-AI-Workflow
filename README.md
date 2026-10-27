# Universal AI Workflow V6.11.0

Portable Python/Git workflow for coordinating AI coding assistants. **Python 3.10+** and **Git** required. The core does not bundle any models, does not guarantee automated successful repairs, and does not deploy or push without operator action.

## What works

- Git worktrees, task ownership and dependency handling
- Explicitly approved validation gates, with optional project-specific pinned policy
- Local agent runner and multi-role orchestration when an AI CLI is installed and authenticated
- V6 experimental LLM planning, repair, separate review, and local dashboard
- Usage/cost reporting **only when providers return supported usage information**

## Quick start

```powershell
git clone https://github.com/salysat/Universal-AI-Workflow.git
cd Universal-AI-Workflow
python scripts/workflow.py validate
python -m unittest discover -s tests -v
python scripts/ai_discovery.py --json
```

## Project-specific test command policy

Supply an operator-reviewed JSON file with `commands` mapping IDs to exact executable argument arrays. The invoking operator must **separately provide its SHA-256** using `--policy-sha256` with `--policy`. The gate still requires `--allow-exec` and committed task-owned changes. This is a tamper check, **not a sandbox**.

```powershell
python scripts/workflow.py gate --run demo --task api --commands examples/validation-commands.json --allow-exec --policy policy.json --policy-sha256 THE_REVIEWED_SHA256
```

## Documentation

- [V6 guide (Arabic)](V6_GUIDE_AR.md)
- [V6.3 agent guide](V6_3_GUIDE_AR.md)
- [AI installation](INSTALL_FOR_AI_AR.md)
- [Operations](docs/OPERATIONS.md)
- [Security](SECURITY.md)

Internal `.ai/schema.json` protocol remains at 4.0 for backward compatibility; application version is tracked separately in `VERSION`.

## V6.11: no external assistants — the same assistant instantiates itself

The default no longer uses any external CLI. `uw-auto` now creates **multiple fresh instances of the same assistant**:

- `mode: self` — when the host supports native subagents, `python scripts/uw_autopilot.py spawn --run RUN` writes one self-contained `SESSION-*.md` per ready task. The orchestrator spawns one copy of itself per file (up to `parallel_sessions`), gives each copy only that file (never the parent history), and collects ≤ 10 lines back. Each copy has its own context → no token exhaustion.
- `mode: sessions` — without subagent support, each SESSION file is pasted into a NEW chat. `tick` automatically generates the next SESSION file. Typing `uw-auto` in each new chat auto-selects the next session with no questions.

External CLI mode is now strictly opt-in (`external_enabled: true` **plus** `approve_agents`, `approve_worktrees` and a configured CLI). It is never the default and never triggered by just typing `uw-auto`.

Session packets are ≤ 450 words and self-contained: task, owned paths, acceptance, routed local skills, what never to read, and the exact `tick` command. See [V6_11_GUIDE_AR.md](V6_11_GUIDE_AR.md) and [docs/SELF_SESSIONS.md](docs/SELF_SESSIONS.md).

**Honest limit:** if a platform supports neither native subagents nor new chats, independent contexts cannot be created by any script; the tool says so instead of pretending.

## V6.10: one-word autopilot — just type `uw-auto`

`uw-auto` is now the single entry point. It does **not** ask you to choose a plan, a mode, a run ID or a skill:

```bash
python scripts/uw_autopilot.py boot          # what the $uw-auto prompt runs first
python scripts/uw_autopilot.py run            # external mode only
python scripts/uw_autopilot.py tick --run RUN --task T01 --evidence "..."   # inhost mode
```

`boot` auto-creates `uw-auto.config.json` (safe defaults), auto-generates a plan from the repository layout when none is registered, routes reviewed **local** skills for each task, measures the context budget, and writes a ≤ 450-word `.ai/runs/RUN/MISSION.md`. The host assistant reads only a compact JSON + MISSION.md.

Two auto-detected modes:

- **external** — an authenticated AI CLI is configured and explicitly approved. Each task runs in its **own process, context window and git worktree**; the host chat sees only a one-line summary. This is the real one-word automation and it is what actually stops token exhaustion. Verified end-to-end with a local demo agent: 3/3 tasks, separate worktrees, ownership checks, validation command, compact report.
- **inhost** — no external CLI. The host does ONE bounded task per chat, then `tick` writes `FRESH_PROMPT.md` and asks for a new chat when the budget is exceeded. No script can make a single web chat spawn independent contexts; that is a platform limit.

Skills are **local-only**: built-in `uw-*` instruction files plus third-party files that are vendored, SHA-256-pinned, reviewed, unexpired and explicitly approved. No download, no install, no `npx skills add`. See [V6_10_GUIDE_AR.md](V6_10_GUIDE_AR.md) and [docs/AUTOPILOT.md](docs/AUTOPILOT.md).

One-time setup for unattended mode: set `approve_agents`, `approve_worktrees` and `agents_config` in `uw-auto.config.json` (gitignored). Until then it works in inhost mode. CLI detection is not authentication.

`FINISHED_UNVERIFIED` means the agent exited 0 with no ownership violations — acceptance criteria are **not** independently verified. Nothing is committed, merged, pushed or deployed.

## V6.9.1: hard context guard (fixes token exhaustion)

Splitting a plan into tasks splits **file ownership**, not the **context window**. In preview and in-host modes no external AI process is launched, so all tasks, the four roles, reports and test logs accumulate in ONE conversation. V6.9.1 adds `scripts/uw_context_guard.py` and a new `uw-context` command (all six platforms):

```bash
python scripts/uw_context_guard.py --root . check --run RUN --max-tokens 12000
python scripts/uw_context_guard.py --root . brief --run RUN
python scripts/uw_context_guard.py --root . prompt --run RUN
python scripts/uw_context_guard.py --root . trim --run RUN --max-chars 800 --apply
```

`brief` replaces printing full run state (measured on a 12-task run: 839 bytes vs 47,497 bytes). `check` returns exit 2 with `over_budget: true` when the estimated file context exceeds the budget — that means **stop and hand off**. `prompt` writes `.ai/runs/RUN/FRESH_PROMPT.md` (≤ 450 words) to start a NEW chat. `trim` shortens stored evidence while preserving a full copy.

`uw-auto`, `uw-team`, `uw-resume`, `AGENTS.md`, `.ai/CONTEXT_POLICY.md` and the always-on host rules now enforce this. Arabic guide: [V6_9_1_GUIDE_AR.md](V6_9_1_GUIDE_AR.md); technical notes: [docs/CONTEXT_GUARD.md](docs/CONTEXT_GUARD.md).

Estimates are UTF-8 bytes/4 of file sizes, **not** provider billing or live context usage. No tool can increase a provider quota. Real context isolation requires either a fresh chat per task or genuinely separate external CLI agents (which cost separately).

## Known limitations

Real Claude/Codex/Gemini execution requires local authenticated CLIs and provider-specific configuration. A separate reviewer can still share underlying model biases. The dashboard is local-only, not a hardened multiuser service. The Audit Scanner is not bundled, and no scanner results are claimed.

## V6.5 additional capabilities

- `python scripts/uw_audit.py --input report.json --run audit01 --output audit-plan.json` imports SARIF or JSON as an editable draft. External PowerShell scanner script is **not bundled**.
- `python scripts/generate_commands.py --check` verifies synchronized assistant entrypoints from `commands/registry.json`.
- AI CLIs and GitHub Actions must be run with operator credentials; no provider tests are claimed.

See [V6.5 guide](V6_5_GUIDE_AR.md).

## V6.9: internal AI orchestration (no external AI process)

`uw_internal_auto.py` enforces task dependencies and sequential Architect → Developer → Tester → Reviewer checkpoints. The host assistant performs the actual work; recording a stage is not proof that code or tests ran. Reviewer approval is required for completed state.

```bash
python scripts/workflow.py plan examples/sample-plan.json
python scripts/uw_internal_auto.py --run demo init
python scripts/uw_internal_auto.py --run demo next
# The host assistant does the work, then records accurate, concrete evidence.
python scripts/uw_internal_auto.py --run demo record api architect --evidence "Reviewed requirements and relevant files"
python scripts/uw_internal_auto.py --run demo report
```

Plan tasks may include `depends_on` arrays of task IDs. A dependency must be COMPLETED before a task becomes ready. Existing runs are not reset by `init`. Detailed Arabic guide: `V6_9_GUIDE_AR.md`.
