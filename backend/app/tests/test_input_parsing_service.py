"""Workspace input parsing tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.input_manifest_service import InputManifestService


def test_input_parsing_service_writes_problem_markdown_and_table_copy(
    tmp_path: Path,
) -> None:
    from app.services.input_parsing_service import InputParsingService

    workspace = tmp_path / "workspace"
    problem = workspace / "input" / "problem" / "problem.txt"
    table = workspace / "input" / "attachments" / "data.csv"
    problem.parent.mkdir(parents=True)
    table.parent.mkdir(parents=True)
    problem.write_text("Optimize water allocation.", encoding="utf-8")
    table.write_text("city,value\nA,1\n", encoding="utf-8")
    InputManifestService(workspace).rebuild()

    parsed = InputParsingService(workspace).parse()

    assert parsed["status"] == "parsed"
    assert workspace.joinpath("input", "parsed", "problem.md").exists()
    assert workspace.joinpath("input", "parsed", "tables", "data.csv").exists()
    assert parsed["qa"]["issue_count"] == 0
    problem_md = workspace.joinpath("input", "parsed", "problem.md").read_text(
        encoding="utf-8"
    )
    assert "Optimize water allocation." in problem_md


def test_input_parsing_service_records_provider_required_assets(
    tmp_path: Path,
) -> None:
    from app.services.input_parsing_service import InputParsingService

    workspace = tmp_path / "workspace"
    pdf = workspace / "input" / "problem" / "statement.pdf"
    image = workspace / "input" / "chat_uploads" / "diagram.png"
    pdf.parent.mkdir(parents=True)
    image.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")
    image.write_bytes(b"\x89PNG\r\n")

    parsed = InputParsingService(workspace).parse()

    assert parsed["qa"]["issue_count"] == 2
    assert {issue["code"] for issue in parsed["qa"]["issues"]} == {
        "provider_required"
    }
    assets_manifest = workspace.joinpath(
        "input",
        "parsed",
        "assets",
        "assets_manifest.json",
    )
    assert assets_manifest.exists()


def test_input_parsing_api_creates_parsed_artifacts_and_progress_event(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    task_id = client.post("/api/gui/workspaces", json={"title": "Parse"}).json()[
        "task_id"
    ]
    client.post(
        f"/api/gui/workspaces/{task_id}/files",
        params={"kind": "problem"},
        files={"files": ("problem.txt", b"optimize routing", "text/plain")},
    )

    parse_response = client.post(f"/api/gui/workspaces/{task_id}/inputs/parse")
    parsed_response = client.get(f"/api/gui/workspaces/{task_id}/inputs/parsed")

    assert parse_response.status_code == 200
    assert parse_response.json()["status"] == "parsed"
    assert parsed_response.status_code == 200
    assert parsed_response.json()["status"] == "parsed"
    event_log = (
        tmp_path / "project" / "work_dir" / task_id / "progress_events.jsonl"
    ).read_text(encoding="utf-8")
    assert "inputs.parse_completed" in event_log
