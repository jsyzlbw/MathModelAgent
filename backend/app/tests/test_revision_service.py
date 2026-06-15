"""Chat and revision loop tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.revision_service import RevisionService


def test_revision_service_appends_and_lists_chat_messages(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    service = RevisionService(workspace)

    message = service.append_message(
        role="user",
        content="Please strengthen assumptions.",
    )

    assert message["role"] == "user"
    assert message["content"] == "Please strengthen assumptions."
    assert message["id"].startswith("msg-")
    assert service.list_messages() == [message]


def test_revision_service_appends_revision_and_summary(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    service = RevisionService(workspace)

    request = service.append_revision_request(
        instruction="Revise Problem 2 validation.",
        target_artifacts=["res.md", "figures/q2.svg"],
    )

    assert request["status"] == "queued"
    assert request["target_artifacts"] == ["res.md", "figures/q2.svg"]
    summary = (workspace / "review" / "revision_summary.md").read_text(
        encoding="utf-8",
    )
    assert "Revise Problem 2 validation." in summary


def test_revision_api_persists_chat_and_revision_requests(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    task_id = "revision-task"
    workspace = tmp_path / "project" / "work_dir" / task_id
    workspace.mkdir(parents=True)
    client = TestClient(app)

    message_response = client.post(
        f"/api/gui/workspaces/{task_id}/chat/messages",
        json={"role": "user", "content": "Tighten conclusion."},
    )
    list_response = client.get(f"/api/gui/workspaces/{task_id}/chat/messages")
    revision_response = client.post(
        f"/api/gui/workspaces/{task_id}/revision/requests",
        json={"instruction": "Tighten conclusion.", "target_artifacts": ["res.md"]},
    )

    assert message_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()["messages"][0]["content"] == "Tighten conclusion."
    assert revision_response.status_code == 200
    assert revision_response.json()["request"]["status"] == "queued"


def test_revision_api_rejects_empty_content_and_unsafe_task_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    task_id = "revision-task"
    workspace = tmp_path / "project" / "work_dir" / task_id
    workspace.mkdir(parents=True)
    client = TestClient(app)

    empty_response = client.post(
        f"/api/gui/workspaces/{task_id}/chat/messages",
        json={"role": "user", "content": " "},
    )
    unsafe_response = client.get("/api/gui/workspaces/../secret/chat/messages")

    assert empty_response.status_code == 400
    assert unsafe_response.status_code in {400, 404}
