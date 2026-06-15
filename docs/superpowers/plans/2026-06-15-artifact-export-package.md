# Artifact Export Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users turn generated artifacts into an explicit final submission package with an artifact manifest, prioritized outputs, and a downloadable zip from Studio.

**Architecture:** Add an `ArtifactPackageService` that scans safe workspace artifacts, writes `exports/artifact_manifest.json`, and builds `exports/submission_package.zip` with final files plus key logs/manifests. Extend artifact APIs with package creation and download endpoints. Studio adds a package button and visible export status while keeping existing preview behavior.

**Tech Stack:** Python pathlib/json/zipfile, FastAPI FileResponse, pytest, existing artifact safety rules, Vue 3, Axios, Vite.

---

## File Structure

- Create `backend/app/services/artifact_package_service.py`: artifact manifest and zip package creation.
- Modify `backend/app/routers/artifacts_router.py`: package create/download endpoints.
- Create `backend/app/tests/test_artifact_package_service.py`: service and API tests.
- Modify `frontend/src/apis/guiApi.ts`: package API types/functions.
- Modify `frontend/src/pages/studio/index.vue`: export package button/status/download in artifacts card.
- Modify `README.md` and `MathModelAgentDesign/DESIGN.md`: document Q route.

## Task 1: Artifact Package Service

**Files:**
- Create: `backend/app/services/artifact_package_service.py`
- Test: `backend/app/tests/test_artifact_package_service.py`

- [ ] **Step 1: Write failing service tests**

Cover:

```python
def test_artifact_package_service_creates_manifest_and_zip(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "res.md").write_text("# Paper", encoding="utf-8")
    (workspace / "figures").mkdir()
    (workspace / "figures" / "q1.svg").write_text("<svg />", encoding="utf-8")
    (workspace / ".secret").write_text("skip", encoding="utf-8")

    package = ArtifactPackageService(workspace).create_package()

    assert package["package_path"] == "exports/submission_package.zip"
    assert package["artifact_count"] == 2
    assert workspace.joinpath("exports", "artifact_manifest.json").exists()
    assert workspace.joinpath("exports", "submission_package.zip").exists()
```

Also assert hidden files and previous exports are excluded from the package input list.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_artifact_package_service.py -q`

Expected: import failure for `app.services.artifact_package_service`.

- [ ] **Step 3: Implement service**

Implement:

```python
class ArtifactPackageService:
    def __init__(self, workspace: Path | str) -> None: ...
    def build_manifest(self) -> dict[str, Any]: ...
    def create_package(self) -> dict[str, Any]: ...
```

Rules:
- Skip hidden files, cache dirs, `exports/submission_package.zip`, and unsafe paths.
- Include text/code/figures/data/PDF/DOCX/TEX/JSON/CSV artifacts.
- Assign priority: final paper files (`res.pdf`, `res.docx`, `res.md`, `.tex`) first, figures next, logs/manifests later.
- Write `exports/artifact_manifest.json` before zipping and include it in the zip.
- Return `package_path`, `manifest_path`, `artifact_count`, `size`, and `artifacts`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_artifact_package_service.py -q`
Run: `cd backend && uv run ruff check app/services/artifact_package_service.py app/tests/test_artifact_package_service.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/services/artifact_package_service.py backend/app/tests/test_artifact_package_service.py
git commit -m "feat: add artifact package service"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 2: Artifact Package Backend API

**Files:**
- Modify: `backend/app/routers/artifacts_router.py`
- Test: `backend/app/tests/test_artifact_package_service.py`

- [ ] **Step 1: Write failing API tests**

Add tests for:
- `POST /api/gui/workspaces/{task_id}/artifacts/package` creates zip and returns metadata.
- `GET /api/gui/workspaces/{task_id}/artifacts/package/download` downloads the zip.
- Missing package download returns 404.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_artifact_package_service.py -q`

Expected: 404 for new endpoints.

- [ ] **Step 3: Implement API**

Expose:
- `POST /workspaces/{task_id}/artifacts/package`
- `GET /workspaces/{task_id}/artifacts/package/download`

Use existing workspace safety helper. Emit progress event `artifacts.package_created` after package creation.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_artifact_package_service.py app/tests/test_progress_events.py -q`
Run: `cd backend && uv run ruff check app/services/artifact_package_service.py app/routers/artifacts_router.py app/tests/test_artifact_package_service.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/routers/artifacts_router.py backend/app/tests/test_artifact_package_service.py
git commit -m "feat: add artifact package api"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 3: Studio Export Package UI

**Files:**
- Modify: `frontend/src/apis/guiApi.ts`
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Add frontend types/functions**

Add:

```ts
export interface ArtifactPackageResponse { task_id: string; package_path: string; manifest_path: string; artifact_count: number; size: number; artifacts: ArtifactItem[] }
export function createArtifactPackage(taskId: string) { ... }
export function getArtifactPackageDownloadUrl(taskId: string) { ... }
```

- [ ] **Step 2: Add export controls**

In artifact card:
- Add “生成提交包” button.
- Show artifact count and zip size after creation.
- Add download button/link for package zip.
- Refresh artifact list after package creation so manifest and zip are visible.

- [ ] **Step 3: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 4: Commit and push**

```bash
git add frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue
git commit -m "feat: add studio artifact export package"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 4: Q Route Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document export package**

Document `exports/artifact_manifest.json`, `exports/submission_package.zip`, package endpoints, and Studio usage.

- [ ] **Step 2: Verify**

Run:
```bash
cd backend && uv run pytest app/tests/test_artifact_package_service.py app/tests/test_input_manifest_service.py app/tests/test_revision_service.py app/tests/test_planning_service.py app/tests/test_rag_case_library.py app/tests/test_gui_config.py app/tests/test_gui_workspace.py app/tests/test_progress_events.py -q
cd ../frontend && pnpm build
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md MathModelAgentDesign/DESIGN.md
git commit -m "docs: describe artifact export package"
git push fork HEAD:codex-implement-mcm-agent
```

## Self-Review

Spec coverage:
- Users can preview existing artifacts and now generate a submission package.
- Package includes a manifest for auditability and safe handoff.
- Export API avoids secrets and uploaded private RAG data by only packaging workspace artifacts.
- Studio shows progress and download affordance.

Placeholder scan:
- No placeholders remain. LaTeX compile QA remains a future route; this route packages whatever artifacts exist now.

Type consistency:
- Package paths use `exports/artifact_manifest.json` and `exports/submission_package.zip` in service, API, UI, and docs.
