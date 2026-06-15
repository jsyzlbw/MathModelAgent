"""Interactive planning service tests."""

from pathlib import Path

import pytest

from app.services.planning_service import PlanningService


def test_planning_service_creates_draft_plan(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "input" / "problem").mkdir(parents=True)
    (workspace / "input" / "attachments").mkdir(parents=True)
    (workspace / "input" / "problem" / "problem.txt").write_text(
        "Build a model to forecast demand and optimize allocation.",
        encoding="utf-8",
    )
    (workspace / "input" / "attachments" / "data.csv").write_text(
        "x,y\n1,2",
        encoding="utf-8",
    )

    plan = PlanningService(workspace).create_plan()

    assert plan["status"] == "draft"
    assert "forecast demand" in plan["problem_summary"]
    assert "data.csv" in plan["data_inventory"]
    assert "validation" in " ".join(plan["modeling_steps"]).lower()
    assert (workspace / "planning" / "plan.json").exists()


def test_planning_service_confirm_action_approves_plan(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    service = PlanningService(workspace)
    service.create_plan(problem_text="Classify cities by resilience.")

    plan = service.apply_action("confirm")

    assert plan["status"] == "approved"
    assert plan["last_action"]["action"] == "confirm"


def test_planning_service_edit_action_updates_content(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    service = PlanningService(workspace)
    service.create_plan(problem_text="Optimize routing.")

    plan = service.apply_action(
        "edit",
        content="Use MILP first, then sensitivity analysis.",
    )

    assert plan["status"] == "draft"
    assert plan["user_revision"] == "Use MILP first, then sensitivity analysis."


def test_planning_service_rejects_invalid_action(tmp_path: Path) -> None:
    service = PlanningService(tmp_path / "workspace")
    service.create_plan(problem_text="Analyze risk.")

    with pytest.raises(ValueError, match="Unsupported HIL action"):
        service.apply_action("approve")
