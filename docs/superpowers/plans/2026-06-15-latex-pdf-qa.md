# LaTeX PDF QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a formatting and submission QA layer that audits paper drafts for section completeness, claim markers, long-line/table/formula risks, and LaTeX/PDF readiness.

**Architecture:** Create `PaperQAService` that reads `res.md`, optional `.tex` files, and artifact registry, then writes `review/paper_qa_report.json` and `review/paper_qa_report.md`. Integrate the pipeline QA stage with this service.

**Tech Stack:** Python pathlib/json/re/shutil, pytest, existing pipeline service.

---

## File Structure

- Create `backend/app/services/paper_qa_service.py`: QA checks and reports.
- Create `backend/app/tests/test_paper_qa_service.py`: service and pipeline tests.
- Modify `backend/app/services/pipeline_service.py`: call QA service in `qa` stage.
- Modify `MathModelAgentDesign/DESIGN.md`: document Y route.

## Task 1: Paper QA Service

**Files:**
- Create: `backend/app/services/paper_qa_service.py`
- Test: `backend/app/tests/test_paper_qa_service.py`

- [ ] **Step 1: Write failing tests**

Cover:
- complete claim-aware `res.md` produces `ok` or warnings only.
- missing required section creates issue.
- overly long line creates overflow risk.
- report JSON/Markdown written.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_paper_qa_service.py -q`

- [ ] **Step 3: Implement service**

Checks:
- required sections exist.
- at least one `[claim:` marker exists.
- lines over 180 characters warning.
- Markdown tables with many columns warning.
- display formulas longer than 160 chars warning.
- TeX engine availability via `shutil.which("latexmk") or shutil.which("pdflatex")`.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && uv run pytest app/tests/test_paper_qa_service.py -q`

## Task 2: Pipeline Integration

Modify pipeline QA stage to call `PaperQAService` and register both QA reports.

Run:

```bash
cd backend && uv run pytest app/tests/test_paper_qa_service.py app/tests/test_pipeline_service.py -q
```

## Task 3: Docs, Commit, Push

```bash
git add docs/superpowers/plans/2026-06-15-latex-pdf-qa.md backend/app/services/paper_qa_service.py backend/app/services/pipeline_service.py backend/app/tests/test_paper_qa_service.py MathModelAgentDesign/DESIGN.md
git commit -m "feat: add paper formatting qa"
git push fork HEAD:codex-implement-mcm-agent
```
