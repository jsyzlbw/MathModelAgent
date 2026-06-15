"""Plan-driven pipeline service tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.planning_service import PlanningService


def test_pipeline_service_runs_stages_and_registers_artifacts(tmp_path: Path) -> None:
    from app.services.pipeline_service import PipelineService

    workspace = tmp_path / "workspace"
    (workspace / "input" / "problem").mkdir(parents=True)
    (workspace / "input" / "problem" / "problem.txt").write_text(
        "Optimize routing.",
        encoding="utf-8",
    )
    PlanningService(workspace).create_plan(problem_text="Optimize routing.")

    result = PipelineService(workspace, task_id="pipe-task").run()

    assert result["status"] == "completed"
    assert workspace.joinpath("pipeline", "state.json").exists()
    assert workspace.joinpath("artifact_registry.json").exists()
    assert workspace.joinpath("reports", "problem_understanding.md").exists()
    assert workspace.joinpath("results", "results_registry.json").exists()
    assert workspace.joinpath("res.md").exists()
    events = workspace.joinpath("progress_events.jsonl").read_text(encoding="utf-8")
    assert "pipeline.stage_completed" in events


def test_pipeline_api_demo_run_and_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    task_id = client.post("/api/gui/workspaces", json={"title": "Pipeline"}).json()[
        "task_id"
    ]
    client.post(
        f"/api/gui/workspaces/{task_id}/files",
        params={"kind": "problem"},
        files={"files": ("problem.txt", b"Optimize allocation", "text/plain")},
    )

    run_response = client.post(
        f"/api/gui/workspaces/{task_id}/run",
        json={"mode": "demo", "problem_text": "Optimize allocation"},
    )
    status_response = client.get(
        f"/api/gui/workspaces/{task_id}/pipeline/status",
    )

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "completed"
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
