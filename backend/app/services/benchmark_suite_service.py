"""Repeatable benchmark smoke suite for pipeline regression checks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.pipeline_service import PipelineService
from app.services.planning_service import PlanningService


REQUIRED_ARTIFACTS = (
    "res.md",
    "paper/claim_plan.json",
    "artifact_registry.json",
    "review/paper_qa_report.json",
    "exports/submission_package.zip",
)


class BenchmarkSuiteService:
    """Run deterministic smoke benchmarks against the plan-driven pipeline."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.benchmarks_dir = self.root / "benchmarks"
        self.workspace = self.benchmarks_dir / "smoke_workspace"
        self.report_json = self.benchmarks_dir / "latest_report.json"
        self.report_md = self.benchmarks_dir / "latest_report.md"

    def run_smoke(self) -> dict[str, Any]:
        """Run the built-in smoke benchmark and write reports."""
        self._prepare_workspace()
        PipelineService(self.workspace, task_id="benchmark-smoke").run()
        checks = [
            {
                "path": path,
                "exists": (self.workspace / path).exists(),
                "status": "passed" if (self.workspace / path).exists() else "failed",
            }
            for path in REQUIRED_ARTIFACTS
        ]
        status = "passed" if all(check["exists"] for check in checks) else "failed"
        report = {
            "version": 1,
            "status": status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "case_id": "smoke_forecast_optimize",
            "workspace": str(self.workspace),
            "checks": checks,
        }
        self._write_reports(report)
        return report

    def _prepare_workspace(self) -> None:
        problem_dir = self.workspace / "input" / "problem"
        attachment_dir = self.workspace / "input" / "attachments"
        problem_dir.mkdir(parents=True, exist_ok=True)
        attachment_dir.mkdir(parents=True, exist_ok=True)
        (problem_dir / "problem.txt").write_text(
            "Forecast demand for a city system and optimize allocation under constraints.",
            encoding="utf-8",
        )
        (attachment_dir / "data.csv").write_text(
            "year,demand,capacity\n2024,100,120\n2025,115,125\n",
            encoding="utf-8",
        )
        PlanningService(self.workspace).create_plan(
            problem_text="Forecast demand for a city system and optimize allocation under constraints."
        )

    def _write_reports(self, report: dict[str, Any]) -> None:
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)
        self.report_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        lines = [
            "# Benchmark Smoke Report",
            "",
            f"- Status: {report['status']}",
            f"- Case: {report['case_id']}",
            "",
            "## Checks",
            "",
        ]
        for check in report["checks"]:
            lines.append(f"- {check['status']}: `{check['path']}`")
        self.report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
