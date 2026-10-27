---
name: uw-auto-v5
description: Auto V5
---
# uw-auto-v5
Run `python scripts/ai_discovery.py` to detect local CLI binaries. Ask for an editable plan draft with `python scripts/auto_plan.py --run RUN --description "DESCRIPTION" --output plan-draft.json`. After the user approves the draft, use `python scripts/workflow.py plan --file plan-draft.json` (confirm actual CLI syntax). Preview with `python scripts/v5_auto.py --run RUN`. Only with explicit authorization execute `python scripts/v5_auto.py --run RUN --approve-worktrees --approve-agents`. Do not auto-commit, merge, push, or deploy. Provide the detailed report from `.ai/runs/RUN/auto_v5/report.md`.
