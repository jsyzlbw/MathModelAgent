"""Structured user-filled RAG case library."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.common_utils import TASK_ID_PATTERN

CASE_FILE_SUFFIXES = {".pdf", ".md", ".txt", ".docx"}
TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".tex"}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "using",
    "model",
    "problem",
    "paper",
}


class RagCaseLibrary:
    """Scan, validate, and index a local RAG case folder."""

    def __init__(self, root: Path | str = "data/rag_cases") -> None:
        self.root = Path(root)

    @property
    def manifest_path(self) -> Path:
        return self.root / ".rag_manifest.json"

    @property
    def index_path(self) -> Path:
        return self.root / ".rag_index.json"

    def scan_cases(self) -> list[dict[str, Any]]:
        """Return all visible case folders with validation status."""
        if not self.root.exists():
            return []
        cases = []
        for path in sorted(self.root.iterdir()):
            if path.name.startswith(".") or not path.is_dir():
                continue
            cases.append(self.validate_case(path.name))
        return cases

    def validate_case(self, case_id: str) -> dict[str, Any]:
        """Validate one case folder."""
        safe_case_id = self._require_safe_case_id(case_id)
        case_dir = self.root / safe_case_id
        issues: list[str] = []
        if not case_dir.exists() or not case_dir.is_dir():
            issues.append("case_folder_not_found")
            return self._case_record(safe_case_id, issues, files=[])

        visible_files = self._visible_files(case_dir)
        root_files = [path for path in visible_files if path.parent == case_dir]
        has_problem = any(path.stem.lower() == "problem" for path in root_files)
        has_paper = any(path.stem.lower() == "paper" for path in root_files)
        if not has_problem:
            issues.append("missing_problem_file")
        if not has_paper:
            issues.append("missing_paper_file")

        invalid_required_suffixes = [
            path.name
            for path in root_files
            if path.stem.lower() in {"problem", "paper"}
            and path.suffix.lower() not in CASE_FILE_SUFFIXES
        ]
        if invalid_required_suffixes:
            issues.append("unsupported_required_file_type")

        return self._case_record(
            safe_case_id,
            issues,
            files=[self._file_record(path, case_dir) for path in visible_files],
        )

    def write_manifest(self) -> dict[str, Any]:
        """Write and return the current library manifest."""
        self.root.mkdir(parents=True, exist_ok=True)
        manifest = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "root": str(self.root),
            "cases": self.scan_cases(),
        }
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest

    def build_keyword_index(self) -> dict[str, Any]:
        """Build a lightweight keyword index for deterministic MVP retrieval."""
        self.root.mkdir(parents=True, exist_ok=True)
        cases = []
        for case in self.scan_cases():
            keywords = self._keywords_for_case(case)
            cases.append(
                {
                    "case_id": case["case_id"],
                    "status": case["status"],
                    "keywords": keywords,
                    "issues": case["issues"],
                }
            )
        index = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "case_count": len(cases),
            "cases": cases,
        }
        self.index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return index

    def _case_record(
        self,
        case_id: str,
        issues: list[str],
        files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "status": "valid" if not issues else "invalid",
            "issues": issues,
            "files": files,
        }

    def _visible_files(self, case_dir: Path) -> list[Path]:
        files = []
        for path in sorted(case_dir.rglob("*")):
            if not path.is_file():
                continue
            relative_parts = path.relative_to(case_dir).parts
            if any(part.startswith(".") for part in relative_parts):
                continue
            files.append(path)
        return files

    def _file_record(self, path: Path, case_dir: Path) -> dict[str, Any]:
        return {
            "path": path.relative_to(case_dir).as_posix(),
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def _keywords_for_case(self, case: dict[str, Any]) -> list[str]:
        case_dir = self.root / str(case["case_id"])
        words: Counter[str] = Counter()
        for file_info in case.get("files", []):
            path = case_dir / str(file_info["path"])
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text):
                if word not in STOPWORDS:
                    words[word] += 1
        return [word for word, _ in words.most_common(30)]

    @staticmethod
    def _require_safe_case_id(case_id: str) -> str:
        normalized = (case_id or "").strip()
        if not TASK_ID_PATTERN.fullmatch(normalized):
            raise ValueError("非法 case_id")
        return normalized
