"""GUI workspace and upload routes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.utils.common_utils import create_task_id, create_work_dir, ensure_safe_task_id

router = APIRouter(tags=["gui-workspace"])

WorkspaceFileKind = Literal["problem", "attachment", "template", "requirement", "chat"]

INPUT_DIRS: dict[WorkspaceFileKind, str] = {
    "problem": "problem",
    "attachment": "attachments",
    "template": "template",
    "requirement": "requirements",
    "chat": "chat_uploads",
}

SAFE_FILENAME_PATTERN = re.compile(r"^[^/\\:\x00][^/\\\x00]{0,254}$")


class WorkspaceCreateRequest(BaseModel):
    """Create workspace request."""

    title: str = ""


def _workspace_root(task_id: str) -> Path:
    safe_task_id = _require_safe_task_id(task_id)
    return Path("project") / "work_dir" / safe_task_id


def _require_safe_task_id(task_id: str) -> str:
    try:
        return ensure_safe_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="非法任务ID") from exc


def _safe_filename(filename: str | None) -> str:
    value = (filename or "").strip()
    if not value or value in {".", ".."}:
        raise HTTPException(status_code=400, detail="非法文件名")
    if Path(value).name != value or not SAFE_FILENAME_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="非法文件名")
    return value


def _ensure_input_dirs(root: Path) -> None:
    for dirname in INPUT_DIRS.values():
        (root / "input" / dirname).mkdir(parents=True, exist_ok=True)


@router.post("/workspaces")
async def create_workspace(request: WorkspaceCreateRequest) -> dict:
    """Create a GUI workspace for one modeling task."""
    task_id = create_task_id()
    root = Path(create_work_dir(task_id))
    _ensure_input_dirs(root)
    metadata = {
        "task_id": task_id,
        "title": request.title,
        "status": "created",
    }
    (root / "workspace.json").write_text(
        __import__("json").dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


@router.get("/workspaces")
async def list_workspaces() -> dict:
    """List GUI workspaces."""
    base = Path("project") / "work_dir"
    if not base.exists():
        return {"workspaces": []}
    workspaces = []
    for path in sorted(base.iterdir(), reverse=True):
        if path.is_dir():
            workspaces.append({"task_id": path.name, "status": "created"})
    return {"workspaces": workspaces}


@router.get("/workspaces/{task_id}/status")
async def get_workspace_status(task_id: str) -> dict:
    """Return basic workspace status."""
    safe_task_id = _require_safe_task_id(task_id)
    root = _workspace_root(safe_task_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    return {"task_id": safe_task_id, "status": "created", "work_dir": str(root)}


@router.post("/workspaces/{task_id}/files")
async def upload_workspace_files(
    task_id: str,
    kind: WorkspaceFileKind,
    files: list[UploadFile] = File(...),
) -> dict:
    """Upload files into a structured GUI workspace input folder."""
    safe_task_id = _require_safe_task_id(task_id)
    root = _workspace_root(safe_task_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    _ensure_input_dirs(root)

    target_dir = root / "input" / INPUT_DIRS[kind]
    saved_files = []
    for upload in files:
        filename = _safe_filename(upload.filename)
        content = await upload.read()
        target = target_dir / filename
        target.write_bytes(content)
        saved_files.append(
            {
                "kind": kind,
                "filename": filename,
                "path": str(target.relative_to(root)),
                "size": len(content),
            }
        )

    return {"task_id": safe_task_id, "files": saved_files}
