# Plan Driven Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `planning/plan.json` drive an observable, resumable workspace pipeline with stage state, progress events, and registered artifacts.

**Architecture:** Add a deterministic `PipelineService` that runs a sequence of named stages against a workspace, records `pipeline/state.json`, writes `artifact_registry.json`, and creates placeholder-but-useful stage artifacts. GUI run can use this plan-driven pipeline for `mode=demo`, while the legacy modeling workflow remains available for real LLM execution.

**Tech Stack:** Python pathlib/json, FastAPI, pytest, existing progress events, existing planning/input/RAG/artifact services, Vue already consumes progress/artifacts.

---

## File Structure

- Create `backend/app/services/pipeline_service.py`: stage runner, artifact registry, status persistence.
- Modify `backend/app/routers/gui_workspace_router.py`: route `mode=demo` runs through `PipelineService` and add pipeline status endpoint.
- Create `backend/app/tests/test_pipeline_service.py`: service/API tests.
- Modify `frontend/src/apis/guiApi.ts`: optional pipeline status API type/function.
- Modify `frontend/src/pages/studio/index.vue`: show plan-driven status in run feedback if available.
- Modify `MathModelAgentDesign/DESIGN.md`: document U route completion.

## Task 1: Pipeline Service

**Files:**
- Create: `backend/app/services/pipeline_service.py`
- Test: `backend/app/tests/test_pipeline_service.py`

- [ ] **Step 1: Write failing tests**

Cover:

```python
def test_pipeline_service_runs_stages_and_registers_artifacts(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "input" / "problem").mkdir(parents=True)
    (workspace / "input" / "problem" / "problem.txt").write_text("Optimize routing.", encoding="utf-8")
    PlanningService(workspace).create_plan(problem_text="Optimize routing.")

    result = PipelineService(workspace, task_id="pipe-task").run()

    assert result["status"] == "completed"
    assert workspace.joinpath("pipeline", "state.json").exists()
    assert workspace.joinpath("artifact_registry.json").exists()
    assert workspace.joinpath("reports", "problem_understanding.md").exists()
    assert workspace.joinpath("res.md").exists()
```

Also assert stage events include `pipeline.stage_completed`.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_pipeline_service.py -q`

Expected: import failure.

- [ ] **Step 3: Implement service**

Stages:
- `intake`: rebuild input manifest.
- `parse`: run `InputParsingService`.
- `rag`: rebuild/query RAG if possible and write `reports/rag_context.md`.
- `plan`: load or create plan.
- `model`: write `reports/model_decision.md`.
- `solve`: write `results/results_registry.json`.
- `write`: write `res.md`.
- `qa`: write `review/reviewer_report.md`.
- `export`: build artifact manifest and zip.

Rules:
- Every stage appends progress events.
- State has `status`, `current_stage`, `stages`, `updated_at`.
- Artifact registry entries have `artifact_id`, `type`, `path`, `producer`, `depends_on`, `status`.
- If a stage fails, mark pipeline `failed` with error message.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_pipeline_service.py -q`

## Task 2: GUI Run Integration

**Files:**
- Modify: `backend/app/routers/gui_workspace_router.py`
- Test: `backend/app/tests/test_pipeline_service.py`

- [ ] **Step 1: Write failing API tests**

Cover:
- `POST /api/gui/workspaces/{task_id}/run` with `mode=demo` runs `PipelineService`.
- `GET /api/gui/workspaces/{task_id}/pipeline/status` returns state.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_pipeline_service.py -q`

Expected: endpoint missing or run still queues old workflow.

- [ ] **Step 3: Implement router integration**

If request mode is `demo`, call `PipelineService(root, task_id).run()` synchronously and return `status=completed`. If mode is `real`, keep existing background legacy workflow.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_pipeline_service.py app/tests/test_gui_workspace.py -q`

## Task 3: Docs, Commit, Push

**Files:**
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document U route**

Describe stage machine, artifact registry, demo mode integration, and recovery status file.

- [ ] **Step 2: Run focused verification**

Run:

```bash
cd backend && uv run pytest app/tests/test_pipeline_service.py app/tests/test_gui_workspace.py -q
```

- [ ] **Step 3: Commit and push**

```bash
git add docs/superpowers/plans/2026-06-15-plan-driven-pipeline.md backend/app/services/pipeline_service.py backend/app/routers/gui_workspace_router.py backend/app/tests/test_pipeline_service.py frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue MathModelAgentDesign/DESIGN.md
git commit -m "feat: add plan driven pipeline"
git push fork HEAD:codex-implement-mcm-agent
```
