"""Modeling strategy and solver template tests."""

from pathlib import Path

from app.services.planning_service import PlanningService


def test_modeling_strategy_detects_prediction_and_optimization(tmp_path: Path) -> None:
    from app.services.modeling_strategy_service import ModelingStrategyService

    service = ModelingStrategyService(tmp_path / "workspace")

    prediction = service.analyze("Forecast demand for the next five years.")
    optimization = service.analyze("Optimize allocation under budget constraints.")

    assert prediction["problem_type"] == "prediction"
    assert any("ARIMA" in item["name"] for item in prediction["candidates"])
    assert optimization["problem_type"] == "optimization"
    assert any("Linear" in item["name"] for item in optimization["candidates"])


def test_solver_template_writes_code_and_results_registry(tmp_path: Path) -> None:
    from app.services.solver_template_service import SolverTemplateService

    workspace = tmp_path / "workspace"
    strategy = {
        "problem_type": "optimization",
        "selected_model": {"name": "Linear Programming"},
        "candidates": [],
    }

    result = SolverTemplateService(workspace).write_solver(strategy)

    assert result["problem_type"] == "optimization"
    assert workspace.joinpath("code", "solver_optimization.py").exists()
    assert workspace.joinpath("results", "results_registry.json").exists()


def test_pipeline_uses_modeling_strategy_and_solver_templates(tmp_path: Path) -> None:
    from app.services.pipeline_service import PipelineService

    workspace = tmp_path / "workspace"
    (workspace / "input" / "problem").mkdir(parents=True)
    (workspace / "input" / "problem" / "problem.txt").write_text(
        "Forecast demand and optimize allocation.",
        encoding="utf-8",
    )
    PlanningService(workspace).create_plan(problem_text="Forecast demand and optimize allocation.")

    PipelineService(workspace, task_id="modeling-pipeline").run()

    assert workspace.joinpath("reports", "model_candidates.json").exists()
    assert workspace.joinpath("code", "solver_prediction.py").exists()
    registry = workspace.joinpath("results", "results_registry.json").read_text(
        encoding="utf-8"
    )
    assert '"problem_type": "prediction"' in registry
