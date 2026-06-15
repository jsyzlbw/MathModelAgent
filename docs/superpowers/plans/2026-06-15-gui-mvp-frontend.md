# GUI MVP Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a usable Vue GUI MVP at `/studio` that lets users configure APIs with per-row connectivity tests, see the empty RAG knowledge-base contract, upload the current modeling task files, discuss a plan with the agent, start/stop/resume runs, watch progress, and inspect artifacts.

**Architecture:** Extend the existing Vue 3 + Tailwind + shadcn-vue frontend. Add a focused GUI API client for the `/api/gui` backend routes from K, then build one product-workbench route composed of small panels. Keep the existing home/chat/task pages intact and add `/studio` as the new productized workflow entry.

**Tech Stack:** Vue 3 Composition API, TypeScript, Axios, Vue Router, Tailwind CSS v3, existing shadcn-vue components, lucide-vue-next icons, Vite build verification.

---

## File Structure

- Create `frontend/src/apis/guiApi.ts`: typed API functions for config, provider tests, workspaces, uploads, run controls, events, and artifacts.
- Create `frontend/src/pages/studio/index.vue`: main workbench layout with Settings, RAG, Upload, Chat/Plan, Progress, and Artifacts panels.
- Modify `frontend/src/router/index.ts`: add `/studio` route.
- Modify `frontend/src/pages/index.vue`: change CTA to open `/studio` so users can discover the new GUI workflow.
- Optionally modify `frontend/src/assets/style.css`: only if minimal page-level polish needs CSS variables or body background.

## Task 1: GUI API Client

**Files:**
- Create: `frontend/src/apis/guiApi.ts`

- [ ] **Step 1: Write TypeScript client code first against backend contract**

Implement exported types and functions:

```ts
export interface GuiConfigResponse { [key: string]: unknown }
export interface ProviderTestRequest { provider: string; config?: Record<string, unknown>; dry_run?: boolean }
export interface ProviderTestResponse { provider: string; ok: boolean; status: string; message: string }
export interface WorkspaceResponse { task_id: string; status: string; title?: string }
export interface ProgressEvent { seq: number; timestamp: string; level: string; stage: string; message: string; metadata: Record<string, unknown> }
```

Functions:
- `getGuiConfig()`
- `saveGuiConfig(config)`
- `testGuiProvider(payload)`
- `createGuiWorkspace(title)`
- `uploadWorkspaceFiles(taskId, kind, files)`
- `runWorkspace(taskId, payload)`
- `stopWorkspace(taskId)`
- `resumeWorkspace(taskId, instruction)`
- `getWorkspaceEvents(taskId, after)`
- `listWorkspaceArtifacts(taskId)`
- `readWorkspaceArtifact(taskId, path)`

- [ ] **Step 2: Verify types/build fail before route imports exist**

Run: `cd frontend && pnpm build`

Expected before page integration: build should still pass if only API file is added. If it fails, fix API types.

- [ ] **Step 3: Commit and push**

```bash
git add frontend/src/apis/guiApi.ts
git commit -m "feat: add gui frontend api client"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 2: Studio Workbench Route Skeleton

**Files:**
- Create: `frontend/src/pages/studio/index.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/pages/index.vue`

- [ ] **Step 1: Implement route shell**

Create a dense, work-focused application screen. First viewport is the tool itself, not a landing page. Use a restrained neutral interface with a dark header strip, compact panels, clear status chips, and no decorative cards-inside-cards.

Layout:
- Header: workspace title, current task id, create workspace button, start/stop buttons.
- Left column: Settings tab and RAG tab.
- Middle column: current task upload area and conversation/plan area.
- Right column: progress timeline and artifacts list.

- [ ] **Step 2: Wire router and CTA**

Add `/studio` route and make existing home CTA push `/studio` instead of `/chat`.

- [ ] **Step 3: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 4: Commit and push**

```bash
git add frontend/src/pages/studio/index.vue frontend/src/router/index.ts frontend/src/pages/index.vue
git commit -m "feat: add gui studio route shell"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 3: Settings Panel with Per-API Test Buttons

**Files:**
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Load and edit config**

On mount call `getGuiConfig()`. Maintain editable state for these rows:
- coordinator
- modeler
- coder
- writer
- tavily
- brave
- exa
- firecrawl
- openalex
- mineru
- humanizer
- fred
- us_census
- noaa

Each row displays label, provider id, relevant fields, masked configured status, and a test button.

- [ ] **Step 2: Implement per-row test button**

Each API row has its own `Test` button that calls `testGuiProvider({ provider, config: draftConfig, dry_run: true })`. The button shows loading while running and then shows success/failure message beside that row. This directly satisfies the user requirement.

- [ ] **Step 3: Implement save button**

Save writes full draft JSON through `saveGuiConfig(draftConfig)` and refreshes masked config. Never render raw secret after save unless the user has just typed it into the input.

- [ ] **Step 4: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/pages/studio/index.vue
git commit -m "feat: add gui settings provider tests"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 4: RAG and Task Upload Panels

**Files:**
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: RAG panel**

Show the expected structure for user-filled RAG cases without uploading yet:
- case folder
- problem statement
- provided data
- solution paper
- notes optional

Also show the backend configured path from `rag.knowledge_base_dir`, defaulting to `data/rag_cases`.

- [ ] **Step 2: Task upload panel**

Implement file inputs grouped by:
- problem
- attachment
- template
- requirement
- chat

When files are selected, call `uploadWorkspaceFiles(currentTaskId, kind, files)` and display uploaded file names.

- [ ] **Step 3: Workspace creation guard**

If no workspace exists, upload buttons are disabled and a create-workspace action is shown.

- [ ] **Step 4: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/pages/studio/index.vue
git commit -m "feat: add gui rag and task uploads"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 5: Chat/Plan, Run Controls, Progress, and Artifacts

**Files:**
- Modify: `frontend/src/pages/studio/index.vue`

- [ ] **Step 1: Chat and plan state**

Add a compact conversation area where users can add messages and a plan editor controlled by the agent/user discussion. MVP stores the conversation locally in the page.

- [ ] **Step 2: Run controls**

Start button calls `runWorkspace(currentTaskId, { problem_text, mode: 'real' })`. Stop calls `stopWorkspace`. Resume sends the latest user revision message via `resumeWorkspace`.

- [ ] **Step 3: Progress polling**

When a workspace exists, poll `getWorkspaceEvents(taskId, after)` every 2 seconds while running and append events. Show a clear timeline so the user sees the agent is working.

- [ ] **Step 4: Artifact list and preview**

Call `listWorkspaceArtifacts`. For text artifacts, call `readWorkspaceArtifact` and render content in a preview panel. For other files, show a download link URL using the backend endpoint path.

- [ ] **Step 5: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 6: Commit and push**

```bash
git add frontend/src/pages/studio/index.vue
git commit -m "feat: add gui run progress and artifacts"
git push fork HEAD:codex-implement-mcm-agent
```

## Task 6: L Route Final Verification and Docs

**Files:**
- Modify: `README.md`
- Modify: `MathModelAgentDesign/DESIGN.md`

- [ ] **Step 1: Document studio usage**

Document `/studio` workflow:
1. configure APIs and test each row
2. prepare empty RAG folder with user cases
3. create workspace
4. upload current problem files
5. discuss plan
6. start run
7. watch progress and review artifacts

- [ ] **Step 2: Verify frontend and focused backend**

Run:
```bash
cd frontend && pnpm build
cd ../backend && uv run pytest app/tests/test_gui_config.py app/tests/test_gui_workspace.py app/tests/test_progress_events.py -q
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md MathModelAgentDesign/DESIGN.md
git commit -m "docs: describe gui studio workflow"
git push fork HEAD:codex-implement-mcm-agent
```

## Self-Review

Spec coverage:
- Settings with per-API test buttons is covered by Task 3.
- Empty user-filled RAG knowledge base is covered by Task 4.
- Multimodal-ready chat area and file upload categories are covered by Tasks 4-5.
- User-visible progress is covered by Task 5.
- Artifact review loop foundation is covered by Task 5.

Placeholder scan:
- No placeholders remain. Local-only chat memory is explicitly scoped as MVP.

Type consistency:
- Endpoint names match K backend routes under `/api/gui`.
- Provider ids match backend `ProviderSmokeTester` ids.
