"""File-backed registry for external sources used by a workspace."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SourceRegistryService:
    """Register and list traceable external sources."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.sources_dir = self.workspace / "sources"
        self.registry_path = self.sources_dir / "source_registry.json"
        self.query_log_path = self.sources_dir / "query_log.jsonl"

    def register_source(
        self,
        provider: str,
        source_type: str,
        title: str,
        url: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a source and return the stable source record."""
        registry = self.list_sources()
        record = {
            "source_id": self._source_id(provider, source_type, url, title),
            "provider": provider,
            "source_type": source_type,
            "title": title,
            "url": url,
            "summary": summary,
            "metadata": metadata or {},
            "created_at": self._now(),
        }
        sources = [
            item for item in registry["sources"] if item["source_id"] != record["source_id"]
        ]
        sources.append(record)
        sources.sort(key=lambda item: item["source_id"])
        self._write_registry(sources)
        return record

    def list_sources(self) -> dict[str, Any]:
        """Return all registered sources."""
        if not self.registry_path.exists():
            return {"version": 1, "sources": []}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def append_query_log(
        self,
        provider_type: str,
        provider: str,
        query: str,
        source_ids: list[str],
    ) -> None:
        """Append one provider query log entry."""
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": self._now(),
            "provider_type": provider_type,
            "provider": provider,
            "query": query,
            "source_ids": source_ids,
        }
        with self.query_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _write_registry(self, sources: list[dict[str, Any]]) -> None:
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": self._now(),
                    "sources": sources,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _source_id(provider: str, source_type: str, url: str, title: str) -> str:
        digest = hashlib.sha1(f"{provider}:{source_type}:{url}:{title}".encode()).hexdigest()[:12]
        return f"src-{digest}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
