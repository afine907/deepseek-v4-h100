---
name: dwp-verify
description: Verify repository AI-first conformance
---

# dwp-verify

Verify that this repository is fully AI-first conformant.

## Usage

```
/dwp-verify
```

## About

This command delegates to the **Verify** sub-skill of the DeepWorkPlan skill.

The Verify sub-skill checks:
- `AGENTS.md` exists with real, runnable commands
- `CLAUDE.md` resolves to `AGENTS.md`
- `docs/` has all standard categories (PRODUCT_SPEC, ARCHITECTURE, etc.)
- All major source modules have `README.md`
- `.agents/` has agents, commands, skills, docs, settings.json
- `.claude → .agents` symlink exists
- DeepWorkPlan skill is discoverable
- `.dwp/` exists and is gitignored
- `tmp/` exists and is gitignored

Returns: **CONFORMANT** or **NOT CONFORMANT** with a detailed checklist.

## Related

- `/dwp-create` — Create a new plan
- `/dwp-execute` — Execute a plan
