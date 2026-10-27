# Skill router V4

| Request | Registry id | Permitted behavior |
|---|---|---|
| Find or explore external skills | `find-skills` | Reference/discovery only; no execution or install |

Always check `REGISTRY.json`: approval, pinned SHA-256, review date, and least-privilege permissions. Missing or failing conditions means **do not execute**. No automatic `npx skills add`.
