"""Parse uploaded workspace inputs into agent-readable artifacts."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.input_manifest_service import InputManifestService


TEXT_CATEGORIES = {"text"}
TABLE_CATEGORIES = {"table"}
ASSET_CATEGORIES = {"image", "pdf", "document", "archive", "binary"}


class InputParsingService:
    """Create parsed input artifacts from the workspace input manifest."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.parsed_dir = self.workspace / "input" / "parsed"
        self.tables_dir = self.parsed_dir / "tables"
        self.assets_dir = self.parsed_dir / "assets"
        self.parsed_manifest_path = self.parsed_dir / "parsed_manifest.json"

    def parse(self) -> dict[str, Any]:
        """Parse current inputs and write normalized artifacts."""
        manifest = InputManifestService(self.workspace).load()
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        problem_sections: list[str] = []
        artifacts: list[dict[str, Any]] = []
        assets: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []

        for item in manifest.get("items", []):
            category = str(item.get("category", "binary"))
            relative_path = str(item.get("path", ""))
            source = self.workspace / relative_path
            if category in TEXT_CATEGORIES:
                text = source.read_text(encoding="utf-8", errors="ignore")
                if item.get("kind") == "problem":
                    problem_sections.append(self._problem_section(item, text))
                artifacts.append(self._artifact("text", relative_path, item))
            elif category in TABLE_CATEGORIES:
                copied = self._copy_table(source)
                table_summary = self._table_summary(source)
                if item.get("kind") == "problem":
                    problem_sections.append(self._problem_section(item, table_summary))
                artifacts.append(
                    self._artifact(
                        "table",
                        copied.relative_to(self.workspace).as_posix(),
                        item,
                    )
                )
            elif category in ASSET_CATEGORIES:
                asset = {
                    "source_path": relative_path,
                    "filename": item.get("filename", source.name),
                    "category": category,
                    "size": item.get("size", 0),
                    "sha256": item.get("sha256", ""),
                    "status": "provider_required",
                }
                assets.append(asset)
                problem_sections.append(
                    self._metadata_section(item, "需要文档解析/OCR provider 深度解析。")
                )
                issues.append(
                    {
                        "severity": "warning",
                        "code": "provider_required",
                        "path": relative_path,
                        "message": f"{category} 文件已登记，需要后续文档或视觉 provider 解析。",
                    }
                )

        if not problem_sections:
            issues.append(
                {
                    "severity": "warning",
                    "code": "missing_problem_text",
                    "path": "input/problem",
                    "message": "未解析到可直接读取的题面文本。",
                }
            )

        problem_path = self.parsed_dir / "problem.md"
        problem_path.write_text(
            "\n\n".join(problem_sections).strip() + "\n",
            encoding="utf-8",
        )
        artifacts.append(self._artifact("problem_markdown", "input/parsed/problem.md", {}))

        assets_manifest_path = self.assets_dir / "assets_manifest.json"
        assets_manifest_path.write_text(
            json.dumps({"assets": assets}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        qa = {
            "issue_count": len(issues),
            "issues": issues,
            "report_path": "input/parsed/parse_qa.md",
        }
        self._write_qa_report(qa)

        parsed = {
            "version": 1,
            "status": "parsed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_manifest_path": "input/input_manifest.json",
            "problem_path": "input/parsed/problem.md",
            "artifacts": artifacts,
            "assets": assets,
            "qa": qa,
        }
        self.parsed_manifest_path.write_text(
            json.dumps(parsed, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return parsed

    def load(self) -> dict[str, Any]:
        """Load parsed manifest, parsing when missing."""
        if not self.parsed_manifest_path.exists():
            return self.parse()
        return json.loads(self.parsed_manifest_path.read_text(encoding="utf-8"))

    def _copy_table(self, source: Path) -> Path:
        target = self.tables_dir / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        return target

    @staticmethod
    def _problem_section(item: dict[str, Any], content: str) -> str:
        return f"## {item.get('filename', 'input')}\n\n{content.strip()}"

    @staticmethod
    def _metadata_section(item: dict[str, Any], note: str) -> str:
        return (
            f"## {item.get('filename', 'input')}\n\n"
            f"- path: `{item.get('path', '')}`\n"
            f"- category: `{item.get('category', '')}`\n"
            f"- note: {note}"
        )

    @staticmethod
    def _artifact(kind: str, path: str, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "kind": kind,
            "path": path,
            "source_path": item.get("path", path),
            "status": "ready",
        }

    @staticmethod
    def _table_summary(path: Path) -> str:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as file:
            rows = list(csv.reader(file, delimiter=delimiter))
        if not rows:
            return "Empty table."
        header = rows[0]
        return (
            f"Table `{path.name}` has {max(len(rows) - 1, 0)} data rows and "
            f"{len(header)} columns: {', '.join(header)}."
        )

    def _write_qa_report(self, qa: dict[str, Any]) -> None:
        lines = [
            "# Input Parse QA",
            "",
            f"- Issue count: {qa['issue_count']}",
            "",
        ]
        for issue in qa["issues"]:
            lines.append(
                f"- [{issue['severity']}] {issue['code']} `{issue['path']}`: {issue['message']}"
            )
        if not qa["issues"]:
            lines.append("- No parsing issues detected.")
        (self.parsed_dir / "parse_qa.md").write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
