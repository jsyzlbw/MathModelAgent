"""Formatting and submission QA for generated paper drafts."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = (
    "Abstract",
    "Introduction",
    "Assumptions",
    "Model",
    "Results",
    "Limitations",
    "Conclusion",
)


class PaperQAService:
    """Audit generated drafts for common paper/LaTeX readiness issues."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.review_dir = self.workspace / "review"
        self.report_json_path = self.review_dir / "paper_qa_report.json"
        self.report_md_path = self.review_dir / "paper_qa_report.md"

    def run(self) -> dict[str, Any]:
        """Run QA checks and write JSON/Markdown reports."""
        paper_path = self.workspace / "res.md"
        text = paper_path.read_text(encoding="utf-8", errors="ignore") if paper_path.exists() else ""
        issues: list[dict[str, Any]] = []
        issues.extend(self._section_issues(text))
        issues.extend(self._claim_issues(text))
        issues.extend(self._line_issues(text))
        issues.extend(self._table_issues(text))
        issues.extend(self._formula_issues(text))
        issues.extend(self._tex_engine_issues())

        status = "ok" if not any(issue["severity"] == "error" for issue in issues) else "issues_found"
        report = {
            "version": 1,
            "status": status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "paper_path": "res.md",
            "issues": issues,
            "issue_count": len(issues),
        }
        self._write_reports(report)
        return report

    @staticmethod
    def _section_issues(text: str) -> list[dict[str, Any]]:
        issues = []
        for section in REQUIRED_SECTIONS:
            if f"## {section}" not in text:
                issues.append(
                    {
                        "severity": "error",
                        "code": "missing_section",
                        "message": f"Missing required section: {section}",
                    }
                )
        return issues

    @staticmethod
    def _claim_issues(text: str) -> list[dict[str, Any]]:
        if "[claim:" in text:
            return []
        return [
            {
                "severity": "error",
                "code": "missing_claim_marker",
                "message": "No claim markers found in draft.",
            }
        ]

    @staticmethod
    def _line_issues(text: str) -> list[dict[str, Any]]:
        issues = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            if len(line) > 180:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "long_line",
                        "message": f"Line {line_no} is {len(line)} characters and may overflow.",
                    }
                )
        return issues

    @staticmethod
    def _table_issues(text: str) -> list[dict[str, Any]]:
        issues = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            if line.strip().startswith("|") and line.count("|") > 8:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "wide_table",
                        "message": f"Markdown table on line {line_no} may be too wide.",
                    }
                )
        return issues

    @staticmethod
    def _formula_issues(text: str) -> list[dict[str, Any]]:
        issues = []
        for match in re.finditer(r"\$\$(.*?)\$\$", text, flags=re.DOTALL):
            formula = " ".join(match.group(1).split())
            if len(formula) > 160:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "long_formula",
                        "message": "Display formula may overflow page width.",
                    }
                )
        return issues

    @staticmethod
    def _tex_engine_issues() -> list[dict[str, Any]]:
        if shutil.which("latexmk") or shutil.which("pdflatex"):
            return []
        return [
            {
                "severity": "warning",
                "code": "tex_engine_missing",
                "message": "No latexmk or pdflatex executable found; PDF compile QA skipped.",
            }
        ]

    def _write_reports(self, report: dict[str, Any]) -> None:
        self.review_dir.mkdir(parents=True, exist_ok=True)
        self.report_json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        lines = ["# Paper QA Report", "", f"- Status: {report['status']}", f"- Issues: {report['issue_count']}", ""]
        for issue in report["issues"]:
            lines.append(f"- [{issue['severity']}] {issue['code']}: {issue['message']}")
        if not report["issues"]:
            lines.append("- No issues detected.")
        self.report_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
