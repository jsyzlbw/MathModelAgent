"""Render claim-aware MCM/ICM paper drafts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.claim_plan_service import ClaimPlanService


class PaperDraftService:
    """Render `res.md` from a claim plan and workspace artifacts."""

    SECTION_ORDER = [
        "Abstract",
        "Introduction",
        "Assumptions",
        "Model",
        "Results",
        "Limitations",
        "Conclusion",
    ]

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)

    def render(self) -> str:
        """Render and write a claim-aware Markdown draft."""
        claim_plan = ClaimPlanService(self.workspace).load()
        claims_by_section = self._claims_by_section(claim_plan.get("claims", []))
        sections = ["# MathModelAgent Claim-Aware Draft", ""]
        for section in self.SECTION_ORDER:
            sections.extend([f"## {section}", "", self._section_body(section, claims_by_section), ""])
        paper = "\n".join(sections).strip() + "\n"
        (self.workspace / "res.md").write_text(paper, encoding="utf-8")
        return paper

    @staticmethod
    def _claims_by_section(claims: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for claim in claims:
            grouped.setdefault(str(claim.get("section", "Results")), []).append(claim)
        return grouped

    def _section_body(
        self,
        section: str,
        claims_by_section: dict[str, list[dict[str, Any]]],
    ) -> str:
        claims = claims_by_section.get(section, [])
        if section == "Abstract":
            return "We propose a structured modeling workflow with evidence-tracked claims."
        if section == "Introduction":
            return "The problem is addressed through parsed inputs, model selection, solver artifacts, and registered sources."
        if section == "Assumptions":
            return "Assumptions are treated as draft claims until validated by data, solver outputs, or user review."
        if section == "Model":
            return self._claim_lines(claims) or "The selected model is documented in `reports/model_decision.md`."
        if section == "Results":
            return self._claim_lines(claims) or "Results are recorded in `results/results_registry.json`."
        if section == "Limitations":
            return "Numerical conclusions remain provisional until dataset-specific solver code is executed and reviewed."
        if section == "Conclusion":
            return "The generated draft preserves traceability from paper claims back to workspace artifacts."
        return ""

    @staticmethod
    def _claim_lines(claims: list[dict[str, Any]]) -> str:
        return "\n".join(
            (
                f"- [claim:{claim['claim_id']}] {claim['statement']} "
                f"(evidence: `{claim['evidence_path']}`"
                f"{', sources: ' + ', '.join(claim['source_ids']) if claim.get('source_ids') else ''})."
            )
            for claim in claims
        )
