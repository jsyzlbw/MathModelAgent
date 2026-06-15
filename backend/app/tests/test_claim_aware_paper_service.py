"""Claim-aware paper generation tests."""

import json
from pathlib import Path

from app.services.planning_service import PlanningService


def _seed_workspace(workspace: Path) -> None:
    (workspace / "results").mkdir(parents=True)
    (workspace / "reports").mkdir(parents=True)
    (workspace / "sources").mkdir(parents=True)
    (workspace / "results" / "results_registry.json").write_text(
        json.dumps(
            {
                "problem_type": "prediction",
                "selected_model": "Regression Forecasting",
                "claims": [
                    {
                        "claim_id": "prediction-template",
                        "value": "Regression Forecasting solver template generated.",
                        "source": "code/solver_prediction.py",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (workspace / "reports" / "model_decision.md").write_text(
        "# Model Decision\n\nSelected regression forecasting.",
        encoding="utf-8",
    )
    (workspace / "sources" / "source_registry.json").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "src-test",
                        "provider": "openalex",
                        "source_type": "academic",
                        "title": "Forecasting source",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_claim_plan_and_paper_draft_include_evidence(tmp_path: Path) -> None:
    from app.services.claim_plan_service import ClaimPlanService
    from app.services.paper_draft_service import PaperDraftService

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    claim_plan = ClaimPlanService(workspace).build()
    paper = PaperDraftService(workspace).render()

    assert claim_plan["claims"][0]["evidence_path"] == "results/results_registry.json"
    assert claim_plan["claims"][0]["source_ids"] == ["src-test"]
    for heading in [
        "Abstract",
        "Introduction",
        "Assumptions",
        "Model",
        "Results",
        "Limitations",
        "Conclusion",
    ]:
        assert f"## {heading}" in paper
    assert "[claim:" in paper


def test_pipeline_writes_claim_plan_and_claim_aware_draft(tmp_path: Path) -> None:
    from app.services.pipeline_service import PipelineService

    workspace = tmp_path / "workspace"
    (workspace / "input" / "problem").mkdir(parents=True)
    (workspace / "input" / "problem" / "problem.txt").write_text(
        "Forecast demand.",
        encoding="utf-8",
    )
    PlanningService(workspace).create_plan(problem_text="Forecast demand.")

    PipelineService(workspace, task_id="claim-pipeline").run()

    assert workspace.joinpath("paper", "claim_plan.json").exists()
    paper = workspace.joinpath("res.md").read_text(encoding="utf-8")
    assert "## Abstract" in paper
    assert "[claim:" in paper
