# Modeling Solver Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic modeling intelligence layer that recognizes common MCM/ICM problem types, proposes candidate models, selects a practical route, and writes solver template artifacts plus a results registry.

**Architecture:** Create `ModelingStrategyService` for task-type classification and model candidate scoring, and `SolverTemplateService` for code skeleton/result registry generation. Integrate these into `PipelineService` model/solve stages so demo runs produce meaningful modeling artifacts instead of generic placeholders.

**Tech Stack:** Python pathlib/json/re/datetime, pytest, existing pipeline service.

---

## File Structure

- Create `backend/app/services/modeling_strategy_service.py`: problem type detection, candidate model library, selection report.
- Create `backend/app/services/solver_template_service.py`: write solver skeletons and results registry.
- Create `backend/app/tests/test_modeling_strategy_service.py`: service and pipeline integration tests.
- Modify `backend/app/services/pipeline_service.py`: use modeling/solver services in model and solve stages.
- Modify `MathModelAgentDesign/DESIGN.md`: document W route completion.

## Task 1: Modeling Strategy And Solver Templates

**Files:**
- Create: `backend/app/services/modeling_strategy_service.py`
- Create: `backend/app/services/solver_template_service.py`
- Test: `backend/app/tests/test_modeling_strategy_service.py`

- [ ] **Step 1: Write failing tests**

Cover:
- text containing `forecast` produces type `prediction`.
- text containing `optimize` produces type `optimization`.
- candidate model list includes ARIMA/regression for prediction and linear/integer programming for optimization.
- solver template writes `code/solver_<type>.py` and `results/results_registry.json`.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_modeling_strategy_service.py -q`

Expected: import failure.

- [ ] **Step 3: Implement services**

Problem types:
- `prediction`
- `optimization`
- `evaluation`
- `classification`
- `network`
- `simulation`
- `risk`
- `geospatial`
- `generic`

Write:
- `reports/model_candidates.json`
- `reports/model_decision.md`
- `code/solver_<problem_type>.py`
- `results/results_registry.json`

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_modeling_strategy_service.py -q`

## Task 2: Pipeline Integration

**Files:**
- Modify: `backend/app/services/pipeline_service.py`
- Test: `backend/app/tests/test_modeling_strategy_service.py`

- [ ] **Step 1: Add failing integration test**

Run pipeline on text `Forecast demand and optimize allocation`; assert:
- `reports/model_candidates.json` exists.
- `results/results_registry.json` includes `problem_type`.
- solver code file exists.

- [ ] **Step 2: Implement integration**

Pipeline model stage uses `ModelingStrategyService`; solve stage uses `SolverTemplateService`.

- [ ] **Step 3: Verify**

Run:

```bash
cd backend && uv run pytest app/tests/test_modeling_strategy_service.py app/tests/test_pipeline_service.py -q
```

## Task 3: Docs, Commit, Push

- [ ] **Step 1: Document W route**
- [ ] **Step 2: Commit and push**

```bash
git add docs/superpowers/plans/2026-06-15-modeling-solver-enhancement.md backend/app/services/modeling_strategy_service.py backend/app/services/solver_template_service.py backend/app/services/pipeline_service.py backend/app/tests/test_modeling_strategy_service.py MathModelAgentDesign/DESIGN.md
git commit -m "feat: add modeling strategy solver templates"
git push fork HEAD:codex-implement-mcm-agent
```
