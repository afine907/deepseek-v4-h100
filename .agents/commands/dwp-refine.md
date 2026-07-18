---
name: dwp-refine
description: Refine a draft Deep Work Plan
---

# dwp-refine

Refine and finalize a draft Deep Work Plan before execution.

## Usage

```
/dwp-refine <draft-name>
```

## About

This command delegates to the **Refine** sub-skill of the DeepWorkPlan skill.

The Refine sub-skill will:
1. Load the draft from `.dwp/drafts/<draft-name>.md`
2. Review task structure, acceptance criteria, and validation gates
3. Allow you to modify, reorder, split, or merge tasks
4. Finalize the draft into `.dwp/plans/<plan-name>/` for execution

## Related

- `/dwp-create` — Create a new plan draft
- `/dwp-execute` — Execute a finalized plan
- `/dwp-resume` — Resume an interrupted plan
- `/dwp-status` — Check plan status
