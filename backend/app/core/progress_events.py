"""File-backed progress events for GUI visibility."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.utils.common_utils import ensure_safe_task_id

ProgressLevel = Literal["info", "warning", "success", "error"]


def _event_file(task_id: str, work_dir: Path | str | None = None) -> Path:
    safe_task_id = ensure_safe_task_id(task_id)
    root = Path(work_dir) if work_dir is not None else Path("project") / "work_dir" / safe_task_id
    return root / "progress_events.jsonl"


def read_progress_events(
    task_id: str,
    after: int = 0,
    work_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Read progress events after a sequence cursor."""
    path = _event_file(task_id, work_dir=work_dir)
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if int(event.get("seq", 0)) > after:
            events.append(event)
    return events


def append_progress_event(
    task_id: str,
    stage: str,
    message: str,
    level: ProgressLevel = "info",
    metadata: dict[str, Any] | None = None,
    work_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Append one progress event to the task JSONL log."""
    path = _event_file(task_id, work_dir=work_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    last_seq = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last_seq = max(last_seq, int(json.loads(line).get("seq", 0)))

    event = {
        "seq": last_seq + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "stage": stage,
        "message": message,
        "metadata": metadata or {},
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event
