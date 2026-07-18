---
name: commit
description: Commit current changes with a conventional commit message
---

# commit

Commit current staged changes with a Conventional Commits message.

## Usage

```
/commit <type>(<scope>): <description>
```

## Examples

```
/commit feat(scheduler): implement chunked prefill
/commit fix(kv_cache_manager): correct LRU eviction ordering
/commit docs(TESTING_GUIDE): update mock test commands
```

## About

- `type`: feat | fix | docs | style | refactor | test | chore | perf
- `scope`: module name (scheduler, kv_cache_manager, etc.)
- `description`: concise description of the change

See `AGENTS.md` for full commit message format.

## Related

- `/pr` — Create a PR after committing
- `/branch` — Create a new branch
