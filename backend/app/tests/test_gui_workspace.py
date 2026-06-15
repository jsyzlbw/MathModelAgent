"""GUI workspace API tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_workspace_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    return TestClient(app)


def test_gui_workspace_api_creates_structured_input_dirs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = make_workspace_client(tmp_path, monkeypatch)

    response = client.post("/api/gui/workspaces", json={"title": "MCM test"})

    assert response.status_code == 200
    body = response.json()
    task_id = body["task_id"]
    assert body["status"] == "created"
    assert (tmp_path / "project" / "work_dir" / task_id / "input" / "problem").is_dir()
    assert (
        tmp_path / "project" / "work_dir" / task_id / "input" / "attachments"
    ).is_dir()
    assert (tmp_path / "project" / "work_dir" / task_id / "input" / "template").is_dir()
    assert (
        tmp_path / "project" / "work_dir" / task_id / "input" / "requirements"
    ).is_dir()


def test_gui_workspace_api_uploads_files_by_kind(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = make_workspace_client(tmp_path, monkeypatch)
    task_id = client.post("/api/gui/workspaces", json={"title": "Upload"}).json()[
        "task_id"
    ]

    response = client.post(
        f"/api/gui/workspaces/{task_id}/files",
        params={"kind": "problem"},
        files={"files": ("problem.pdf", b"pdf bytes", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["files"][0]["kind"] == "problem"
    assert body["files"][0]["filename"] == "problem.pdf"
    assert (
        tmp_path
        / "project"
        / "work_dir"
        / task_id
        / "input"
        / "problem"
        / "problem.pdf"
    ).read_bytes() == b"pdf bytes"


def test_gui_workspace_api_rejects_unsafe_task_id_and_filename(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = make_workspace_client(tmp_path, monkeypatch)

    unsafe_task_response = client.get("/api/gui/workspaces/../secret/status")
    assert unsafe_task_response.status_code in {400, 404}

    task_id = client.post("/api/gui/workspaces", json={"title": "Unsafe"}).json()[
        "task_id"
    ]
    upload_response = client.post(
        f"/api/gui/workspaces/{task_id}/files",
        params={"kind": "attachment"},
        files={"files": ("../evil.csv", b"x,y\n1,2", "text/csv")},
    )
    assert upload_response.status_code == 400


def test_gui_artifact_api_lists_and_reads_safe_workspace_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = make_workspace_client(tmp_path, monkeypatch)
    task_id = client.post("/api/gui/workspaces", json={"title": "Artifacts"}).json()[
        "task_id"
    ]
    root = tmp_path / "project" / "work_dir" / task_id
    (root / "res.md").write_text("# Paper\n\ncontent", encoding="utf-8")
    (root / ".hidden").write_text("hidden", encoding="utf-8")

    list_response = client.get(f"/api/gui/workspaces/{task_id}/artifacts")
    assert list_response.status_code == 200
    filenames = {item["path"] for item in list_response.json()["artifacts"]}
    assert "res.md" in filenames
    assert ".hidden" not in filenames

    content_response = client.get(
        f"/api/gui/workspaces/{task_id}/artifacts/content",
        params={"path": "res.md"},
    )
    assert content_response.status_code == 200
    assert content_response.json()["content"] == "# Paper\n\ncontent"

    traversal_response = client.get(
        f"/api/gui/workspaces/{task_id}/artifacts/content",
        params={"path": "../secret.txt"},
    )
    assert traversal_response.status_code == 400


def test_gui_workspace_api_starts_background_run_from_problem_text(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = make_workspace_client(tmp_path, monkeypatch)
    task_id = client.post("/api/gui/workspaces", json={"title": "Run"}).json()[
        "task_id"
    ]
    calls = []

    async def fake_run(task_id, ques_all, comp_template, format_output):
        calls.append(
            {
                "task_id": task_id,
                "ques_all": ques_all,
                "comp_template": comp_template,
                "format_output": format_output,
            }
        )

    monkeypatch.setattr(
        "app.routers.gui_workspace_router.run_modeling_task_async",
        fake_run,
    )

    response = client.post(
        f"/api/gui/workspaces/{task_id}/run",
        json={"problem_text": "Solve this MCM problem.", "mode": "real"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    assert calls[0]["task_id"] == task_id
    assert calls[0]["ques_all"] == "Solve this MCM problem."


@pytest.mark.anyio
async def test_gui_workspace_stop_delegates_to_active_task(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    from app.routers import modeling_router
    from app.routers.gui_workspace_router import stop_workspace_run

    task_id = "run-1"
    event = __import__("asyncio").Event()
    modeling_router._active_tasks[task_id] = (None, event)  # type: ignore[assignment]

    try:
        response = await stop_workspace_run(task_id)
    finally:
        modeling_router._active_tasks.pop(task_id, None)

    assert response.success is True
    assert event.is_set()


def test_gui_workspace_resume_records_event(tmp_path: Path, monkeypatch) -> None:
    client = make_workspace_client(tmp_path, monkeypatch)
    task_id = client.post("/api/gui/workspaces", json={"title": "Resume"}).json()[
        "task_id"
    ]

    response = client.post(
        f"/api/gui/workspaces/{task_id}/resume",
        json={"instruction": "Revise assumptions."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resume_requested"
    events = client.get(f"/api/gui/workspaces/{task_id}/events").json()["events"]
    assert events[-1]["stage"] == "task.resume_requested"
