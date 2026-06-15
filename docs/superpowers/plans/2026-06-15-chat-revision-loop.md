# Chat Revision Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the Studio conversation and user revision requests in each workspace so users can review a draft, ask for changes, and the agent can resume from a structured revision queue instead of a page-local message buffer.

**Architecture:** Add a small file-backed revision service under `backend/app/services`. It stores chat messages in `conversation/messages.jsonl`, revision requests in `review/revision_requests.jsonl`, and a readable `review/revision_summary.md`. A FastAPI router exposes chat and revision endpoints under `/api/gui/workspaces/{task_id}` and emits progress events. Studio uses these endpoints for send/modify actions while keeping the current local display as a live cache.

**Tech Stack:** FastAPI, Pydantic, pathlib/json/jsonl, existing `progress_events`, pytest, Vue 3 Composition API, Axios.

---

## File Structure

- Create `backend/app/services/revision_service.py`: append/list chat messages, append/list revision requests, write Markdown summary.
- Create `backend/app/routers/revision_router.py`: chat and revision API routes.
- Modify `backend/app/main.py`: include the revision router under `/api/gui`.
- Create `backend/app/tests/test_revision_service.py`: service and API tests.
- Modify `frontend/src/apis/guiApi.ts`: typed chat/revision API functions.
- Modify `frontend/src/pages/studio/index.vue`: persist messages, load existing messages, submit revision requests, show queued revision status.
- Modify `README.md` and `MathModelAgentDesign/DESIGN.md`: document O route.

## Task 1: Revision Service

**Files:**
- Create: `backend/app/services/revision_service.py`
- Test: `backend/app/tests/test_revision_service.py`

- [ ] **Step 1: Write failing service tests**

Create tests for these behaviors:

```python
def test_revision_service_appends_and_lists_chat_messages(tmp_path):
    workspace = tmp_path / "workspace"
    service = RevisionService(workspace)

    message = service.append_message(role="user", content="Please strengthen assumptions.")

    assert message["role"] == "user"
    assert message["content"] == "Please strengthen assumptions."
    assert message["id"].startswith("msg-")
    assert service.list_messages() == [message]


def test_revision_service_appends_revision_and_summary(tmp_path):
    workspace = tmp_path / "workspace"
    service = RevisionService(workspace)

    request = service.append_revision_request(
        instruction="Revise Problem 2 validation.",
        target_artifacts=["res.md", "figures/q2.svg"],
    )

    assert request["status"] == "queued"
    assert request["target_artifacts"] == ["res.md", "figures/q2.svg"]
    summary = workspace.joinpath("review", "revision_summary.md").read_text(encoding="utf-8")
    assert "Revise Problem 2 validation." in summary
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_revision_service.py -q`

Expected: import failure for `app.services.revision_service`.

- [ ] **Step 3: Implement service**

Implement:

```python
class RevisionService:
    def __init__(self, workspace: Path | str) -> None: ...
    def append_message(self, role: str, content: str, attachments: list[str] | None = None) -> dict[str, Any]: ...
    def list_messages(self) -> list[dict[str, Any]]: ...
    def append_revision_request(self, instruction: str, target_artifacts: list[str] | None = None) -> dict[str, Any]: ...
    def list_revision_requests(self) -> list[dict[str, Any]]: ...
```

Rules:
- Valid roles are `user` and `agent`.
- Empty content is rejected with `ValueError("Message content cannot be empty")`.
- Revision instructions cannot be empty.
- IDs use deterministic prefixes plus UTC timestamp, such as `msg-20260615T120000123456Z`.
- JSONL files are created as needed.
- `revision_summary.md` lists queued requests newest-last.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_revision_service.py -q`
Run: `cd backend && uv run ruff check app/services/revision_service.py app/tests/test_revision_service.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/services/revision_service.py backend/app/tests/test_revision_service.py
git commit -m "feat: add revision loop service"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 2: Chat and Revision Backend API

**Files:**
- Create: `backend/app/routers/revision_router.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_revision_service.py`

- [ ] **Step 1: Write failing API tests**

Add tests for:

```python
def test_revision_api_persists_chat_and_revision_requests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    task_id = "revision-task"
    workspace = tmp_path / "project" / "work_dir" / task_id
    workspace.mkdir(parents=True)
    client = TestClient(app)

    message_response = client.post(
        f"/api/gui/workspaces/{task_id}/chat/messages",
        json={"role": "user", "content": "Tighten conclusion."},
    )
    list_response = client.get(f"/api/gui/workspaces/{task_id}/chat/messages")
    revision_response = client.post(
        f"/api/gui/workspaces/{task_id}/revision/requests",
        json={"instruction": "Tighten conclusion.", "target_artifacts": ["res.md"]},
    )

    assert message_response.status_code == 200
    assert list_response.json()["messages"][0]["content"] == "Tighten conclusion."
    assert revision_response.json()["request"]["status"] == "queued"
```

Also test unsafe task IDs and empty content return 400.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_revision_service.py -q`

Expected: 404 for the new endpoints.

- [ ] **Step 3: Implement router**

Expose:
- `GET /workspaces/{task_id}/chat/messages`
- `POST /workspaces/{task_id}/chat/messages`
- `GET /workspaces/{task_id}/revision/requests`
- `POST /workspaces/{task_id}/revision/requests`

Use safe task ID validation, require existing workspace, convert service `ValueError` to HTTP 400, and append progress events:
- `chat.message_added`
- `revision.request_queued`

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_revision_service.py app/tests/test_progress_events.py -q`
Run: `cd backend && uv run ruff check app/services/revision_service.py app/routers/revision_router.py app/main.py app/tests/test_revision_service.py`

- [ ] **Step 5: Commit and push**

```bash
git add backend/app/routers/revision_router.py backend/app/main.py backend/app/tests/test_revision_service.py
git commit -m "feat: add chat revision api"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 3: Studio Revision Loop Integration

**Files:**
- Modify: `frontend/src/apis/guiApi.ts`
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Add frontend API types and functions**

Add:

```ts
export interface ChatMessageRecord { id: string; role: "user" | "agent"; content: string; attachments: string[]; created_at: string }
export interface RevisionRequestRecord { id: string; instruction: string; target_artifacts: string[]; status: string; created_at: string }
export function listChatMessages(taskId: string) { ... }
export function appendChatMessage(taskId: string, payload: { role: "user" | "agent"; content: string; attachments?: string[] }) { ... }
export function listRevisionRequests(taskId: string) { ... }
export function createRevisionRequest(taskId: string, payload: { instruction: string; target_artifacts?: string[] }) { ... }
```

- [ ] **Step 2: Persist chat send**

Update Studio:
- `LocalMessage` includes optional `id`.
- `sendChatMessage()` ensures a workspace, posts the user message, then posts an agent acknowledgement message.
- After creating a workspace, call `refreshChatMessages()` and `refreshRevisionRequests()`.

- [ ] **Step 3: Persist revision requests**

Update `requestResume()`:
- Ensure workspace.
- Use chat input or plan draft as instruction.
- POST `/revision/requests` with text artifacts from current artifact list when available.
- Keep the existing `/resume` call for compatibility, but the structured revision request is now the primary record.
- Show the newest queued revision in the chat panel.

- [ ] **Step 4: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/apis/guiApi.ts frontend/src/pages/studio/index.vue
git commit -m "feat: persist studio chat revisions"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 4: O Route Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document revision loop**

Document that conversation and revision requests are stored under:
- `conversation/messages.jsonl`
- `review/revision_requests.jsonl`
- `review/revision_summary.md`

- [ ] **Step 2: Verify**

Run:
```bash
cd backend && uv run pytest app/tests/test_revision_service.py app/tests/test_planning_service.py app/tests/test_rag_case_library.py app/tests/test_gui_config.py app/tests/test_gui_workspace.py app/tests/test_progress_events.py -q
cd ../frontend && pnpm build
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md MathModelAgentDesign/DESIGN.md
git commit -m "docs: describe chat revision loop"
git push fork HEAD:codex-implement-mcm-agent
```

## Self-Review

Spec coverage:
- User-agent discussion is persisted instead of page-local only.
- User dissatisfaction after draft review becomes a structured revision request.
- Agent progress visibility is maintained through progress events.
- The workflow remains safe: no secrets or uploaded user files are committed.

Placeholder scan:
- No placeholders remain. Full autonomous re-run from a queued revision remains future workflow work, but the durable contract and API are implemented in this route.

Type consistency:
- Chat roles are `user` and `agent` in backend, frontend, and tests.
- Revision status starts as `queued` in service, API, and UI.
