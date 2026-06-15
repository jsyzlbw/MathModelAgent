"""GUI workspace API tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


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
