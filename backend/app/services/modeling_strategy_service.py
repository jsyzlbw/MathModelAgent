"""Deterministic modeling strategy selection for MCM/ICM tasks."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "prediction": [
        {"name": "ARIMA / Exponential Smoothing", "strength": "time-series baseline"},
        {"name": "Regression Forecasting", "strength": "interpretable drivers"},
        {"name": "Gradient Boosting", "strength": "nonlinear tabular patterns"},
    ],
    "optimization": [
        {"name": "Linear Programming", "strength": "resource allocation"},
        {"name": "Integer Programming", "strength": "discrete decisions"},
        {"name": "Multi-objective Optimization", "strength": "trade-off analysis"},
    ],
    "evaluation": [
        {"name": "AHP-TOPSIS", "strength": "multi-criteria ranking"},
        {"name": "Entropy Weight Method", "strength": "data-driven weights"},
    ],
    "classification": [
        {"name": "Logistic Regression", "strength": "interpretable classification"},
        {"name": "Random Forest", "strength": "robust nonlinear classifier"},
    ],
    "network": [
        {"name": "Graph Centrality", "strength": "network importance"},
        {"name": "Shortest Path / Flow", "strength": "routing and capacity"},
    ],
    "simulation": [
        {"name": "Monte Carlo Simulation", "strength": "uncertainty propagation"},
        {"name": "Agent-based Simulation", "strength": "interaction dynamics"},
    ],
    "risk": [
        {"name": "Scenario Analysis", "strength": "stress testing"},
        {"name": "Sensitivity Analysis", "strength": "parameter robustness"},
    ],
    "geospatial": [
        {"name": "Spatial Clustering", "strength": "regional grouping"},
        {"name": "Gravity / Accessibility Model", "strength": "location interaction"},
    ],
    "generic": [
        {"name": "Baseline Regression", "strength": "interpretable baseline"},
        {"name": "Sensitivity Analysis", "strength": "robustness check"},
    ],
}


KEYWORDS = {
    "prediction": ("forecast", "predict", "trend", "time series", "demand"),
    "optimization": ("optimize", "allocation", "minimize", "maximize", "constraint", "budget"),
    "evaluation": ("evaluate", "rank", "score", "index", "criteria"),
    "classification": ("classify", "category", "cluster", "label"),
    "network": ("network", "route", "path", "flow", "graph"),
    "simulation": ("simulate", "simulation", "monte carlo", "scenario"),
    "risk": ("risk", "uncertainty", "resilience", "robust"),
    "geospatial": ("spatial", "geo", "map", "region", "location"),
}


class ModelingStrategyService:
    """Analyze problem text and write model selection artifacts."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.reports_dir = self.workspace / "reports"

    def analyze(self, problem_text: str | None = None) -> dict[str, Any]:
        """Return and persist a deterministic modeling strategy."""
        text = problem_text or self._read_problem_text()
        problem_type = self._detect_type(text)
        candidates = MODEL_LIBRARY[problem_type]
        strategy = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "problem_type": problem_type,
            "type_scores": self._type_scores(text),
            "candidates": candidates,
            "selected_model": candidates[0],
            "selection_reason": (
                f"Selected {candidates[0]['name']} as a practical first model for "
                f"{problem_type} tasks."
            ),
        }
        self._write_strategy(strategy)
        return strategy

    def _write_strategy(self, strategy: dict[str, Any]) -> None:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.reports_dir / "model_candidates.json").write_text(
            json.dumps(strategy, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.reports_dir / "model_decision.md").write_text(
            "# Model Decision\n\n"
            f"- Problem type: `{strategy['problem_type']}`\n"
            f"- Selected model: {strategy['selected_model']['name']}\n"
            f"- Reason: {strategy['selection_reason']}\n",
            encoding="utf-8",
        )

    def _read_problem_text(self) -> str:
        parsed = self.workspace / "input" / "parsed" / "problem.md"
        if parsed.exists():
            return parsed.read_text(encoding="utf-8", errors="ignore")
        problem_dir = self.workspace / "input" / "problem"
        if not problem_dir.exists():
            return ""
        return "\n\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in sorted(problem_dir.iterdir())
            if path.is_file()
        )

    @classmethod
    def _detect_type(cls, text: str) -> str:
        scores = cls._type_scores(text)
        best_type, best_score = max(scores.items(), key=lambda item: item[1])
        return best_type if best_score > 0 else "generic"

    @staticmethod
    def _type_scores(text: str) -> dict[str, int]:
        normalized = text.lower()
        scores: dict[str, int] = {}
        for problem_type, keywords in KEYWORDS.items():
            scores[problem_type] = sum(
                1 for keyword in keywords if re.search(rf"\b{re.escape(keyword)}\b", normalized)
            )
        return scores
