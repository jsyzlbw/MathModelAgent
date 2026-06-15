"""GUI progress event tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.progress_events import append_progress_event, read_progress_events
from app.main import app


def test_progress_events_append_and_read_after_cursor(tmp_path: Path) -> None:
    task_id = "task-1"
    root = tmp_path / "project" / "work_dir" / task_id
    root.mkdir(parents=True)

    first = append_progress_event(
        task_id,
        stage="start",
        message="started",
        level="info",
        work_dir=root,
    )
    second = append_progress_event(
        task_id,
        stage="finish",
        message="finished",
        level="success",
        work_dir=root,
    )

    assert first["seq"] == 1
    assert second["seq"] == 2
    assert read_progress_events(task_id, after=1, work_dir=root) == [second]


def test_progress_events_endpoint_reads_workspace_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    task_id = client.post("/api/gui/workspaces", json={"title": "Events"}).json()[
        "task_id"
    ]
    root = tmp_path / "project" / "work_dir" / task_id
    append_progress_event(task_id, stage="start", message="started", work_dir=root)
    append_progress_event(task_id, stage="finish", message="finished", work_dir=root)

    response = client.get(f"/api/gui/workspaces/{task_id}/events", params={"after": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["events"][0]["seq"] == 2
    assert body["next_after"] == 2
