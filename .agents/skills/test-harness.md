---
name: test-harness
description: Run the project's test suite with pytest
allowed-tools: Bash
---

# Test Harness Skill

Run the project's test suite and report results.

## Commands

### Mock Tests (no GPU)

```
pytest tests/ -m mock -v
```

### Unit Tests

```
pytest tests/unit/ -v
```

### All Tests

```
pytest tests/ -v
```

### With Coverage

```
pytest tests/ --cov=src --cov-report=term-missing
```

## About

- **pytest** with **pytest-mock** for mocking vLLM calls
- **prometheus-client** for metrics testing
- `-m mock` marker: runs tests with MockInferenceEngine (no GPU needed)
- `-m unit` marker: runs unit tests only
- `-m integration` marker: requires GPU/vLLM instance

## No GPU Mode

When developing without GPU access, all vLLM calls are replaced by `MockInferenceEngine`
which simulates 100-2000ms random latency and 50-500 token generations.
