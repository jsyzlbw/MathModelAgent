# Structured RAG Case Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the empty user-filled RAG folder into a structured case library with validation, manifest generation, lightweight indexing, backend API access, and GUI visibility.

**Architecture:** Keep user content in ignored `backend/data/rag_cases/`. Commit only `.gitkeep`, schema docs, and code. Add a backend service that scans one folder per modeling case, validates required files, writes a non-secret `.rag_manifest.json`, and builds a lightweight keyword index JSON. Later workflows can consume the same manifest/index without relying on GUI state.

**Tech Stack:** Python pathlib/json/hashlib, FastAPI routes under `/api/gui/rag`, pytest, existing Vue Studio page, no vector DB yet for M MVP.

---

## File Structure

- Create `backend/app/services/rag_case_library.py`: scan, validate, manifest, and keyword index logic.
- Create `backend/app/routers/rag_router.py`: GUI API for listing cases, validating a case, rebuilding index, and reading the library guide.
- Modify `backend/app/main.py`: include RAG router under `/api/gui/rag`.
- Create `backend/data/rag_cases/README.md`: committed user instructions for case folder structure.
- Create `backend/app/tests/test_rag_case_library.py`: service and API tests.
- Modify `frontend/src/apis/guiApi.ts`: typed RAG API functions.
- Modify `frontend/src/pages/studio/index.vue`: RAG panel lists cases, validation state, rebuild index action.
- Modify `README.md` and `MathModelAgentDesign/DESIGN.md`: document M route.

## Task 1: RAG Case Library Service

**Files:**
- Create: `backend/app/services/rag_case_library.py`
- Create: `backend/data/rag_cases/README.md`
- Test: `backend/app/tests/test_rag_case_library.py`

- [ ] **Step 1: Write failing tests**

Tests cover:
- Empty library returns no cases and no error.
- Valid case folder with `problem.pdf`, `paper.pdf`, and optional `data/` returns status `valid`.
- Invalid case folder missing problem or paper returns explicit issues.
- Manifest excludes hidden files and includes file hashes.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_rag_case_library.py -q`

Expected: import failure for `app.services.rag_case_library`.

- [ ] **Step 3: Implement service**

Implement:
- `RagCaseLibrary(root: Path | str)`
- `scan_cases()`
- `validate_case(case_id)`
- `write_manifest()`
- `build_keyword_index()`

Required case structure:
```text
case-id/
  problem.(pdf|md|txt|docx)
  paper.(pdf|md|txt|docx)
  data/                 optional
  notes.md              optional
```

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_rag_case_library.py -q`
Run: `cd backend && uv run ruff check app/services/rag_case_library.py app/tests/test_rag_case_library.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/services/rag_case_library.py backend/app/tests/test_rag_case_library.py backend/data/rag_cases/README.md
git commit -m "feat: add structured rag case library"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 2: RAG Backend API

**Files:**
- Create: `backend/app/routers/rag_router.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_rag_case_library.py`

- [ ] **Step 1: Write failing API tests**

Endpoints:
- `GET /api/gui/rag/cases`
- `POST /api/gui/rag/cases/{case_id}/validate`
- `POST /api/gui/rag/index/rebuild`
- `GET /api/gui/rag/guide`

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_rag_case_library.py -q`

Expected: 404 for RAG API endpoints.

- [ ] **Step 3: Implement router**

Use dependency `get_rag_case_library()` so tests can override root path. Return structured JSON that contains `cases`, `issues`, `manifest_path`, and `index_path`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_rag_case_library.py -q`
Run: `cd backend && uv run ruff check app/routers/rag_router.py app/main.py app/tests/test_rag_case_library.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/routers/rag_router.py backend/app/main.py backend/app/tests/test_rag_case_library.py
git commit -m "feat: add rag case library api"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 3: Studio RAG Panel Integration

**Files:**
- Modify: `frontend/src/apis/guiApi.ts`
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Add frontend API functions**

Add:
- `listRagCases()`
- `validateRagCase(caseId)`
- `rebuildRagIndex()`
- `getRagGuide()`

- [ ] **Step 2: Update RAG panel**

Show:
- guide path and required folder structure
- scan/rebuild buttons
- case list with valid/invalid status
- issues per invalid case

- [ ] **Step 3: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 4: Commit and push**

```bash
git add frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue
git commit -m "feat: show rag case library in studio"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 4: M Route Final Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document RAG library contract**

Document case folder naming, required files, validation behavior, and index rebuild.

- [ ] **Step 2: Verify**

Run:
```bash
cd backend && uv run pytest app/tests/test_rag_case_library.py app/tests/test_gui_config.py app/tests/test_gui_workspace.py app/tests/test_progress_events.py -q
cd ../frontend && pnpm build
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md MathModelAgentDesign/DESIGN.md
git commit -m "docs: describe structured rag case library"
git push fork HEAD:codex-implement-mcm-agent
```

## Self-Review

Spec coverage:
- User-filled empty RAG folder is preserved.
- Required per-case structure is explicit and machine-validated.
- GUI can show cases, issues, and rebuild index status.
- No user papers or data are committed.

Placeholder scan:
- No placeholders remain. Vector embeddings are explicitly deferred; M MVP provides deterministic manifest and keyword index.

Type consistency:
- Backend routes use `/api/gui/rag`.
- Case ids are folder names and are validated as safe path segments.
