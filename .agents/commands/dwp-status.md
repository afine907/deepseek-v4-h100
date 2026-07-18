---
name: dwp-status
description: Check the status of a Deep Work Plan
---

# dwp-status

Show the current status of a Deep Work Plan.

## Usage

```
/dwp-status [plan-name]
```

If `plan-name` is omitted, all active plans are shown.

## About

This command delegates to the **Status** sub-skill of the DeepWorkPlan skill.

Shows:
- Overall completion percentage
- Per-task status (pending / in_progress / completed)
- Key decisions logged
- Any blockers or deferred items

## Related

- `/dwp-create` — Create a new plan
- `/dwp-execute` — Execute a plan
- `/dwp-resume` — Resume an interrupted plan
