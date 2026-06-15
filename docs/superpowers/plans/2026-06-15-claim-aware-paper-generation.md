# Claim-Aware Paper Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate paper drafts from an explicit claim plan so key statements are tied to artifacts, result records, RAG chunks, or source IDs.

**Architecture:** Add `ClaimPlanService` to build `paper/claim_plan.json` from model decisions, results registry, source registry, and RAG logs. Add `PaperDraftService` to render `res.md` with standard MCM/ICM sections and claim IDs. Integrate the pipeline write stage with these services.

**Tech Stack:** Python pathlib/json/datetime, pytest, existing pipeline artifacts.

---

## File Structure

- Create `backend/app/services/claim_plan_service.py`: build/load claim plan.
- Create `backend/app/services/paper_draft_service.py`: render claim-aware markdown.
- Create `backend/app/tests/test_claim_aware_paper_service.py`: service and pipeline tests.
- Modify `backend/app/services/pipeline_service.py`: use paper draft service in write stage.
- Modify `MathModelAgentDesign/DESIGN.md`: document X route.

## Task 1: Claim Plan And Paper Draft Services

**Files:**
- Create: `backend/app/services/claim_plan_service.py`
- Create: `backend/app/services/paper_draft_service.py`
- Test: `backend/app/tests/test_claim_aware_paper_service.py`

- [ ] **Step 1: Write failing tests**

Cover:
- claim plan contains at least one claim sourced from `results/results_registry.json`.
- paper draft contains Abstract, Introduction, Assumptions, Model, Results, Limitations, Conclusion.
- rendered paper includes claim IDs like `[claim:...]`.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_claim_aware_paper_service.py -q`

- [ ] **Step 3: Implement services**

Claim fields:
- `claim_id`
- `section`
- `statement`
- `evidence_type`
- `evidence_path`
- `source_ids`
- `status`

Paper sections:
- abstract
- introduction
- assumptions
- model
- results
- limitations
- conclusion

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_claim_aware_paper_service.py -q`

## Task 2: Pipeline Integration

**Files:**
- Modify: `backend/app/services/pipeline_service.py`
- Test: `backend/app/tests/test_claim_aware_paper_service.py`

- [ ] **Step 1: Add integration test**

Run pipeline and assert `paper/claim_plan.json` and `res.md` exist and include claim IDs.

- [ ] **Step 2: Implement integration**

Replace generic write stage with `PaperDraftService`.

- [ ] **Step 3: Verify**

Run:

```bash
cd backend && uv run pytest app/tests/test_claim_aware_paper_service.py app/tests/test_pipeline_service.py -q
```

## Task 3: Docs, Commit, Push

```bash
git add docs/superpowers/plans/2026-06-15-claim-aware-paper-generation.md backend/app/services/claim_plan_service.py backend/app/services/paper_draft_service.py backend/app/services/pipeline_service.py backend/app/tests/test_claim_aware_paper_service.py MathModelAgentDesign/DESIGN.md
git commit -m "feat: add claim aware paper generation"
git push fork HEAD:codex-implement-mcm-agent
```
