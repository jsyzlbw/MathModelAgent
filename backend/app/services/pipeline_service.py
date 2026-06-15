"""Plan-driven workspace pipeline with artifact registry."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.core.progress_events import append_progress_event
from app.services.artifact_package_service import ArtifactPackageService
from app.services.input_manifest_service import InputManifestService
from app.services.input_parsing_service import InputParsingService
from app.services.modeling_strategy_service import ModelingStrategyService
from app.services.planning_service import PlanningService
from app.services.rag_vector_index_service import RagVectorIndexService
from app.services.solver_template_service import SolverTemplateService


PipelineStage = Callable[[], list[dict[str, Any]]]


class PipelineService:
    """Run deterministic plan-driven stages for a workspace."""

    STAGES = ("intake", "parse", "rag", "plan", "model", "solve", "write", "qa", "export")

    def __init__(self, workspace: Path | str, task_id: str) -> None:
        self.workspace = Path(workspace)
        self.task_id = task_id
        self.pipeline_dir = self.workspace / "pipeline"
        self.state_path = self.pipeline_dir / "state.json"
        self.registry_path = self.workspace / "artifact_registry.json"
        self.artifacts: list[dict[str, Any]] = []

    def run(self) -> dict[str, Any]:
        """Run all pipeline stages and persist final state."""
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts = self._load_artifact_registry()
        state = self._initial_state()
        self._write_state(state)

        stage_handlers: dict[str, PipelineStage] = {
            "intake": self._stage_intake,
            "parse": self._stage_parse,
            "rag": self._stage_rag,
            "plan": self._stage_plan,
            "model": self._stage_model,
            "solve": self._stage_solve,
            "write": self._stage_write,
            "qa": self._stage_qa,
            "export": self._stage_export,
        }

        try:
            for stage in self.STAGES:
                state["status"] = "running"
                state["current_stage"] = stage
                self._mark_stage(state, stage, "running")
                self._write_state(state)
                append_progress_event(
                    self.task_id,
                    stage="pipeline.stage_started",
                    message=f"Pipeline stage started: {stage}",
                    metadata={"stage": stage},
                    work_dir=self.workspace,
                )

                produced = stage_handlers[stage]()
                for artifact in produced:
                    self._register_artifact(**artifact)
                self._write_artifact_registry()

                self._mark_stage(state, stage, "completed")
                state["updated_at"] = self._now()
                self._write_state(state)
                append_progress_event(
                    self.task_id,
                    stage="pipeline.stage_completed",
                    message=f"Pipeline stage completed: {stage}",
                    level="success",
                    metadata={"stage": stage, "artifact_count": len(produced)},
                    work_dir=self.workspace,
                )
        except Exception as exc:
            state["status"] = "failed"
            state["error"] = str(exc)
            state["updated_at"] = self._now()
            self._write_state(state)
            append_progress_event(
                self.task_id,
                stage="pipeline.failed",
                message=f"Pipeline failed: {str(exc)[:160]}",
                level="error",
                work_dir=self.workspace,
            )
            raise

        state["status"] = "completed"
        state["current_stage"] = None
        state["updated_at"] = self._now()
        self._write_state(state)
        return state

    def load_state(self) -> dict[str, Any]:
        """Load pipeline state, returning idle state when absent."""
        if not self.state_path.exists():
            return self._initial_state(status="not_started")
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _stage_intake(self) -> list[dict[str, Any]]:
        InputManifestService(self.workspace).rebuild()
        return [
            self._artifact_record(
                artifact_id="input_manifest",
                type_="input_manifest",
                path="input/input_manifest.json",
                producer="PipelineIntake",
            )
        ]

    def _stage_parse(self) -> list[dict[str, Any]]:
        InputParsingService(self.workspace).parse()
        return [
            self._artifact_record(
                artifact_id="parsed_problem",
                type_="parsed_problem",
                path="input/parsed/problem.md",
                producer="PipelineParse",
                depends_on=["input_manifest"],
            ),
            self._artifact_record(
                artifact_id="parse_qa",
                type_="parse_qa",
                path="input/parsed/parse_qa.md",
                producer="PipelineParse",
                depends_on=["input_manifest"],
            ),
        ]

    def _stage_rag(self) -> list[dict[str, Any]]:
        report = self.workspace / "reports" / "rag_context.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        try:
            rag_root = Path("data") / "rag_cases"
            result = RagVectorIndexService(rag_root).query("mathematical modeling methods", top_k=3)
            lines = ["# RAG Context", ""]
            for hit in result["hits"]:
                lines.append(f"- `{hit['case_id']}` `{hit['source_path']}` score={hit['score']}: {hit['text'][:240]}")
            if not result["hits"]:
                lines.append("- No RAG hits available.")
        except Exception as exc:
            lines = ["# RAG Context", "", f"- RAG unavailable: {str(exc)[:160]}"]
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return [
            self._artifact_record(
                artifact_id="rag_context",
                type_="rag_context",
                path="reports/rag_context.md",
                producer="PipelineRAG",
                depends_on=["parsed_problem"],
            )
        ]

    def _stage_plan(self) -> list[dict[str, Any]]:
        PlanningService(self.workspace).load_plan()
        return [
            self._artifact_record(
                artifact_id="execution_plan",
                type_="plan",
                path="planning/plan.json",
                producer="PipelinePlan",
                depends_on=["parsed_problem", "rag_context"],
            )
        ]

    def _stage_model(self) -> list[dict[str, Any]]:
        ModelingStrategyService(self.workspace).analyze()
        understanding = self.workspace / "reports" / "problem_understanding.md"
        understanding.write_text(
            "# Problem Understanding\n\n"
            "The pipeline parsed the uploaded task and prepared a plan-driven modeling workflow.\n",
            encoding="utf-8",
        )
        return [
            self._artifact_record(
                artifact_id="problem_understanding",
                type_="problem_understanding_report",
                path="reports/problem_understanding.md",
                producer="PipelineModel",
                depends_on=["execution_plan"],
            ),
            self._artifact_record(
                artifact_id="model_decision",
                type_="model_decision",
                path="reports/model_decision.md",
                producer="PipelineModel",
                depends_on=["execution_plan"],
            ),
            self._artifact_record(
                artifact_id="model_candidates",
                type_="model_candidates",
                path="reports/model_candidates.json",
                producer="PipelineModel",
                depends_on=["execution_plan"],
            ),
        ]

    def _stage_solve(self) -> list[dict[str, Any]]:
        strategy_path = self.workspace / "reports" / "model_candidates.json"
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
        solver = SolverTemplateService(self.workspace).write_solver(strategy)
        return [
            self._artifact_record(
                artifact_id="results_registry",
                type_="results_registry",
                path=solver["results_path"],
                producer="PipelineSolve",
                depends_on=["model_decision"],
            ),
            self._artifact_record(
                artifact_id="solver_code",
                type_="solver_code",
                path=solver["solver_path"],
                producer="PipelineSolve",
                depends_on=["model_decision"],
            ),
        ]

    def _stage_write(self) -> list[dict[str, Any]]:
        path = self.workspace / "res.md"
        path.write_text(
            "# MathModelAgent Draft\n\n"
            "## Abstract\n\n"
            "This draft was generated by the plan-driven pipeline and awaits model-specific expansion.\n\n"
            "## Method\n\n"
            "See `reports/model_decision.md` and `results/results_registry.json` for the current evidence chain.\n",
            encoding="utf-8",
        )
        return [
            self._artifact_record(
                artifact_id="paper_draft",
                type_="paper_markdown",
                path="res.md",
                producer="PipelineWriter",
                depends_on=["results_registry", "model_decision"],
            )
        ]

    def _stage_qa(self) -> list[dict[str, Any]]:
        path = self.workspace / "review" / "reviewer_report.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Reviewer Report\n\n"
            "- Status: draft requires real solver results before final submission.\n"
            "- Evidence chain: artifact registry created.\n",
            encoding="utf-8",
        )
        return [
            self._artifact_record(
                artifact_id="reviewer_report",
                type_="review_report",
                path="review/reviewer_report.md",
                producer="PipelineQA",
                depends_on=["paper_draft"],
            )
        ]

    def _stage_export(self) -> list[dict[str, Any]]:
        package = ArtifactPackageService(self.workspace).create_package()
        return [
            self._artifact_record(
                artifact_id="submission_package",
                type_="submission_package",
                path=package["package_path"],
                producer="PipelineExport",
                depends_on=["paper_draft", "reviewer_report"],
            )
        ]

    def _initial_state(self, status: str = "running") -> dict[str, Any]:
        now = self._now()
        return {
            "version": 1,
            "status": status,
            "current_stage": None,
            "created_at": now,
            "updated_at": now,
            "stages": [{"name": stage, "status": "pending"} for stage in self.STAGES],
        }

    @staticmethod
    def _mark_stage(state: dict[str, Any], stage: str, status: str) -> None:
        for item in state["stages"]:
            if item["name"] == stage:
                item["status"] = status
                item["updated_at"] = PipelineService._now()
                break

    def _register_artifact(
        self,
        artifact_id: str,
        type_: str,
        path: str,
        producer: str,
        depends_on: list[str] | None = None,
    ) -> None:
        self.artifacts = [
            artifact for artifact in self.artifacts if artifact["artifact_id"] != artifact_id
        ]
        self.artifacts.append(
            {
                "artifact_id": artifact_id,
                "type": type_,
                "path": path,
                "producer": producer,
                "depends_on": depends_on or [],
                "status": "ready",
                "created_at": self._now(),
            }
        )

    @staticmethod
    def _artifact_record(
        artifact_id: str,
        type_: str,
        path: str,
        producer: str,
        depends_on: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "artifact_id": artifact_id,
            "type_": type_,
            "path": path,
            "producer": producer,
            "depends_on": depends_on or [],
        }

    def _load_artifact_registry(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return data.get("artifacts", [])

    def _write_artifact_registry(self) -> None:
        self.registry_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": self._now(),
                    "artifacts": self.artifacts,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_state(self, state: dict[str, Any]) -> None:
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
