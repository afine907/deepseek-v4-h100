---
name: agent-create
description: Create a new agent for this repository
---

# agent-create

Create a new agent for this repository's `.agents/agents/` directory.

## Usage

```
/agent-create <agent-name> [role-description]
```

## About

This command delegates to the **Author** sub-skill of the DeepWorkPlan skill.

The Author sub-skill will:
1. Scaffold a new agent file in `.agents/agents/<agent-name>.md`
2. Define the agent's persona, responsibilities, and focus areas
3. Provide usage instructions
4. Register the agent in `skills_agents_catalog.md`

## Related

- `/skill-create` — Create a new skill
- `/dwp-verify` — Verify the agent is properly registered
