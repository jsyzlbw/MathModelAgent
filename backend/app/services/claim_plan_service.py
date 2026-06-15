"""Build claim plans that tie paper statements to evidence artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ClaimPlanService:
    """Create `paper/claim_plan.json` from workspace evidence artifacts."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.paper_dir = self.workspace / "paper"
        self.claim_plan_path = self.paper_dir / "claim_plan.json"

    def build(self) -> dict[str, Any]:
        """Build and persist a claim plan."""
        results = self._read_json("results/results_registry.json")
        source_ids = self._source_ids()
        result_claims = results.get("claims", []) if isinstance(results, dict) else []
        claims = []
        if result_claims:
            for index, claim in enumerate(result_claims, start=1):
                claims.append(
                    {
                        "claim_id": str(claim.get("claim_id") or f"result-claim-{index}"),
                        "section": "Results",
                        "statement": str(claim.get("value") or "A model result is available."),
                        "evidence_type": "result",
                        "evidence_path": "results/results_registry.json",
                        "source_ids": source_ids,
                        "status": "supported",
                    }
                )
        else:
            claims.append(
                {
                    "claim_id": "pipeline-draft-claim",
                    "section": "Model",
                    "statement": "The pipeline generated a modeling strategy draft.",
                    "evidence_type": "artifact",
                    "evidence_path": "reports/model_decision.md",
                    "source_ids": source_ids,
                    "status": "draft",
                }
            )

        plan = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "claims": claims,
        }
        self.paper_dir.mkdir(parents=True, exist_ok=True)
        self.claim_plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return plan

    def load(self) -> dict[str, Any]:
        """Load existing claim plan, building when absent."""
        if not self.claim_plan_path.exists():
            return self.build()
        return json.loads(self.claim_plan_path.read_text(encoding="utf-8"))

    def _source_ids(self) -> list[str]:
        registry = self._read_json("sources/source_registry.json")
        return [str(source["source_id"]) for source in registry.get("sources", [])]

    def _read_json(self, relative_path: str) -> dict[str, Any]:
        path = self.workspace / relative_path
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
