# GUI Service Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend service foundation that lets the existing Vue GUI use one ignored JSON config file, test each configured API independently, manage task workspaces, show progress events, run tasks in the background, and browse generated artifacts.

**Architecture:** Extend the current FastAPI backend under `backend/app` instead of creating a second service. Add small route modules for runtime config, GUI workspaces, progress events, and artifacts; keep existing `/modeling` compatibility while exposing stable `/api/gui/*` endpoints for the new product workflow. Runtime secrets live in `backend/mcm_agent_config.local.json`, which is ignored by git; `backend/mcm_agent_config.example.json` is committed as the template.

**Tech Stack:** FastAPI, Pydantic v2, existing Redis/WebSocket message manager, current `MathModelWorkFlow`, pytest, ruff, Vue integration in later L route.

---

## File Structure

- Create `backend/app/config/runtime_config.py`: load, merge, mask, and save the ignored JSON runtime configuration.
- Create `backend/app/config/provider_smoke.py`: deterministic provider connectivity checks for LLM, OpenAlex, Tavily, and placeholder external APIs.
- Create `backend/app/routers/config_router.py`: REST API for config read/write and per-provider connectivity tests.
- Create `backend/app/routers/gui_workspace_router.py`: create/list/read GUI workspaces, upload files into structured folders, and start/stop/resume runs.
- Create `backend/app/routers/artifacts_router.py`: list, read, and download safe files under a task workspace.
- Create `backend/app/core/progress_events.py`: append JSONL progress events and read them back with an `after` cursor.
- Modify `backend/app/main.py`: include new routers under stable `/api/gui` prefixes.
- Modify `backend/app/core/workflow.py` and `backend/app/routers/modeling_router.py`: emit progress events alongside existing Redis messages and expose task run state.
- Create `backend/mcm_agent_config.example.json`: committed template without secrets.
- Modify `.gitignore`: ignore `backend/mcm_agent_config.local.json`, GUI uploaded knowledge base contents, and runtime workspaces.
- Create backend tests in `backend/app/tests/test_gui_config.py`, `backend/app/tests/test_gui_workspace.py`, and `backend/app/tests/test_progress_events.py`.

## Task 1: JSON Runtime Config Store

**Files:**
- Create: `backend/app/config/runtime_config.py`
- Create: `backend/mcm_agent_config.example.json`
- Modify: `.gitignore`
- Test: `backend/app/tests/test_gui_config.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from app.config.runtime_config import RuntimeConfigStore, mask_secret


def test_runtime_config_store_writes_local_json_and_masks_secrets(tmp_path: Path):
    example = tmp_path / "example.json"
    local = tmp_path / "local.json"
    example.write_text(
        '{"llm":{"coordinator":{"api_key":"","model":"gpt-test"}},"search":{"tavily":{"api_key":""}}}',
        encoding="utf-8",
    )

    store = RuntimeConfigStore(example_path=example, local_path=local)
    saved = store.save({"llm": {"coordinator": {"api_key": "sk-secret"}}})

    assert local.exists()
    assert saved["llm"]["coordinator"]["api_key_configured"] is True
    assert saved["llm"]["coordinator"]["api_key_preview"].endswith("cret")
    assert "sk-secret" not in str(saved)


def test_mask_secret_keeps_empty_values_unconfigured():
    assert mask_secret("") == {"configured": False, "preview": ""}
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`

Expected: import failure for `app.config.runtime_config`.

- [ ] **Step 3: Implement config store**

Implement `RuntimeConfigStore.load_raw()`, `load_masked()`, `save()`, deep merge of example defaults and user overrides, and recursive masking for keys containing `api_key`, `token`, `secret`, or `password`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`
Run: `cd backend && uv run ruff check app/config/runtime_config.py app/tests/test_gui_config.py`

- [ ] **Step 5: Commit and push**

```bash
git add .gitignore backend/app/config/runtime_config.py backend/app/tests/test_gui_config.py backend/mcm_agent_config.example.json
git commit -m "feat: add gui runtime config store"
git push origin codex/implement-mcm-agent
```

## Task 2: Config API and Per-Provider Connectivity Tests

**Files:**
- Create: `backend/app/config/provider_smoke.py`
- Create: `backend/app/routers/config_router.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_gui_config.py`

- [ ] **Step 1: Write failing endpoint tests**

Add tests using FastAPI `TestClient` with dependency-free temp config paths. Cover:

```python
def test_gui_config_endpoint_masks_api_keys(client): ...
def test_gui_config_test_provider_reports_missing_key(client): ...
def test_gui_config_test_provider_accepts_config_payload_without_persisting(client): ...
```

Expected API:
- `GET /api/gui/config`
- `PUT /api/gui/config`
- `POST /api/gui/config/test-provider` with `{ "provider": "coordinator", "config": {...optional draft...} }`

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`

Expected: 404 for `/api/gui/config`.

- [ ] **Step 3: Implement router and smoke checker**

Implement LLM provider checks using the existing provider classes with `max_tokens=1`. Implement OpenAlex check via `httpx`. For search/data providers, return structured `missing_config`, `not_implemented`, or `ok` states instead of crashing. Never return raw secrets.

- [ ] **Step 4: Include router in app**

Add `app.include_router(config_router.router, prefix="/api/gui")` in `backend/app/main.py`.

- [ ] **Step 5: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`
Run: `cd backend && uv run ruff check app/config/provider_smoke.py app/routers/config_router.py app/main.py app/tests/test_gui_config.py`

- [ ] **Step 6: Commit and push**

```bash
git add backend/app/config/provider_smoke.py backend/app/routers/config_router.py backend/app/main.py backend/app/tests/test_gui_config.py
git commit -m "feat: add gui config api and provider tests"
git push origin codex/implement-mcm-agent
```

## Task 3: GUI Workspace and Upload API

**Files:**
- Create: `backend/app/routers/gui_workspace_router.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_gui_workspace.py`

- [ ] **Step 1: Write failing workspace tests**

Cover:
- `POST /api/gui/workspaces` creates `project/work_dir/<task_id>/input/{problem,attachments,template,requirements}`.
- `POST /api/gui/workspaces/{task_id}/files?kind=problem|attachment|template|requirement` stores uploaded files in the correct subfolder.
- path traversal in task id or file name is rejected.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_gui_workspace.py -q`

Expected: 404 or missing router.

- [ ] **Step 3: Implement workspace router**

Reuse `create_task_id`, `create_work_dir`, and `ensure_safe_task_id`. Add safe filename sanitization. Add `GET /api/gui/workspaces` and `GET /api/gui/workspaces/{task_id}/status`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_gui_workspace.py -q`
Run: `cd backend && uv run ruff check app/routers/gui_workspace_router.py app/tests/test_gui_workspace.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/routers/gui_workspace_router.py backend/app/main.py backend/app/tests/test_gui_workspace.py
git commit -m "feat: add gui workspace upload api"
git push origin codex/implement-mcm-agent
```

## Task 4: Progress Events and Artifact API

**Files:**
- Create: `backend/app/core/progress_events.py`
- Create: `backend/app/routers/artifacts_router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/modeling_router.py`
- Test: `backend/app/tests/test_progress_events.py`
- Test: `backend/app/tests/test_gui_workspace.py`

- [ ] **Step 1: Write failing tests**

Cover:
- appending two events returns sequence numbers `1`, `2`.
- `GET /api/gui/workspaces/{task_id}/events?after=1` returns only event `2`.
- artifacts list includes safe files and excludes hidden/cache files.
- artifact content endpoint rejects `../` traversal.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_progress_events.py app/tests/test_gui_workspace.py -q`

Expected: import failure for `progress_events` and 404 for artifact/events endpoints.

- [ ] **Step 3: Implement progress events**

Create JSONL event writer under `project/work_dir/<task_id>/progress_events.jsonl` with fields `seq`, `timestamp`, `level`, `stage`, `message`, and `metadata`.

- [ ] **Step 4: Implement event and artifact endpoints**

Expose:
- `GET /api/gui/workspaces/{task_id}/events`
- `GET /api/gui/workspaces/{task_id}/artifacts`
- `GET /api/gui/workspaces/{task_id}/artifacts/content?path=res.md`
- `GET /api/gui/workspaces/{task_id}/artifacts/download?path=res.docx`

- [ ] **Step 5: Wire existing task messages into progress events**

In `run_modeling_task_async`, append events for task start, workflow success, cancel, and failure. Keep Redis/WebSocket behavior unchanged.

- [ ] **Step 6: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_progress_events.py app/tests/test_gui_workspace.py -q`
Run: `cd backend && uv run ruff check app/core/progress_events.py app/routers/artifacts_router.py app/routers/modeling_router.py app/tests/test_progress_events.py app/tests/test_gui_workspace.py`

- [ ] **Step 7: Commit and push**

```bash
git add backend/app/core/progress_events.py backend/app/routers/artifacts_router.py backend/app/main.py backend/app/routers/modeling_router.py backend/app/tests/test_progress_events.py backend/app/tests/test_gui_workspace.py
git commit -m "feat: add gui progress and artifact APIs"
git push origin codex/implement-mcm-agent
```

## Task 5: Background Run, Resume, and Stop API

**Files:**
- Modify: `backend/app/routers/gui_workspace_router.py`
- Modify: `backend/app/routers/modeling_router.py`
- Test: `backend/app/tests/test_gui_workspace.py`

- [ ] **Step 1: Write failing run-control tests**

Cover:
- `POST /api/gui/workspaces/{task_id}/run` starts a background task from uploaded problem text.
- `POST /api/gui/workspaces/{task_id}/stop` delegates to existing cancellation state.
- `POST /api/gui/workspaces/{task_id}/resume` records a resume-request event and returns a clear MVP status.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_gui_workspace.py -q`

Expected: 404 for run control endpoints.

- [ ] **Step 3: Implement run-control endpoints**

For MVP, load question text from uploaded problem files or `problem_text` body, call existing `run_modeling_task_async` through `BackgroundTasks`, and return `{task_id,status}`. Stop must use the same active task registry as `/modeling/{task_id}/cancel`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_gui_workspace.py -q`
Run: `cd backend && uv run ruff check app/routers/gui_workspace_router.py app/routers/modeling_router.py app/tests/test_gui_workspace.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/routers/gui_workspace_router.py backend/app/routers/modeling_router.py backend/app/tests/test_gui_workspace.py
git commit -m "feat: add gui workflow run controls"
git push origin codex/implement-mcm-agent
```

## Task 6: K Route Documentation and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `MathModelAgentDesign/DESIGN.md` or create `docs/superpowers/specs/2026-06-15-gui-productization-design.md` if the design folder is committed.
- Test: existing backend tests.

- [ ] **Step 1: Update docs**

Document:
- `backend/mcm_agent_config.local.json` is the ignored runtime config.
- `backend/mcm_agent_config.example.json` is the committed template.
- Per-provider test endpoint powers one button beside every API config row.
- RAG knowledge base starts empty and is filled by the user in later M route.
- GUI service endpoints under `/api/gui`.

- [ ] **Step 2: Verify docs and backend tests**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py app/tests/test_gui_workspace.py app/tests/test_progress_events.py -q`
Run: `cd backend && uv run ruff check app`

- [ ] **Step 3: Commit and push**

```bash
git add README.md MathModelAgentDesign/DESIGN.md docs/superpowers/specs/2026-06-15-gui-productization-design.md backend/mcm_agent_config.example.json
git commit -m "docs: describe gui service foundation"
git push origin codex/implement-mcm-agent
```

## Self-Review

Spec coverage:
- Unified JSON config is covered by Tasks 1-2.
- Each API row test button backend support is covered by Task 2.
- Workspace uploads for problem, attachments, template, and requirements are covered by Task 3.
- User-visible progress is covered by Task 4.
- Run/stop/resume backend control is covered by Task 5.
- Documentation and GitHub sync are covered by Task 6.

Placeholder scan:
- No task contains TBD or TODO placeholders. MVP limitations are explicit where resume is not yet a full workflow replay.

Type consistency:
- Endpoint prefixes consistently use `/api/gui`.
- Task identifiers consistently use `task_id`.
