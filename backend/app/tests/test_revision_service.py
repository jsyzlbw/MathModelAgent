"""Chat and revision loop tests."""

from pathlib import Path

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
