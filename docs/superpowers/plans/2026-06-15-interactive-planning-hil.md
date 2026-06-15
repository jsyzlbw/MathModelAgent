# Interactive Planning And HIL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit plan approval layer before long-running modeling tasks: the agent proposes a structured plan, the user can confirm/edit/regenerate/ask/skip/abort, and the final approved plan is stored in the workspace for downstream runs.

**Architecture:** Implement a deterministic backend planning service for MVP. It reads workspace problem text and RAG manifest hints, generates a structured `planning/plan.json`, appends progress events, and exposes HIL actions under `/api/gui/workspaces/{task_id}/planning`. The frontend Studio plan editor talks to these endpoints and persists user decisions.

**Tech Stack:** FastAPI, Pydantic, pathlib/json, existing workspace/progress utilities, pytest, Vue Studio, Axios.

---

## File Structure

- Create `backend/app/services/planning_service.py`: plan draft creation, load/save, and HIL action handling.
- Create `backend/app/routers/planning_router.py`: planning/HIL API routes.
- Modify `backend/app/main.py`: include planning router under `/api/gui`.
- Create `backend/app/tests/test_planning_service.py`: service and API tests.
- Modify `frontend/src/apis/guiApi.ts`: planning API types/functions.
- Modify `frontend/src/pages/studio/index.vue`: generate plan, apply HIL actions, show plan status.
- Modify `README.md` and `MathModelAgentDesign/DESIGN.md`: document N route.

## Task 1: Planning Service

**Files:**
- Create: `backend/app/services/planning_service.py`
- Test: `backend/app/tests/test_planning_service.py`

- [ ] **Step 1: Write failing tests**

Cover:
- `create_plan()` writes `planning/plan.json` with status `draft`.
- Plan contains problem summary, data inventory, modeling steps, expected artifacts, and risks.
- `apply_action(confirm)` changes status to `approved`.
- `apply_action(edit)` updates plan content and keeps status `draft`.
- Invalid action raises a clear error.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_planning_service.py -q`

Expected: import failure for `app.services.planning_service`.

- [ ] **Step 3: Implement service**

Use deterministic heuristics for MVP:
- summarize first 500 characters of problem text
- infer data inventory from `input/attachments`
- default modeling steps: understand, data, model candidates, solve, validate, write, review
- expected artifacts: `planning/plan.json`, `res.md`, `res.docx`, figures, logs

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_planning_service.py -q`
Run: `cd backend && uv run ruff check app/services/planning_service.py app/tests/test_planning_service.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/services/planning_service.py backend/app/tests/test_planning_service.py
git commit -m "feat: add interactive planning service"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 2: Planning/HIL Backend API

**Files:**
- Create: `backend/app/routers/planning_router.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_planning_service.py`

- [ ] **Step 1: Write failing API tests**

Endpoints:
- `POST /api/gui/workspaces/{task_id}/planning/draft`
- `GET /api/gui/workspaces/{task_id}/planning`
- `POST /api/gui/workspaces/{task_id}/planning/action`

Actions: `confirm`, `edit`, `regenerate`, `ask`, `skip`, `abort`.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_planning_service.py -q`

Expected: 404 for planning endpoints.

- [ ] **Step 3: Implement router**

Use safe task id validation and `project/work_dir/<task_id>` roots. Append progress events for draft creation and HIL actions.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_planning_service.py -q`
Run: `cd backend && uv run ruff check app/routers/planning_router.py app/main.py app/tests/test_planning_service.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/routers/planning_router.py backend/app/main.py backend/app/tests/test_planning_service.py
git commit -m "feat: add planning hil api"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 3: Studio Planning/HIL Integration

**Files:**
- Modify: `frontend/src/apis/guiApi.ts`
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Add frontend planning API**

Add types and functions:
- `draftWorkspacePlan(taskId, problemText?)`
- `getWorkspacePlan(taskId)`
- `applyWorkspacePlanAction(taskId, payload)`

- [ ] **Step 2: Wire Studio plan panel**

Add buttons:
- 生成计划
- 确认
- 保存修改
- 重新生成
- 提问
- 跳过
- 中止

Show plan status and last decision. Keep plan editor editable.

- [ ] **Step 3: Run controls use approved plan**

When starting a run, if plan status is not approved, show a warning toast but allow manual override for MVP.

- [ ] **Step 4: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue
git commit -m "feat: add studio planning hil controls"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 4: N Route Final Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document planning workflow**

Document the plan-first workflow and the six HIL actions.

- [ ] **Step 2: Verify**

Run:
```bash
cd backend && uv run pytest app/tests/test_planning_service.py app/tests/test_rag_case_library.py app/tests/test_gui_config.py app/tests/test_gui_workspace.py app/tests/test_progress_events.py -q
cd ../frontend && pnpm build
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md MathModelAgentDesign/DESIGN.md
git commit -m "docs: describe interactive planning hil"
git push fork HEAD:codex-implement-mcm-agent
```

## Self-Review

Spec coverage:
- User/agent plan discussion before execution is covered.
- Six HIL actions are represented in backend and frontend.
- Plan is stored as a workspace artifact for downstream workflows.
- User-visible progress events are emitted for planning actions.

Placeholder scan:
- No placeholders remain. LLM-based planning is deferred; deterministic MVP enables UI and workflow contract now.

Type consistency:
- Plan status uses `draft`, `approved`, `skipped`, `aborted`.
- HIL action names match existing product requirement: confirm/edit/regenerate/ask/skip/abort.
