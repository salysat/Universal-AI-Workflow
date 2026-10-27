# V4.1 Local Agent Runner / تشغيل الوكلاء المحليين

The runner does **not** download AI models, install CLIs, supply API credentials, or bypass providers' approvals. It launches an operator-configured program with an argv array (`shell=False`), in a pre-created Git worktree, and captures its stdout/stderr and changed paths. This is **not** a security sandbox; any installed CLI may have broad filesystem/network rights. Use with trusted CLIs and a disposable repository or OS sandbox for untrusted tools.

## Quick start (Windows PowerShell)

```powershell
py -3 scripts\workflow.py validate
py -3 scripts\workflow.py plan --file examples\sample-plan.json
py -3 scripts\workflow.py worktree --run demo --task api
py -3 scripts\workflow.py worktree --run demo --task ui
py -3 scripts\agent_runner.py check-config --config examples\agents.example.json
py -3 scripts\agent_runner.py run --run demo --task api --agent demo-safe --config examples\agents.example.json --approve-exec
py -3 scripts\agent_runner.py parallel --run demo --tasks api ui --agent demo-safe --config examples\agents.example.json --max-workers 2 --approve-exec
```

Change `run_id`, task paths and names before a real run. The sample `demo-safe` command only prints a message. Run it from the repository checkout (not an agent worktree). Runtime reports are stored under `.ai/runs/<run>/agents/<task>/` and ignored by Git. Do **not** commit these logs if they contain sensitive data.

## Configuring a real CLI

Copy `examples/agents.example.json` into a local ignored file such as `agents.local.json`, add its filename to `.git/info/exclude`, and define an explicit executable and argv according to your CLI's *current* documented syntax. Supported placeholders: `{worktree}`, `{prompt_file}`, `{run_id}`, `{task_id}`. The script does not assume command syntax for Codex, Claude, Gemini, OpenCode or Cursor.

Every task must be ACTIVE with a clean Git worktree created via `workflow.py worktree`. When launching multiple workers, each task uses a separate worktree. Agent runs are not auto-committed or merged. If a CLI changes anything outside its assigned `paths`, the report is `BLOCKED`; changed files remain on disk so inspect/revert them. **Detection is post-execution; it does not prevent access or edits.**

`FINISHED_UNVERIFIED` means only that the CLI exited with code zero and the changed paths detected by Git fit the ownership list. It does **not** mean acceptance tests passed. Use `workflow.py complete` only after manually reviewing and committing changes with evidence, and use your build/test gate after integration.

If executable options are unknown or a vendor CLI is not installed, use manual agent sessions in separate worktrees. The agent runner is opt-in (`--approve-exec`) and does not access cloud accounts automatically.
