# Security Review — PLAN_local_dev_wsl2

**Date:** 2026-07-19
**Auditor:** Task 6 of PLAN_local_dev_wsl2
**Scope:** All code produced in Tasks 1–5

## Summary

| Check | Result |
|-------|--------|
| Hardcoded secrets | ✅ None found |
| Prompt injection | ⚠️ Low risk (see §2) |
| Input validation (FastAPI) | ⚠️ Limited (see §3) |
| API key handling | ✅ Correct (env vars only) |
| Dependency vulnerabilities | ⚠️ Not audited (see §4) |
| Docker security | ⚠️ Runs as root (see §5) |

---

## 1. Hardcoded Secrets

**Status:** ✅ Clean

- No API keys, passwords, or tokens found in `src/`
- `configs/agent.yaml` stores `api_key_env: ANTHROPIC_API_KEY` (env var name only, correct pattern)
- `tuner_agent.py` reads via `os.getenv()` — no hardcoded values

---

## 2. Prompt Injection (Agent Tuning)

**Status:** ⚠️ Low Risk — Design Limitation

The `TunerAgent` feeds `metrics_before/after` values and `config_str` into the LLM prompt. A malicious or malformed benchmark result (e.g., `TunerAgent._get_metrics_from_runner()` returning crafted values) could influence LLM recommendations.

**Mitigations:**
- All metrics come from the local `BenchmarkRunner`, not external user input
- `json.dumps()` sanitizes dict values before insertion
- `history` field contains LLM-generated `reasoning` — this is a known agent self-reflection loop risk; the `DECISION_PROMPT` constrains output to JSON format

**Recommendation:** Add schema validation on LLM JSON output before applying config changes:
```python
changes = llm_response.get("changes", {})
# Validate keys are known config params before applying
allowed = {"batch_size", "chunk_size", "kv_cache_high_watermark", "prefill_ratio"}
if not all(k in allowed for k in changes):
    logger.warning("LLM returned unknown config keys, skipping")
    changes = {}
```

---

## 3. Input Validation (FastAPI Control Layer)

**Status:** ⚠️ Limited

`POST /config` accepts numeric parameters (`batch_size`, `kv_cache_high_watermark`, etc.) via `UpdateConfigRequest`. Pydantic validates types but **does not enforce numeric ranges**.

A negative `batch_size` or `kv_cache_high_watermark > 1.0` would be accepted.

**Recommendation:** Add range validators in `UpdateConfigRequest`:
```python
class UpdateConfigRequest(BaseModel):
    batch_size: Optional[int] = Field(None, gt=0, le=256)
    kv_cache_high_watermark: Optional[float] = Field(None, gt=0, le=1.0)
```

---

## 4. Dependency Vulnerabilities

**Status:** ⚠️ Not audited

Key dependencies: `fastapi`, `uvicorn`, `pydantic`, `anthropic`, `openai`, `vllm`.

**Recommendation:** Run `pip audit` or `safety check` before production deployment:
```bash
pip install safety
safety check --file requirements.txt
```

Known common issues in transitive deps (noted for future review):
- `vllm` has not been audited for CVE at time of this review
- `fastapi`/`pydantic` — ensure latest stable version used in H100 environment

---

## 5. Docker Security

**Status:** ⚠️ Runs as Root

`Dockerfile` uses `nvidia/cuda:12.4.1-runtime-ubuntu22.04` base image and does **not** specify a `USER` directive. The container runs as root by default.

**Recommendation:** Add a non-root user:
```dockerfile
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
```

Also consider:
- Use `--read-only` flag for production containers
- Add `.dockerignore` to exclude unnecessary files

---

## 6. Other Observations

| Item | Status | Notes |
|------|--------|-------|
| `src/main.py` — `--mode tune` REST calls | ✅ OK | `tuner` URL defaults to `localhost:8000`; no auth on REST endpoints |
| `configs/model.yaml` — model names | ✅ OK | No SSRF risk from model name field |
| `launch_h100.sh` — shell injection | ✅ OK | All args are quoted; `set -e` present |
| WSL2 env (Task 1) | ✅ OK | All env vars set explicitly; no `.wslconfig` modified |

---

## Recommendations Summary

| Priority | Finding | Action |
|----------|---------|--------|
| Medium | FastAPI POST /config lacks range validation | Add Pydantic `Field(gt=0, le=N)` validators |
| Low | Dockerfile runs as root | Add `USER appuser` directive |
| Low | LLM output not schema-validated before applying | Validate `changes` keys against allowed set |
| Low | No `pip audit` run | Run dependency vulnerability scan before H100 deployment |

---

## Conclusion

**Issues found — not blocking.** The codebase is structurally sound for local development. The identified issues are standard production hardening items (non-root container, input range validation, dependency scanning) that should be addressed before H100 deployment.
