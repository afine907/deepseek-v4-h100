---
name: dwp-resume
description: Resume an interrupted Deep Work Plan
---

# dwp-resume

Resume an interrupted Deep Work Plan from where it left off.

## Usage

```
/dwp-resume [plan-name]
```

If `plan-name` is omitted, the most recently interrupted plan is selected.

## About

This command delegates to the **Resume** sub-skill of the DeepWorkPlan skill.

The Resume sub-skill will:
1. Read `PROGRESS.md` to find the first incomplete task
2. Restore context from task files and previous outputs
3. Continue execution from that point
4. Update `PROGRESS.md` as tasks complete

## Related

- `/dwp-create` — Create a new plan
- `/dwp-execute` — Execute a plan from the start
- `/dwp-refine` — Refine a draft
- `/dwp-status` — Check plan status
