---
name: verify
description: Verify that a code change actually works end-to-end
allowed-tools: Bash
---

# Verify Skill

Drive the project's real runtime to verify that a change actually works.

## When to Use

- Before committing non-trivial changes
- After implementing a new feature
- When tests pass but you're unsure the feature actually works

## How to Use

1. Identify the change's primary runtime surface (the feature's main entry point)
2. Exercise it with real inputs — not just unit test inputs
3. Observe the actual output or behavior
4. Compare against expected behavior

## For This Project

| Change Type | Verification Approach |
|-------------|----------------------|
| Scheduler logic | Run `pytest tests/ -m mock -v` + review scheduling metrics |
| KV Cache LRU | Run `pytest tests/ -m mock -v` + verify evict counts |
| Metrics exporter | Run mock test + `curl http://localhost:8000/metrics` |
| Docker build | Run `docker build -t deepseek-v4-h100 .` (requires GPU) |
| Launch script | Run `bash launch_h100.sh --help` (no GPU needed for help) |

## Do NOT Verify

- Diff-only changes that touch no runtime surface
- Pure documentation changes
- Test-only changes (unit tests are the runtime surface for tests)
