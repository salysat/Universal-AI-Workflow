# Operator guide

## Run lifecycle
`plan` validates unique task IDs, paths, and ownership overlap; writes `.ai/runs/<run>/plan.json`. `worktree` creates a branch/worktree for each task inside sibling directory `<repo>-agent-worktrees`; `complete` records operator-supplied evidence and resulting head; `gate` runs a reviewed JSON argv allowlist and stores exit codes; `integrate --approve` merges completed task heads with manual approval. Re-test after integration. Never claim VERIFIED solely because someone typed an evidence string.

**Important**: `plan` and `worktree` require a Git checkout for isolation; tasks must be nonoverlapping. A finished run does not grant permission to push or deploy. The integrator refuses dirty working trees and ongoing unresolved Git conflicts. Always check exact HEAD and branch before running integration.

## CLI
```text
python scripts/workflow.py validate
python scripts/workflow.py init --project NAME
python scripts/workflow.py plan --file examples/sample-plan.json
python scripts/workflow.py status [--run demo]
python scripts/workflow.py worktree --run demo --task api
python scripts/workflow.py complete --run demo --task api --evidence "tests passed" 
python scripts/workflow.py gate --run demo --commands examples/validation-commands.json --allow-exec
python scripts/workflow.py integrate --run demo --approve
```

The included `validation-commands.json` is a safe example showing Python `--version`. In real projects, set explicit `argv` arrays (`["dotnet","test"]`, for example); no shell interpolation. Build and gate results are not proof of all correctness.

## Running real AI tools
Open each returned worktree path in separate sessions of your preferred AI assistant with its existing CLI/login. Tell each assistant to work *only* on owned paths and obey `AGENTS.md`. This program does not spawn or authenticate agent models. Tasks touching common build metadata can still conflict semantically; serialize them.

## Constraints
Supported: Python 3.10+, Git 2.35+ recommended, Windows/macOS/Linux. No third-party Python packages. No multi-host coordination. Ownership is optimistic and local; no OS sandbox. Worktree locations must be kept private until reviewed.
