---
name: dwp-create
description: Create a new Deep Work Plan
---

# dwp-create

Create a new Deep Work Plan for this repository.

## Usage

```
/dwp-create <plan-name> [description]
```

## About

This command delegates to the **Create** sub-skill of the DeepWorkPlan skill installed in this repository.

The Create sub-skill will:
1. Analyze the current task and context
2. Generate a structured Deep Work Plan draft in `.dwp/drafts/`
3. Guide you through refine and finalize steps

## Related

- `/dwp-execute` — Execute an existing plan
- `/dwp-refine` — Refine a draft plan
- `/dwp-resume` — Resume an interrupted plan
- `/dwp-status` — Check plan status
- `/dwp-verify` — Verify repository AI-first conformance
