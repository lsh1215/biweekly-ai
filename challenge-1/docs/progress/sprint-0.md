# Sprint 0: Risk Validation — Progress Report

> Date: 2026-03-30
> Status: **PASS** — Go decision confirmed

---

## Summary

Sprint 0 validated the two biggest risks: (1) SmolVLA model loading on Apple Silicon MPS, and (2) `claude -p` CLI for orchestrator use. Both passed.

## Results

### 0.1 Project Scaffolding
- **Status**: Complete
- Created full directory structure: `src/{orchestrator,executor,simulation,common}`, `tests/`, `configs/`, `docker/`
- Config files: `pyproject.toml`, `warehouse.yaml`, `robot.yaml`, `objects.yaml`
- Common types: `TaskState` enum, `PickTask`, `VerificationResult`, `Order`, `RobotAction` dataclasses

### 0.2 Python Environment
- **Status**: Complete
- **Python**: 3.12.4 (initially tried 3.14.2 but lerobot incompatible due to stricter dataclass rules)
- **venv**: `.venv/` with Python 3.12
- **Key packages**: torch 2.11.0, transformers 5.4.0, lerobot 0.3.2, pyzmq 27.1.0
- **Issue**: `lerobot` 0.5.0 + Python 3.14 had `TypeError: non-default argument follows default argument` in GR00T N1 dataclass. Resolved by using Python 3.12.

### 0.3 SmolVLA MPS Load Test
- **Status**: PASS
- **Model**: SmolVLA via `lerobot.policies.smolvla` (not `transformers.AutoModelForVision2Seq` — deprecated in transformers 5.x)
- **Parameters**: 450M
- **Memory**: 1.12 GB (well under 8GB limit)
- **Load time**: ~22s (with HuggingFace download caching)
- **MPS device**: Successfully moved to `mps:0`
- **Decision**: Use SmolVLA as primary VLA model (no fallback needed, but ScriptedPolicy available)

### 0.4 claude -p Vision Validation
- **Status**: PASS
- **Response format**: JSON with `--output-format json` — returns `{"type":"result", "result":"..."}` envelope
- **Inner content**: Claude wraps JSON in markdown code fences (```json ... ```), wrapper strips them
- **Latency**: ~5-7s per call (within 10s limit)
- **Mock mode**: Fully functional for testing without live Claude
- **Tests**: 7/7 passing (6 mock + 1 live latency)

### 0.5 Fallback Status
| Component | Primary | Fallback | Status |
|-----------|---------|----------|--------|
| VLA Model | SmolVLA (450M) | ScriptedPolicy | Primary works |
| Vision | claude -p | Gazebo API pose query | Primary works |
| Python | 3.12.4 | — | Required (3.14 incompatible) |

## Test Results

```
tests/test_sprint0_smolvla.py — 7 passed (MPS: 2, SmolVLA: 3, Fallback: 2)
tests/test_sprint0_vision.py  — 7 passed (Wrapper: 3, Vision: 3, Latency: 1)
Total: 14 passed, 0 failed
```

## Issues & Resolutions

| Issue | Resolution |
|-------|-----------|
| Python 3.14 + lerobot dataclass error | Switched to Python 3.12.4 |
| `AutoModelForVision2Seq` removed in transformers 5.x | Use `lerobot.policies.smolvla.SmolVLAPolicy` directly |
| `num2words` missing for SmolVLM processor | `pip install num2words` |
| claude -p wraps JSON in markdown fences | Wrapper strips ``` fences before parsing |

## Go/No-Go Decision

**GO** — Both critical risks validated. Proceeding to Sprint 1 (Simulation Environment).
