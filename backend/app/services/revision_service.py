"""File-backed chat and revision request service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ChatRole = Literal["user", "agent"]

VALID_ROLES = {"user", "agent"}


class RevisionService:
    """Persist workspace conversation and revision requests."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace)
        self.conversation_dir = self.workspace / "conversation"
        self.review_dir = self.workspace / "review"
        self.messages_path = self.conversation_dir / "messages.jsonl"
        self.revisions_path = self.review_dir / "revision_requests.jsonl"
        self.summary_path = self.review_dir / "revision_summary.md"

    def append_message(
        self,
        role: str,
        content: str,
        attachments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Append one chat message."""
        if role not in VALID_ROLES:
            raise ValueError(f"Unsupported chat role: {role}")
        normalized = content.strip()
        if not normalized:
            raise ValueError("Message content cannot be empty")

        message = {
            "id": self._id("msg"),
            "role": role,
            "content": normalized,
            "attachments": attachments or [],
            "created_at": self._now(),
        }
        self._append_jsonl(self.messages_path, message)
        return message

    def list_messages(self) -> list[dict[str, Any]]:
        """List persisted chat messages in append order."""
        return self._read_jsonl(self.messages_path)

    def append_revision_request(
        self,
        instruction: str,
        target_artifacts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Append one queued revision request."""
        normalized = instruction.strip()
        if not normalized:
            raise ValueError("Revision instruction cannot be empty")

        request = {
            "id": self._id("rev"),
            "instruction": normalized,
            "target_artifacts": target_artifacts or [],
            "status": "queued",
            "created_at": self._now(),
        }
        self._append_jsonl(self.revisions_path, request)
        self._write_summary()
        return request

    def list_revision_requests(self) -> list[dict[str, Any]]:
        """List persisted revision requests in append order."""
        return self._read_jsonl(self.revisions_path)

    def _write_summary(self) -> None:
        requests = self.list_revision_requests()
        lines = ["# Revision Requests", ""]
        if not requests:
            lines.append("No revision requests have been queued.")
        for item in requests:
            lines.extend(
                [
                    f"## {item['id']}",
                    "",
                    f"- Status: {item['status']}",
                    f"- Created at: {item['created_at']}",
                    f"- Target artifacts: {', '.join(item['target_artifacts']) or 'none'}",
                    "",
                    item["instruction"],
                    "",
                ]
            )
        self.review_dir.mkdir(parents=True, exist_ok=True)
        self.summary_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    @staticmethod
    def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    @classmethod
    def _id(cls, prefix: str) -> str:
        return f"{prefix}-{cls._now().replace('-', '').replace(':', '').replace('.', '')}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
