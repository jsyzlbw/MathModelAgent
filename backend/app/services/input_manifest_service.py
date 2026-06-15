"""Workspace input manifest and lightweight preview service."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INPUT_DIRS = {
    "problem": "problem",
    "attachment": "attachments",
    "template": "template",
    "requirement": "requirements",
    "chat": "chat_uploads",
}

TEXT_SUFFIXES = {".txt", ".md", ".tex", ".bib", ".json", ".log"}
TABLE_SUFFIXES = {".csv", ".tsv"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".svg"}
PDF_SUFFIXES = {".pdf"}
DOCUMENT_SUFFIXES = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}
ARCHIVE_SUFFIXES = {".zip", ".tar", ".gz", ".7z", ".rar"}


class InputManifestService:
    """Build and read a typed inventory of uploaded workspace inputs."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.input_dir = self.workspace / "input"
        self.manifest_path = self.input_dir / "input_manifest.json"

    def rebuild(self) -> dict[str, Any]:
        """Scan workspace input folders and write the manifest."""
        items = []
        for kind, dirname in INPUT_DIRS.items():
            root = self.input_dir / dirname
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file() and not any(part.startswith(".") for part in path.parts):
                    items.append(self._item_for_path(kind, path))

        manifest = {
            "version": 1,
            "generated_at": self._now(),
            "items": items,
        }
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest

    def load(self) -> dict[str, Any]:
        """Load current manifest, rebuilding when missing."""
        if not self.manifest_path.exists():
            return self.rebuild()
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def preview(self, relative_path: str) -> dict[str, Any]:
        """Return preview metadata for one workspace-relative input path."""
        path = self._safe_path(relative_path)
        kind = self._kind_for_path(path)
        return self._item_for_path(kind, path)

    def _item_for_path(self, kind: str, path: Path) -> dict[str, Any]:
        suffix = path.suffix.lower()
        category = self._category_for_suffix(suffix)
        return {
            "kind": kind,
            "path": path.resolve().relative_to(self.workspace.resolve()).as_posix(),
            "filename": path.name,
            "suffix": suffix,
            "category": category,
            "size": path.stat().st_size,
            "sha256": self._sha256(path),
            "preview": self._preview_for_path(path, category),
        }

    def _safe_path(self, relative_path: str) -> Path:
        requested = (self.workspace / relative_path).resolve()
        workspace_resolved = self.workspace.resolve()
        if workspace_resolved != requested and workspace_resolved not in requested.parents:
            raise ValueError("Input path escapes workspace")
        if not requested.exists() or not requested.is_file():
            raise FileNotFoundError(relative_path)
        if self.input_dir.resolve() not in requested.parents:
            raise ValueError("Input path is not under input directory")
        return requested

    def _kind_for_path(self, path: Path) -> str:
        try:
            dirname = path.relative_to(self.input_dir).parts[0]
        except (IndexError, ValueError):
            return "attachment"
        for kind, input_dirname in INPUT_DIRS.items():
            if dirname == input_dirname:
                return kind
        return "attachment"

    @staticmethod
    def _category_for_suffix(suffix: str) -> str:
        if suffix in TEXT_SUFFIXES:
            return "text"
        if suffix in TABLE_SUFFIXES:
            return "table"
        if suffix in IMAGE_SUFFIXES:
            return "image"
        if suffix in PDF_SUFFIXES:
            return "pdf"
        if suffix in DOCUMENT_SUFFIXES:
            return "document"
        if suffix in ARCHIVE_SUFFIXES:
            return "archive"
        return "binary"

    @staticmethod
    def _preview_for_path(path: Path, category: str) -> str:
        if category == "text":
            return path.read_text(encoding="utf-8", errors="ignore")[:2000]
        if category == "table":
            return InputManifestService._table_preview(path)
        if category == "image":
            return "Image file metadata captured; visual OCR is deferred."
        if category == "pdf":
            return "PDF metadata captured; text extraction is deferred to document providers."
        if category == "document":
            return "Document metadata captured; parsing is deferred to document providers."
        if category == "archive":
            return "Archive metadata captured; extraction is deferred."
        return "Binary file metadata captured."

    @staticmethod
    def _table_preview(path: Path) -> str:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        rows = []
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as file:
            reader = csv.reader(file, delimiter=delimiter)
            for index, row in enumerate(reader):
                if index > 5:
                    break
                rows.append(row)
        if not rows:
            return "Empty table file."
        header = rows[0]
        body = rows[1:6]
        lines = [f"columns: {', '.join(header)}", "rows:"]
        lines.extend(", ".join(row) for row in body)
        return "\n".join(lines)

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
