"""Artifact package service and API tests."""

from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app
from app.services.artifact_package_service import ArtifactPackageService


def test_artifact_package_service_creates_manifest_and_zip(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "res.md").write_text("# Paper", encoding="utf-8")
    (workspace / "figures").mkdir()
    (workspace / "figures" / "q1.svg").write_text("<svg />", encoding="utf-8")
    (workspace / ".secret").write_text("skip", encoding="utf-8")

    package = ArtifactPackageService(workspace).create_package()

    assert package["package_path"] == "exports/submission_package.zip"
    assert package["artifact_count"] == 2
    assert (workspace / "exports" / "artifact_manifest.json").exists()
    package_path = workspace / "exports" / "submission_package.zip"
    assert package_path.exists()
    with ZipFile(package_path) as archive:
        names = set(archive.namelist())
    assert "res.md" in names
    assert "figures/q1.svg" in names
    assert ".secret" not in names


def test_artifact_package_service_excludes_previous_exports(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "exports").mkdir(parents=True)
    (workspace / "res.pdf").write_bytes(b"%PDF")
    (workspace / "exports" / "submission_package.zip").write_bytes(b"old")

    package = ArtifactPackageService(workspace).create_package()

    paths = {artifact["path"] for artifact in package["artifacts"]}
    assert "res.pdf" in paths
    assert "exports/submission_package.zip" not in paths


def test_artifact_package_api_creates_and_downloads_package(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    task_id = client.post("/api/gui/workspaces", json={"title": "Package"}).json()[
        "task_id"
    ]
    root = tmp_path / "project" / "work_dir" / task_id
    (root / "res.md").write_text("# Paper", encoding="utf-8")

    package_response = client.post(
        f"/api/gui/workspaces/{task_id}/artifacts/package",
    )
    download_response = client.get(
        f"/api/gui/workspaces/{task_id}/artifacts/package/download",
    )

    assert package_response.status_code == 200
    assert package_response.json()["artifact_count"] == 1
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/zip"


def test_artifact_package_download_missing_returns_404(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    task_id = client.post("/api/gui/workspaces", json={"title": "Package"}).json()[
        "task_id"
    ]

    response = client.get(f"/api/gui/workspaces/{task_id}/artifacts/package/download")

    assert response.status_code == 404
