# .agents — AI Agent Configuration

This directory contains AI agent configurations, skills, and commands for this repository.

## Quick Start

1. Read [AGENTS.md](../AGENTS.md) for the project index and mandatory rules
2. Pick an agent from [docs/skills_agents_catalog.md](docs/skills_agents_catalog.md)
3. Use commands like `/dwp-create`, `/dwp-execute`, `/commit`, `/code-review`

## Structure

```
.agents/
├── agents/         # Agent personas (reviewer, architect, executor, etc.)
├── commands/       # Slash commands (dwp-*, commit, pr, etc.)
├── skills/         # Skill definitions (deepworkplan, test-harness, verify)
├── docs/           # Catalogs and references
│   ├── skills_agents_catalog.md
│   └── COMMANDS_REFERENCE.md
└── settings.json   # Claude Code harness configuration
```

## Resources

- [DeepWorkPlan Skill](skills/deepworkplan.md) — structured multi-task plans
- [Test Harness Skill](skills/test-harness.md) — run pytest
- [Verify Skill](skills/verify.md) — end-to-end verification
- [Commands Reference](docs/COMMANDS_REFERENCE.md) — all available commands
