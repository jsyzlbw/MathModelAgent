# Multimodal Input Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Studio uploads into a typed multimodal input inventory so the agent can see exactly which problem PDFs, images, spreadsheets, templates, chat attachments, and extra requirements are present before planning or running.

**Architecture:** Add a file-backed input manifest service for each workspace. Upload endpoints update `input/input_manifest.json` with file kind, relative path, suffix, MIME category, size, SHA256, and lightweight preview metadata. A new API lists and previews uploaded inputs. Studio shows the manifest beside upload controls so users can confirm the task package is complete.

**Tech Stack:** Python pathlib/hashlib/mimetypes/csv/json, FastAPI, pytest, existing upload route, Vue 3, Axios, Vite build verification.

---

## File Structure

- Create `backend/app/services/input_manifest_service.py`: scan/update uploaded files and produce lightweight preview metadata.
- Modify `backend/app/routers/gui_workspace_router.py`: update manifest after uploads and expose input listing/preview endpoints.
- Create `backend/app/tests/test_input_manifest_service.py`: service/API tests for manifest and previews.
- Modify `frontend/src/apis/guiApi.ts`: typed input manifest API functions.
- Modify `frontend/src/pages/studio/index.vue`: show uploaded input manifest and preview snippets in the task upload card.
- Modify `README.md` and `MathModelAgentDesign/DESIGN.md`: document P route.

## Task 1: Input Manifest Service

**Files:**
- Create: `backend/app/services/input_manifest_service.py`
- Test: `backend/app/tests/test_input_manifest_service.py`

- [ ] **Step 1: Write failing service tests**

Cover:

```python
def test_input_manifest_records_file_metadata(tmp_path):
    workspace = tmp_path / "workspace"
    path = workspace / "input" / "problem" / "problem.txt"
    path.parent.mkdir(parents=True)
    path.write_text("optimize water allocation", encoding="utf-8")

    manifest = InputManifestService(workspace).rebuild()

    item = manifest["items"][0]
    assert item["kind"] == "problem"
    assert item["path"] == "input/problem/problem.txt"
    assert item["category"] == "text"
    assert item["sha256"]
    assert "optimize water" in item["preview"]
```

Also cover CSV shape preview and image category by suffix.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_input_manifest_service.py -q`

Expected: import failure for `app.services.input_manifest_service`.

- [ ] **Step 3: Implement service**

Implement:

```python
class InputManifestService:
    def __init__(self, workspace: Path | str) -> None: ...
    def rebuild(self) -> dict[str, Any]: ...
    def load(self) -> dict[str, Any]: ...
    def preview(self, relative_path: str) -> dict[str, Any]: ...
```

Rules:
- Scan under `input/problem`, `input/attachments`, `input/template`, `input/requirements`, `input/chat_uploads`.
- Map directories back to API kinds: `problem`, `attachment`, `template`, `requirement`, `chat`.
- Categories: `text`, `table`, `image`, `pdf`, `document`, `archive`, `binary`.
- Text previews read first 2000 characters with `errors="ignore"`.
- CSV previews include columns and up to five rows.
- Image/PDF/document previews return metadata only for now.
- Manifest path is `input/input_manifest.json`.
- Never read outside workspace.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_input_manifest_service.py -q`
Run: `cd backend && uv run ruff check app/services/input_manifest_service.py app/tests/test_input_manifest_service.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/services/input_manifest_service.py backend/app/tests/test_input_manifest_service.py
git commit -m "feat: add input manifest service"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 2: Input Manifest Backend API

**Files:**
- Modify: `backend/app/routers/gui_workspace_router.py`
- Test: `backend/app/tests/test_input_manifest_service.py`

- [ ] **Step 1: Write failing API tests**

Add tests for:
- Uploading files updates `input/input_manifest.json`.
- `GET /api/gui/workspaces/{task_id}/inputs` returns manifest items.
- `GET /api/gui/workspaces/{task_id}/inputs/preview?path=input/problem/problem.txt` returns text preview.
- Path traversal in preview returns 400.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_input_manifest_service.py -q`

Expected: 404 for inputs endpoints or missing manifest after upload.

- [ ] **Step 3: Implement API and upload hook**

In `upload_workspace_files()`, call `InputManifestService(root).rebuild()` after saving files.
Expose:
- `GET /workspaces/{task_id}/inputs`
- `GET /workspaces/{task_id}/inputs/preview`

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_input_manifest_service.py app/tests/test_gui_workspace.py -q`
Run: `cd backend && uv run ruff check app/services/input_manifest_service.py app/routers/gui_workspace_router.py app/tests/test_input_manifest_service.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/routers/gui_workspace_router.py backend/app/tests/test_input_manifest_service.py
git commit -m "feat: add workspace input manifest api"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 3: Studio Input Manifest UI

**Files:**
- Modify: `frontend/src/apis/guiApi.ts`
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Add frontend types/functions**

Add:

```ts
export interface WorkspaceInputItem { kind: WorkspaceFileKind; path: string; filename: string; suffix: string; category: string; size: number; sha256: string; preview: string }
export interface WorkspaceInputManifest { version: number; generated_at: string; items: WorkspaceInputItem[] }
export function listWorkspaceInputs(taskId: string) { ... }
export function previewWorkspaceInput(taskId: string, path: string) { ... }
```

- [ ] **Step 2: Refresh manifest after uploads**

Update Studio:
- Add `workspaceInputs`, `inputPreview`, and loading state.
- After `createWorkspace()` and `uploadFilesForKind()`, call `refreshWorkspaceInputs()`.

- [ ] **Step 3: Show package inventory**

In the upload card, add a compact inventory list:
- Path + category + size.
- Click opens preview below the list.
- Text/table preview renders in a small monospace panel; binary categories show metadata only.

- [ ] **Step 4: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue
git commit -m "feat: show studio input manifest"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 4: P Route Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document multimodal manifest**

Document `input/input_manifest.json`, categories, preview limitation, and why OCR/model parsing remains provider-driven later.

- [ ] **Step 2: Verify**

Run:
```bash
cd backend && uv run pytest app/tests/test_input_manifest_service.py app/tests/test_revision_service.py app/tests/test_planning_service.py app/tests/test_rag_case_library.py app/tests/test_gui_config.py app/tests/test_gui_workspace.py app/tests/test_progress_events.py -q
cd ../frontend && pnpm build
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md MathModelAgentDesign/DESIGN.md
git commit -m "docs: describe multimodal input manifest"
git push fork HEAD:codex-implement-mcm-agent
```

## Self-Review

Spec coverage:
- Current problem upload area now supports multiple files as a typed package rather than opaque storage.
- Multimodal categories include text, table, image, PDF, document, archive, and binary.
- User can see what the agent sees before planning/running.
- No external OCR/API is required for this route; it creates a reliable contract for future MinerU and multimodal providers.

Placeholder scan:
- No placeholders remain. OCR and deep parsing are explicitly deferred to provider integration; metadata and previews are implemented now.

Type consistency:
- Upload kind names match existing `WorkspaceFileKind` values.
- Manifest item `path` is workspace-relative and reused by preview API and frontend click handler.
