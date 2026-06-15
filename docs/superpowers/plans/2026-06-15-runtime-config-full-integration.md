# Runtime Config Full Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the ignored JSON runtime config drive LLM roles, provider smoke checks, RAG embedding/rerank settings, academic/data keys, and Studio settings rows without relying on `.env.dev` for core agent behavior.

**Architecture:** Keep `RuntimeConfigStore` as the single file-backed source of truth and add a small typed registry layer that converts JSON nodes into runtime settings for legacy workflow code. Extend the example config and Studio settings form for Voyage embedding/rerank, Semantic Scholar, and official-data providers. Improve provider smoke results so each row reports a stable machine status while never returning raw secrets.

**Tech Stack:** Python pathlib/json/dataclasses, FastAPI, pytest, existing LLM provider classes, Vue 3 Composition API, TypeScript, Vite.

---

## File Structure

- Create `backend/app/config/runtime_registry.py`: typed accessors for LLM role configs, runtime values, OpenAlex, RAG, and provider-key lookup.
- Modify `backend/app/core/llm/llm_factory.py`: build role LLMs from `runtime_registry` first, falling back to `.env.dev` settings.
- Modify `backend/app/core/workflow.py`: read context windows, retry/chat limits, and OpenAlex credentials from `runtime_registry`.
- Modify `backend/app/config/provider_smoke.py`: support `semantic_scholar`, `embedding`, `reranker`, official keyed providers, and clearer error mapping.
- Modify `backend/mcm_agent_config.example.json`: include embedding/rerank provider/key/base URL fields and Semantic Scholar.
- Modify `backend/app/tests/test_gui_config.py`: cover registry fallback, JSON-driven LLM creation, Voyage config masking, and provider smoke rows.
- Modify `frontend/src/pages/studio/index.vue`: add settings rows for embedding, reranker, Semantic Scholar, and no-key official providers.
- Modify `MathModelAgentDesign/DESIGN.md`: document R route completion.

## Task 1: Runtime Registry

**Files:**
- Create: `backend/app/config/runtime_registry.py`
- Modify: `backend/app/tests/test_gui_config.py`

- [ ] **Step 1: Write failing tests**

Add tests proving:

```python
def test_runtime_registry_reads_llm_role_from_json(tmp_path):
    example = tmp_path / "example.json"
    local = tmp_path / "local.json"
    example.write_text('{"llm":{"coordinator":{"api_type":"openai-chat","api_key":"","model":""}}}', encoding="utf-8")
    local.write_text('{"llm":{"coordinator":{"api_key":"sk-local","model":"deepseek","base_url":"https://api.deepseek.com/v1","context_window":64000,"max_tokens":2048}}}', encoding="utf-8")

    registry = RuntimeConfigRegistry(RuntimeConfigStore(example, local))
    role = registry.llm_role("coordinator")

    assert role.api_key == "sk-local"
    assert role.model == "deepseek"
    assert role.context_window == 64000
    assert role.max_tokens == 2048
```

Also cover runtime values and OpenAlex credentials.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`

Expected: import failure for `RuntimeConfigRegistry`.

- [ ] **Step 3: Implement registry**

Implement dataclasses:

```python
@dataclass(frozen=True)
class LLMRoleConfig:
    api_type: ApiType | None
    api_key: str | None
    model: str | None
    base_url: str | None
    context_window: int
    max_tokens: int | None
```

Implement:
- `RuntimeConfigRegistry(store: RuntimeConfigStore | None = None)`
- `llm_role(role, fallback_settings=settings)`
- `runtime_int(name, fallback)`
- `openalex()`
- `rag()`
- `provider_node(path)`
- `get_runtime_registry()`

Rules:
- JSON values win when present and non-empty.
- `.env.dev` settings remain fallback for existing deployments.
- Invalid `api_type` falls back to `openai-chat`.
- Empty strings normalize to `None`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`

## Task 2: Legacy Workflow Uses Runtime JSON

**Files:**
- Modify: `backend/app/core/llm/llm_factory.py`
- Modify: `backend/app/core/workflow.py`
- Modify: `backend/app/tests/test_gui_config.py`

- [ ] **Step 1: Write failing tests**

Add tests that monkeypatch `LLMFactory.registry` or monkeypatch `get_runtime_registry()` so `get_all_llms()` returns LLM instances populated from JSON instead of `settings`.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`

Expected: LLMFactory still uses `settings`, so JSON role values are ignored.

- [ ] **Step 3: Implement integration**

Update `LLMFactory` to accept an optional registry and call `registry.llm_role("coordinator")`, etc.

Update `MathModelWorkFlow.execute()` to use:
- role context windows from registry.
- runtime `max_chat_turns` and `max_retries`.
- OpenAlex email/key from registry.

Retain old `.env.dev` fallback behavior through the registry.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`

## Task 3: Provider Smoke And Config Schema

**Files:**
- Modify: `backend/app/config/provider_smoke.py`
- Modify: `backend/mcm_agent_config.example.json`
- Modify: `backend/app/tests/test_gui_config.py`

- [ ] **Step 1: Write failing tests**

Cover:
- `embedding` returns `missing_config` without provider/key/model.
- `embedding` returns `configured` with Voyage provider/key/model in dry-run mode.
- `reranker` behaves the same.
- `semantic_scholar` checks `academic.semantic_scholar.api_key`.
- official providers with keys use keyed checks; public providers return configured without key.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`

Expected: unknown provider or missing schema for new rows.

- [ ] **Step 3: Implement smoke checks**

Add `embedding` and `reranker` checks under the `rag` node:
- embedding fields: `embedding_provider`, `embedding_model`, `embedding_api_key`, `embedding_base_url`.
- reranker fields: `reranker_provider`, `reranker_model`, `reranker_api_key`, `reranker_base_url`.

Map exceptions to:
- `auth_error`
- `quota_error`
- `network_error`
- `failed`

For now, real Voyage calls are not made in normal tests; dry-run verifies complete config. This keeps tests deterministic while preserving the provider contract.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_gui_config.py -q`

## Task 4: Studio Settings Rows

**Files:**
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Add rows**

Add API setting rows:
- `embedding`
- `reranker`
- `semantic_scholar`
- `world_bank`
- `oecd`
- `undata`
- `nasa_power`
- `open_meteo`
- `overpass`

For no-key providers, omit the secret field and still expose a test button.

- [ ] **Step 2: Verify build**

Run: `cd frontend && pnpm build`

Expected: Vite build succeeds.

## Task 5: Route Verification, Docs, Commit, Push

**Files:**
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document R route**

Add a short section explaining:
- JSON config now drives legacy LLM/workflow behavior.
- Embedding/rerank providers are represented in schema and Studio.
- Provider tests support new rows.

- [ ] **Step 2: Run focused verification**

Run:

```bash
cd backend && uv run pytest app/tests/test_gui_config.py -q
cd frontend && pnpm build
```

- [ ] **Step 3: Commit and push**

```bash
git add docs/superpowers/plans/2026-06-15-runtime-config-full-integration.md backend/app/config/runtime_registry.py backend/app/config/provider_smoke.py backend/app/core/llm/llm_factory.py backend/app/core/workflow.py backend/app/tests/test_gui_config.py backend/mcm_agent_config.example.json frontend/src/pages/studio/index.vue MathModelAgentDesign/DESIGN.md
git commit -m "feat: integrate runtime config across providers"
git push fork HEAD:codex-implement-mcm-agent
```
