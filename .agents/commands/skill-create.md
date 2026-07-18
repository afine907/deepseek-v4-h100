---
name: skill-create
description: Create a new skill for this repository
---

# skill-create

Create a new skill for this repository's `.agents/skills/` directory.

## Usage

```
/skill-create <skill-name> [description]
```

## About

This command delegates to the **Author** sub-skill of the DeepWorkPlan skill.

The Author sub-skill will:
1. Scaffold a new skill file in `.agents/skills/<skill-name>/`
2. Generate the skill definition (name, description, allowed tools)
3. Provide the step-by-step flow for the skill
4. Register the skill in `skills_agents_catalog.md`

## Related

- `/agent-create` — Create a new agent
- `/dwp-verify` — Verify the skill is properly registered
