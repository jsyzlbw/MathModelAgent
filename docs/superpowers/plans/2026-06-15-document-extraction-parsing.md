# Document Extraction Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade uploaded input manifests into parsed, agent-readable artifacts under `input/parsed/`, with QA diagnostics and Studio visibility.

**Architecture:** Add a deterministic `InputParsingService` that consumes `input/input_manifest.json`, parses text and table files directly, records PDF/image/Office metadata as provider-ready placeholders, and writes a parsed manifest plus `problem.md`, normalized tables, asset metadata, and QA markdown. Expose a backend parse endpoint and a Studio button so users can trigger parsing before planning.

**Tech Stack:** Python pathlib/json/csv/shutil, FastAPI, pytest, existing `InputManifestService`, progress events, Vue 3, TypeScript, Vite.

---

## File Structure

- Create `backend/app/services/input_parsing_service.py`: parse manifest items into `input/parsed/` artifacts.
- Modify `backend/app/routers/gui_workspace_router.py`: add `POST /workspaces/{task_id}/inputs/parse` and `GET /workspaces/{task_id}/inputs/parsed`.
- Create `backend/app/tests/test_input_parsing_service.py`: service and API tests.
- Modify `frontend/src/apis/guiApi.ts`: parsed input API types/functions.
- Modify `frontend/src/pages/studio/index.vue`: parse button, parsed summary, QA preview in upload panel.
- Modify `MathModelAgentDesign/DESIGN.md`: document S route completion.

## Task 1: Input Parsing Service

**Files:**
- Create: `backend/app/services/input_parsing_service.py`
- Test: `backend/app/tests/test_input_parsing_service.py`

- [ ] **Step 1: Write failing service tests**

Cover:

```python
def test_input_parsing_service_writes_problem_markdown_and_table_copy(tmp_path):
    workspace = tmp_path / "workspace"
    problem = workspace / "input" / "problem" / "problem.txt"
    table = workspace / "input" / "attachments" / "data.csv"
    problem.parent.mkdir(parents=True)
    table.parent.mkdir(parents=True)
    problem.write_text("Optimize water allocation.", encoding="utf-8")
    table.write_text("city,value\nA,1\n", encoding="utf-8")
    InputManifestService(workspace).rebuild()

    parsed = InputParsingService(workspace).parse()

    assert parsed["status"] == "parsed"
    assert workspace.joinpath("input", "parsed", "problem.md").exists()
    assert workspace.joinpath("input", "parsed", "tables", "data.csv").exists()
    assert parsed["qa"]["issue_count"] == 0
```

Also cover PDF/image placeholder metadata and missing manifest rebuild.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_input_parsing_service.py -q`

Expected: import failure for `InputParsingService`.

- [ ] **Step 3: Implement service**

Implement:
- `InputParsingService(workspace)`
- `parse()`
- `load()`

Rules:
- Rebuild input manifest when missing.
- Write `input/parsed/parsed_manifest.json`.
- Write `input/parsed/problem.md` by concatenating text/table problem files and metadata stubs for PDFs/documents/images.
- Copy CSV/TSV attachments to `input/parsed/tables/`.
- Write `input/parsed/assets/assets_manifest.json` for images/PDF/documents/binary files.
- Write `input/parsed/parse_qa.md` listing issue severity and provider-needed items.
- Do not fail on unsupported formats; record them as `provider_required`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_input_parsing_service.py -q`

## Task 2: Backend Parse API

**Files:**
- Modify: `backend/app/routers/gui_workspace_router.py`
- Test: `backend/app/tests/test_input_parsing_service.py`

- [ ] **Step 1: Write failing API tests**

Add tests for:
- `POST /api/gui/workspaces/{task_id}/inputs/parse` creates parsed artifacts and progress event.
- `GET /api/gui/workspaces/{task_id}/inputs/parsed` returns current parsed manifest.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_input_parsing_service.py -q`

Expected: 404 for new endpoints.

- [ ] **Step 3: Implement API**

Use existing safe task ID logic. Append progress event:
- `inputs.parse_started`
- `inputs.parse_completed`

Return parsed manifest with `status`, `artifacts`, and `qa`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_input_parsing_service.py app/tests/test_input_manifest_service.py -q`

## Task 3: Studio Parse Controls

**Files:**
- Modify: `frontend/src/apis/guiApi.ts`
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Add API types/functions**

Add:
- `WorkspaceParsedInputs`
- `parseWorkspaceInputs(taskId)`
- `getWorkspaceParsedInputs(taskId)`

- [ ] **Step 2: Add GUI controls**

In the upload/input manifest card:
- Add “解析输入” button.
- Show parsed status, artifact count, QA issue count.
- Show QA markdown summary in a compact `<pre>` block.

- [ ] **Step 3: Verify frontend build**

Run: `cd frontend && pnpm build`

## Task 4: Route Verification, Docs, Commit, Push

**Files:**
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document S route**

Add a short section describing parsed artifacts, QA report, and provider-ready placeholder behavior.

- [ ] **Step 2: Run focused verification**

Run:

```bash
cd backend && uv run pytest app/tests/test_input_parsing_service.py app/tests/test_input_manifest_service.py -q
cd frontend && pnpm build
```

- [ ] **Step 3: Commit and push**

```bash
git add docs/superpowers/plans/2026-06-15-document-extraction-parsing.md backend/app/services/input_parsing_service.py backend/app/routers/gui_workspace_router.py backend/app/tests/test_input_parsing_service.py frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue MathModelAgentDesign/DESIGN.md
git commit -m "feat: add workspace input parsing"
git push fork HEAD:codex-implement-mcm-agent
```
