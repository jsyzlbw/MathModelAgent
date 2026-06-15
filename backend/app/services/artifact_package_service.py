"""Build audited downloadable packages from workspace artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".ipynb_checkpoints"}
ALLOWED_SUFFIXES = {
    ".pdf",
    ".docx",
    ".md",
    ".tex",
    ".bib",
    ".json",
    ".csv",
    ".txt",
    ".log",
    ".py",
    ".ipynb",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


class ArtifactPackageService:
    """Create an artifact manifest and submission zip for one workspace."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.exports_dir = self.workspace / "exports"
        self.manifest_path = self.exports_dir / "artifact_manifest.json"
        self.package_path = self.exports_dir / "submission_package.zip"

    def build_manifest(self) -> dict[str, Any]:
        """Build and write an artifact manifest."""
        artifacts = [self._artifact_for_path(path) for path in self._iter_artifacts()]
        artifacts.sort(key=lambda item: (item["priority"], item["path"]))
        manifest = {
            "version": 1,
            "generated_at": self._now(),
            "artifacts": artifacts,
        }
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest

    def create_package(self) -> dict[str, Any]:
        """Create the submission package zip and return metadata."""
        manifest = self.build_manifest()
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(self.package_path, "w", compression=ZIP_DEFLATED) as archive:
            for artifact in manifest["artifacts"]:
                archive.write(self.workspace / artifact["path"], artifact["path"])
            archive.write(
                self.manifest_path,
                self.manifest_path.relative_to(self.workspace).as_posix(),
            )
        return {
            "package_path": self.package_path.relative_to(self.workspace).as_posix(),
            "manifest_path": self.manifest_path.relative_to(self.workspace).as_posix(),
            "artifact_count": len(manifest["artifacts"]),
            "size": self.package_path.stat().st_size,
            "artifacts": manifest["artifacts"],
        }

    def _iter_artifacts(self) -> list[Path]:
        if not self.workspace.exists():
            return []
        paths = []
        for path in self.workspace.rglob("*"):
            if not path.is_file() or not self._is_visible_artifact(path):
                continue
            if path == self.package_path:
                continue
            if path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            paths.append(path)
        return paths

    def _is_visible_artifact(self, path: Path) -> bool:
        relative_parts = path.relative_to(self.workspace).parts
        if any(part.startswith(".") for part in relative_parts):
            return False
        return not any(part in SKIP_DIRS for part in relative_parts)

    def _artifact_for_path(self, path: Path) -> dict[str, Any]:
        relative = path.relative_to(self.workspace).as_posix()
        return {
            "path": relative,
            "filename": path.name,
            "size": path.stat().st_size,
            "file_type": path.suffix.lstrip(".").lower(),
            "sha256": self._sha256(path),
            "priority": self._priority(relative),
        }

    @staticmethod
    def _priority(relative_path: str) -> int:
        name = Path(relative_path).name.lower()
        suffix = Path(relative_path).suffix.lower()
        if name in {"res.pdf", "main.pdf", "paper.pdf"}:
            return 0
        if name in {"res.docx", "main.docx", "paper.docx"}:
            return 1
        if name in {"res.md", "main.tex"} or suffix == ".tex":
            return 2
        if relative_path.startswith("figures/") or suffix in {".svg", ".png", ".jpg", ".jpeg"}:
            return 3
        if suffix in {".csv", ".json"}:
            return 4
        return 5

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
