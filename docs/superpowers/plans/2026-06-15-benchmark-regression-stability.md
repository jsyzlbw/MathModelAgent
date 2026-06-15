# Benchmark Regression Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable benchmark/regression smoke suite that validates the mature pipeline creates required artifacts and reports clear pass/fail status.

**Architecture:** Create `BenchmarkSuiteService` that builds a temporary benchmark workspace from built-in case text, runs `PipelineService`, checks required artifacts/events, and writes benchmark reports under `benchmarks/`. Add a CLI-like testable service entry and focused tests.

**Tech Stack:** Python pathlib/json/tempfile/datetime, pytest, existing pipeline service.

---

## File Structure

- Create `backend/app/services/benchmark_suite_service.py`: benchmark workspace setup, run, checks, reports.
- Create `backend/app/tests/test_benchmark_suite_service.py`: benchmark service tests.
- Modify `MathModelAgentDesign/DESIGN.md`: document Z route.

## Task 1: Benchmark Suite Service

**Files:**
- Create: `backend/app/services/benchmark_suite_service.py`
- Test: `backend/app/tests/test_benchmark_suite_service.py`

- [ ] **Step 1: Write failing tests**

Cover:
- running benchmark returns status `passed`.
- report includes checks for `res.md`, `paper/claim_plan.json`, `artifact_registry.json`, `review/paper_qa_report.json`, `exports/submission_package.zip`.
- Markdown and JSON reports are written.

- [ ] **Step 2: Verify RED**

Run: `cd backend && uv run pytest app/tests/test_benchmark_suite_service.py -q`

- [ ] **Step 3: Implement service**

Implement:
- `BenchmarkSuiteService(root)`
- `run_smoke()`
- built-in case text: forecast demand and optimize allocation.
- required artifact checks.
- write `benchmarks/latest_report.json` and `.md`.

- [ ] **Step 4: Verify**

Run:

```bash
cd backend && uv run pytest app/tests/test_benchmark_suite_service.py app/tests/test_pipeline_service.py -q
```

## Task 2: Docs, Commit, Push

```bash
git add docs/superpowers/plans/2026-06-15-benchmark-regression-stability.md backend/app/services/benchmark_suite_service.py backend/app/tests/test_benchmark_suite_service.py MathModelAgentDesign/DESIGN.md
git commit -m "feat: add benchmark smoke suite"
git push fork HEAD:codex-implement-mcm-agent
```
