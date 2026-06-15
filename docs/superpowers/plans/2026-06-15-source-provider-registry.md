# Source Provider Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified source registry and provider facade for web search, academic lookup, and official data discovery so later writing/modeling stages can cite registered sources instead of free-floating facts.

**Architecture:** Create a file-backed `SourceRegistryService` and deterministic `SourceProviderService`. The provider service supports offline-safe query plans for search, academic, and official data providers while preserving provider names/config nodes for real adapters. API endpoints let Studio or pipeline run source discovery and inspect the source registry.

**Tech Stack:** Python pathlib/json/hashlib/datetime, FastAPI, pytest, runtime config registry, Vue 3/TypeScript optional client functions.

---

## File Structure

- Create `backend/app/services/source_registry_service.py`: register/list source records and append query logs.
- Create `backend/app/services/source_provider_service.py`: query provider facade for `search`, `academic`, and `official_data`.
- Create `backend/app/routers/source_router.py`: source query/list API routes.
- Modify `backend/app/main.py`: include source router under `/api/gui`.
- Create `backend/app/tests/test_source_provider_service.py`: service/API tests.
- Modify `frontend/src/apis/guiApi.ts`: source API types/functions.
- Modify `frontend/src/pages/studio/index.vue`: compact source discovery controls in the right-side artifacts/progress area.
- Modify `MathModelAgentDesign/DESIGN.md`: document V route completion.

## Task 1: Source Registry And Provider Service

**Files:**
- Create: `backend/app/services/source_registry_service.py`
- Create: `backend/app/services/source_provider_service.py`
- Test: `backend/app/tests/test_source_provider_service.py`

- [ ] **Step 1: Write failing tests**

Cover:
- registering a source creates stable `source_id` and writes `sources/source_registry.json`.
- querying `academic/openalex` returns registered source records.
- querying `official_data/world_bank` returns a registered source record.
- query log is appended.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_source_provider_service.py -q`

Expected: import failure.

- [ ] **Step 3: Implement services**

Source record fields:
- `source_id`
- `provider`
- `source_type`
- `title`
- `url`
- `summary`
- `metadata`
- `created_at`

Provider facade:
- `query(provider_type, provider, query, limit=5)`
- deterministic offline records for Tavily/Brave/Exa/Firecrawl/OpenAlex/Semantic Scholar/World Bank/FRED/US Census/NOAA/Open-Meteo/Overpass.
- records all query attempts in `sources/query_log.jsonl`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_source_provider_service.py -q`

## Task 2: Source API And GUI Hooks

**Files:**
- Create: `backend/app/routers/source_router.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_source_provider_service.py`
- Modify: `frontend/src/apis/guiApi.ts`
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Write failing API tests**

Endpoints:
- `POST /api/gui/workspaces/{task_id}/sources/query`
- `GET /api/gui/workspaces/{task_id}/sources`

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_source_provider_service.py -q`

Expected: 404.

- [ ] **Step 3: Implement API**

Use workspace-safe root resolution. Return source registry and query result.

- [ ] **Step 4: Add GUI hooks**

Add a compact source discovery row:
- query input
- provider type select via simple text fields
- button
- list latest source IDs/titles

- [ ] **Step 5: Verify**

Run:

```bash
cd backend && uv run pytest app/tests/test_source_provider_service.py -q
cd frontend && pnpm build
```

## Task 3: Docs, Commit, Push

- [ ] **Step 1: Document V route**
- [ ] **Step 2: Commit and push**

```bash
git add docs/superpowers/plans/2026-06-15-source-provider-registry.md backend/app/services/source_registry_service.py backend/app/services/source_provider_service.py backend/app/routers/source_router.py backend/app/tests/test_source_provider_service.py backend/app/main.py frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue MathModelAgentDesign/DESIGN.md
git commit -m "feat: add source provider registry"
git push fork HEAD:codex-implement-mcm-agent
```
