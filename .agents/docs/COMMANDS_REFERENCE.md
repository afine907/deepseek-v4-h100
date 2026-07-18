# Commands Reference

## DeepWorkPlan Commands

| Command | Description |
|---------|-------------|
| `/dwp-create <name>` | Create a new Deep Work Plan |
| `/dwp-execute [name]` | Execute an existing plan |
| `/dwp-refine <draft>` | Refine and finalize a draft |
| `/dwp-resume [plan]` | Resume an interrupted plan |
| `/dwp-status [plan]` | Check plan status |
| `/dwp-verify` | Verify AI-first conformance |

## Development Commands

| Command | Description |
|---------|-------------|
| `/commit <type>(<scope>): <desc>` | Commit with conventional message |
| `/branch <name>` | Create and switch to a new branch |
| `/pr [title] [body]` | Create or update a Pull Request |
| `/code-review [files...]` | Run focused code review |

## Skill & Agent Commands

| Command | Description |
|---------|-------------|
| `/skill-create <name> [desc]` | Create a new skill |
| `/agent-create <name> [role]` | Create a new agent |

## Git Commands (Native)

```bash
# Stage and commit
git add <files>
git commit -m "feat(scheduler): description"

# Create branch
git checkout -b feature/xxx

# Push
git push origin feature/xxx
```

## Test Commands (Native)

```bash
pytest tests/ -m mock -v        # Mock tests (no GPU)
pytest tests/unit/ -v            # Unit tests
pytest tests/ --cov=src -v      # With coverage
```

## Docker Commands (Native)

```bash
docker build -t deepseek-v4-h100 .   # Build image
bash launch_h100.sh --help           # View launch options
```
