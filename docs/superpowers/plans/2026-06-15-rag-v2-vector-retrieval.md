# RAG V2 Vector Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the structured RAG case library from keyword-only indexing to chunked retrieval with embedding/rerank-ready metadata, retrieval logs, and Studio visibility.

**Architecture:** Add a local `RagVectorIndexService` that chunks text-like case files, creates deterministic hash embeddings as an offline fallback, stores `.rag_chunks.jsonl` and `.rag_vectors.jsonl`, and retrieves ranked chunks with case/source traceability. Keep Voyage configuration in runtime JSON for future online embedding calls, but make the local index deterministic so tests and offline usage remain reliable.

**Tech Stack:** Python pathlib/json/hashlib/math/re, FastAPI, pytest, existing `RagCaseLibrary`, Vue 3, TypeScript, Vite.

---

## File Structure

- Create `backend/app/services/rag_vector_index_service.py`: chunking, hash embeddings, retrieval, and retrieval logging.
- Modify `backend/app/routers/rag_router.py`: add vector rebuild and query endpoints.
- Create `backend/app/tests/test_rag_vector_index_service.py`: service/API tests.
- Modify `frontend/src/apis/guiApi.ts`: vector RAG response types and functions.
- Modify `frontend/src/pages/studio/index.vue`: query input, rebuild vector index, show retrieval hits.
- Modify `MathModelAgentDesign/DESIGN.md`: document T route completion.

## Task 1: Vector Index Service

**Files:**
- Create: `backend/app/services/rag_vector_index_service.py`
- Test: `backend/app/tests/test_rag_vector_index_service.py`

- [ ] **Step 1: Write failing tests**

Cover:

```python
def test_rag_vector_index_builds_chunks_and_retrieves(tmp_path):
    case_dir = tmp_path / "rag_cases" / "case-water"
    case_dir.mkdir(parents=True)
    (case_dir / "problem.md").write_text("Optimize water allocation.", encoding="utf-8")
    (case_dir / "paper.md").write_text("Linear programming model for water allocation.", encoding="utf-8")

    service = RagVectorIndexService(tmp_path / "rag_cases")
    index = service.rebuild()
    hits = service.query("water programming", top_k=2)

    assert index["chunk_count"] >= 2
    assert hits["hits"][0]["case_id"] == "case-water"
    assert hits["hits"][0]["chunk_id"]
    assert hits["hits"][0]["source_path"] in {"problem.md", "paper.md"}
```

Also assert retrieval log is written.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_rag_vector_index_service.py -q`

Expected: import failure.

- [ ] **Step 3: Implement service**

Implement:
- `RagVectorIndexService(root)`
- `rebuild()`
- `query(query_text, top_k=5, filters=None)`

Rules:
- Only chunk valid cases from `RagCaseLibrary.scan_cases()`.
- Read `.md`, `.txt`, `.csv`, `.json`, `.tex`.
- Chunk by paragraph, capped to 1200 chars.
- Create deterministic 64-dimensional hash embeddings.
- Score by cosine similarity plus a small lexical overlap bonus.
- Write `.rag_chunks.jsonl`, `.rag_vectors.jsonl`, `.rag_retrieval_log.jsonl`.
- Every hit includes `case_id`, `chunk_id`, `source_path`, `score`, `text`, and `metadata`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_rag_vector_index_service.py -q`

## Task 2: RAG API And Studio UI

**Files:**
- Modify: `backend/app/routers/rag_router.py`
- Test: `backend/app/tests/test_rag_vector_index_service.py`
- Modify: `frontend/src/apis/guiApi.ts`
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Write failing API tests**

Endpoints:
- `POST /api/gui/rag/vector/rebuild`
- `POST /api/gui/rag/query`

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_rag_vector_index_service.py -q`

Expected: 404 for new endpoints.

- [ ] **Step 3: Implement API**

Use `get_rag_case_library()` dependency to share root override in tests. Return paths/counts for rebuild and ranked hits for query.

- [ ] **Step 4: Implement Studio UI**

Add:
- Query text input in RAG tab.
- “向量索引” rebuild button.
- “检索” button.
- Compact list of hits with case_id, source_path, score, text snippet.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
cd backend && uv run pytest app/tests/test_rag_vector_index_service.py app/tests/test_rag_case_library.py -q
cd frontend && pnpm build
```

## Task 3: Docs, Commit, Push

**Files:**
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document T route**

Describe chunk index, deterministic embedding fallback, retrieval logs, and citation traceability.

- [ ] **Step 2: Commit and push**

```bash
git add docs/superpowers/plans/2026-06-15-rag-v2-vector-retrieval.md backend/app/services/rag_vector_index_service.py backend/app/routers/rag_router.py backend/app/tests/test_rag_vector_index_service.py frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue MathModelAgentDesign/DESIGN.md
git commit -m "feat: add rag vector retrieval"
git push fork HEAD:codex-implement-mcm-agent
```
