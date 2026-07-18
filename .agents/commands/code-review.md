---
name: code-review
description: Run a focused code review on changed files
---

# code-review

Review changed or new code for correctness, security, and quality.

## Usage

```
/code-review [files...]
```

## About

Reviewer agent (`reviewer`) performs a focused review on provided files or current diff.

## What it checks

- Logic errors and edge cases
- Security vulnerabilities (key leakage, injection)
- Test coverage
- Adherence to `docs/STANDARDS.md`

## Related

- `/pr` — Open or update a PR
- `/commit` — Commit current changes
