"""Interactive planning and HIL state service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

HilAction = Literal["confirm", "edit", "regenerate", "ask", "skip", "abort"]

SUPPORTED_ACTIONS = {"confirm", "edit", "regenerate", "ask", "skip", "abort"}


class PlanningService:
    """Create and update a workspace planning artifact."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.planning_dir = self.workspace / "planning"
        self.plan_path = self.planning_dir / "plan.json"

    def create_plan(self, problem_text: str = "") -> dict[str, Any]:
        """Create a deterministic MVP plan draft."""
        self.planning_dir.mkdir(parents=True, exist_ok=True)
        source_text = problem_text.strip() or self._read_problem_text()
        plan = {
            "version": 1,
            "status": "draft",
            "created_at": self._now(),
            "updated_at": self._now(),
            "problem_summary": self._summarize(source_text),
            "data_inventory": self._data_inventory(),
            "modeling_steps": [
                "Problem understanding and sub-question decomposition",
                "Data inventory, cleaning, and exploratory analysis",
                "Generate candidate models and compare assumptions",
                "Implement solver experiments and collect evidence",
                "Run validation, sensitivity, and robustness checks",
                "Draft paper sections with claim-aware evidence links",
                "Review formatting, limitations, and final submission package",
            ],
            "expected_artifacts": [
                "planning/plan.json",
                "res.md",
                "res.docx",
                "figures/",
                "progress_events.jsonl",
            ],
            "risks": [
                "Input files may omit key data needed for quantitative validation",
                "External API availability may affect data enrichment",
                "Generated models require user review before final submission",
            ],
            "user_revision": "",
            "last_action": None,
        }
        self._write(plan)
        return plan

    def load_plan(self) -> dict[str, Any]:
        """Load current plan, creating an empty draft if needed."""
        if not self.plan_path.exists():
            return self.create_plan()
        return json.loads(self.plan_path.read_text(encoding="utf-8"))

    def apply_action(self, action: str, content: str = "") -> dict[str, Any]:
        """Apply one HIL action to the current plan."""
        if action not in SUPPORTED_ACTIONS:
            raise ValueError(f"Unsupported HIL action: {action}")

        if action == "regenerate":
            plan = self.create_plan(problem_text=content)
        else:
            plan = self.load_plan()

        if action == "confirm":
            plan["status"] = "approved"
        elif action == "edit":
            plan["status"] = "draft"
            plan["user_revision"] = content
        elif action == "ask":
            plan["status"] = "draft"
            plan["user_question"] = content
        elif action == "skip":
            plan["status"] = "skipped"
        elif action == "abort":
            plan["status"] = "aborted"

        plan["updated_at"] = self._now()
        plan["last_action"] = {
            "action": action,
            "content": content,
            "created_at": self._now(),
        }
        self._write(plan)
        return plan

    def _read_problem_text(self) -> str:
        problem_dir = self.workspace / "input" / "problem"
        if not problem_dir.exists():
            return ""
        chunks = []
        for path in sorted(problem_dir.iterdir()):
            if path.is_file():
                chunks.append(path.read_bytes().decode("utf-8", errors="ignore"))
        return "\n\n".join(chunk for chunk in chunks if chunk.strip())

    def _data_inventory(self) -> list[str]:
        attachment_dir = self.workspace / "input" / "attachments"
        if not attachment_dir.exists():
            return []
        return sorted(path.name for path in attachment_dir.iterdir() if path.is_file())

    @staticmethod
    def _summarize(text: str) -> str:
        normalized = " ".join(text.split())
        if not normalized:
            return "No problem statement has been provided yet."
        return normalized[:500]

    def _write(self, plan: dict[str, Any]) -> None:
        self.planning_dir.mkdir(parents=True, exist_ok=True)
        self.plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
