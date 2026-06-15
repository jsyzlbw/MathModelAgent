"""GUI progress event and artifact routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.progress_events import read_progress_events
from app.utils.common_utils import ensure_safe_task_id

router = APIRouter(tags=["gui-artifacts"])

TEXT_SUFFIXES = {".txt", ".md", ".tex", ".bib", ".json", ".csv", ".log", ".py"}
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".ipynb_checkpoints"}


def _require_workspace(task_id: str) -> Path:
    try:
        safe_task_id = ensure_safe_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="非法任务ID") from exc
    root = Path("project") / "work_dir" / safe_task_id
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    return root


def _safe_artifact_path(root: Path, relative_path: str) -> Path:
    requested = (root / relative_path).resolve()
    root_resolved = root.resolve()
    if root_resolved != requested and root_resolved not in requested.parents:
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return requested


def _is_visible_artifact(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    if any(part.startswith(".") for part in relative_parts):
        return False
    return not any(part in SKIP_DIRS for part in relative_parts)


@router.get("/workspaces/{task_id}/events")
async def get_workspace_events(task_id: str, after: int = 0) -> dict:
    """Read progress events for a workspace."""
    root = _require_workspace(task_id)
    events = read_progress_events(task_id, after=after, work_dir=root)
    next_after = events[-1]["seq"] if events else after
    return {"task_id": task_id, "events": events, "next_after": next_after}


@router.get("/workspaces/{task_id}/artifacts")
async def list_artifacts(task_id: str) -> dict:
    """List visible files generated in the workspace."""
    root = _require_workspace(task_id)
    artifacts = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not _is_visible_artifact(path, root):
            continue
        relative = path.relative_to(root).as_posix()
        artifacts.append(
            {
                "path": relative,
                "filename": path.name,
                "size": path.stat().st_size,
                "file_type": path.suffix.lstrip(".").lower(),
            }
        )
    return {"task_id": task_id, "artifacts": artifacts}


@router.get("/workspaces/{task_id}/artifacts/content")
async def read_artifact_content(task_id: str, path: str) -> dict:
    """Read a text artifact safely."""
    root = _require_workspace(task_id)
    artifact = _safe_artifact_path(root, path)
    if artifact.suffix.lower() not in TEXT_SUFFIXES:
        raise HTTPException(status_code=415, detail="仅支持文本产物预览")
    return {
        "task_id": task_id,
        "path": artifact.relative_to(root.resolve()).as_posix(),
        "content": artifact.read_text(encoding="utf-8"),
    }


@router.get("/workspaces/{task_id}/artifacts/download")
async def download_artifact(task_id: str, path: str) -> FileResponse:
    """Download one artifact safely."""
    root = _require_workspace(task_id)
    artifact = _safe_artifact_path(root, path)
    return FileResponse(artifact, filename=artifact.name)
