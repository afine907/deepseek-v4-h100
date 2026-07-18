---
name: dwp-execute
description: Execute an existing Deep Work Plan
---

# dwp-execute

Execute an existing, finalized Deep Work Plan from `.dwp/plans/`.

## Usage

```
/dwp-execute [plan-name]
```

If `plan-name` is omitted, the most recent active plan is selected.

## About

This command delegates to the **Execute** sub-skill of the DeepWorkPlan skill.

The Execute sub-skill will:
1. Load the plan from `.dwp/plans/<plan-name>/`
2. Execute tasks one-by-one with validation gates
3. Update `PROGRESS.md` after each task
4. Report completion or blockers

## Related

- `/dwp-create` — Create a new plan
- `/dwp-refine` — Refine a draft plan
- `/dwp-resume` — Resume an interrupted plan
- `/dwp-status` — Check plan status
