"""Artifact package service and API tests."""

from pathlib import Path
from zipfile import ZipFile

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
