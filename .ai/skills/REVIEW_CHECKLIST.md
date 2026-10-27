# Third-party skill review checklist
Each item maps to a REGISTRY field. Do not set `approved_for_execution: true` until all are checked **and** the user approved.

- [ ] Specific source repository and pinned version/commit identified → `source`, `commit`
- [ ] Publisher and code provenance reviewed; not based on install count or stars alone → `source`, `notes`
- [ ] README, SKILL.md, scripts, dependencies, and lifecycle hooks inspected → `notes`
- [ ] Network, shell, filesystem, secret, credential, and external-service access assessed → `permissions`
- [ ] Hash of the reviewed SKILL.md recorded (`sha256sum`) → `sha256`
- [ ] License and compatibility checked; expected benefit outweighs context cost → `notes`
- [ ] Trigger conditions defined so it is not used on unrelated tasks → `triggers`
- [ ] User explicitly approved installing/running the exact command
- [ ] Registry updated: `review_status`, `reviewed_at`, `reviewed_by`, `review_expires` (≤ 90 days)

## Re-review when
Upstream version/commit changes, the SKILL.md hash differs, permissions change, or `review_expires` passes.
