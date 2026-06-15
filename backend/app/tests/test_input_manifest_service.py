"""Workspace input manifest tests."""

from pathlib import Path

from app.services.input_manifest_service import InputManifestService


def test_input_manifest_records_file_metadata(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    path = workspace / "input" / "problem" / "problem.txt"
    path.parent.mkdir(parents=True)
    path.write_text("optimize water allocation", encoding="utf-8")

    manifest = InputManifestService(workspace).rebuild()

    item = manifest["items"][0]
    assert item["kind"] == "problem"
    assert item["path"] == "input/problem/problem.txt"
    assert item["category"] == "text"
    assert item["sha256"]
    assert "optimize water" in item["preview"]


def test_input_manifest_records_csv_shape_preview(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    path = workspace / "input" / "attachments" / "data.csv"
    path.parent.mkdir(parents=True)
    path.write_text("city,value\nA,1\nB,2\n", encoding="utf-8")

    preview = InputManifestService(workspace).rebuild()["items"][0]["preview"]

    assert "columns: city, value" in preview
    assert "A, 1" in preview


def test_input_manifest_categorizes_image_by_suffix(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    path = workspace / "input" / "chat_uploads" / "diagram.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\x89PNG\r\n")

    item = InputManifestService(workspace).rebuild()["items"][0]

    assert item["kind"] == "chat"
    assert item["category"] == "image"
    assert item["preview"] == "Image file metadata captured; visual OCR is deferred."
