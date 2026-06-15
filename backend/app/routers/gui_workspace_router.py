"""GUI workspace and upload routes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.progress_events import append_progress_event
from app.routers.modeling_router import (
    CancelTaskResponse,
    _active_tasks,
    run_modeling_task_async,
)
from app.schemas.enums import CompTemplate, FormatOutPut
from app.services.input_manifest_service import InputManifestService
from app.services.input_parsing_service import InputParsingService
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


class WorkspaceRunRequest(BaseModel):
    """Start workflow request."""

    problem_text: str = ""
    mode: Literal["demo", "real"] = "real"
    comp_template: CompTemplate = CompTemplate.CHINA
    format_output: FormatOutPut = FormatOutPut.Markdown


class WorkspaceResumeRequest(BaseModel):
    """Resume request for MVP revision loops."""

    instruction: str = ""


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

    manifest = InputManifestService(root).rebuild()

    return {"task_id": safe_task_id, "files": saved_files, "manifest": manifest}


@router.get("/workspaces/{task_id}/inputs")
async def list_workspace_inputs(task_id: str) -> dict:
    """List typed uploaded input manifest items."""
    safe_task_id = _require_safe_task_id(task_id)
    root = _workspace_root(safe_task_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    return {
        "task_id": safe_task_id,
        "manifest": InputManifestService(root).load(),
    }


@router.get("/workspaces/{task_id}/inputs/preview")
async def preview_workspace_input(task_id: str, path: str) -> dict:
    """Preview one uploaded input file by workspace-relative path."""
    safe_task_id = _require_safe_task_id(task_id)
    root = _workspace_root(safe_task_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    try:
        item = InputManifestService(root).preview(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="文件不存在") from exc
    return {"task_id": safe_task_id, "item": item}


@router.post("/workspaces/{task_id}/inputs/parse")
async def parse_workspace_inputs(task_id: str) -> dict:
    """Parse uploaded inputs into normalized agent-readable artifacts."""
    safe_task_id = _require_safe_task_id(task_id)
    root = _workspace_root(safe_task_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    append_progress_event(
        safe_task_id,
        stage="inputs.parse_started",
        message="开始解析工作区输入文件",
        work_dir=root,
    )
    parsed = InputParsingService(root).parse()
    append_progress_event(
        safe_task_id,
        stage="inputs.parse_completed",
        message="输入解析完成",
        level="success",
        metadata={
            "artifact_count": len(parsed.get("artifacts", [])),
            "issue_count": parsed.get("qa", {}).get("issue_count", 0),
        },
        work_dir=root,
    )
    return {"task_id": safe_task_id, **parsed}


@router.get("/workspaces/{task_id}/inputs/parsed")
async def get_workspace_parsed_inputs(task_id: str) -> dict:
    """Return current parsed input manifest."""
    safe_task_id = _require_safe_task_id(task_id)
    root = _workspace_root(safe_task_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    return {"task_id": safe_task_id, **InputParsingService(root).load()}


def _read_problem_text(root: Path) -> str:
    problem_dir = root / "input" / INPUT_DIRS["problem"]
    if not problem_dir.exists():
        return ""
    chunks = []
    for path in sorted(problem_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".txt", ".md", ".tex", ".csv"}:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        else:
            chunks.append(path.read_bytes().decode("utf-8", errors="ignore"))
    return "\n\n".join(chunk for chunk in chunks if chunk.strip())


@router.post("/workspaces/{task_id}/run")
async def start_workspace_run(
    task_id: str,
    request: WorkspaceRunRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """Start the existing modeling workflow from a GUI workspace."""
    safe_task_id = _require_safe_task_id(task_id)
    root = _workspace_root(safe_task_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")

    problem_text = request.problem_text.strip() or _read_problem_text(root)
    if not problem_text:
        raise HTTPException(status_code=400, detail="缺少题目文本或题目文件")

    append_progress_event(
        safe_task_id,
        stage="task.queued",
        message="任务已加入后台队列",
        metadata={"mode": request.mode},
        work_dir=root,
    )
    background_tasks.add_task(
        run_modeling_task_async,
        safe_task_id,
        problem_text,
        request.comp_template,
        request.format_output,
    )
    return {"task_id": safe_task_id, "status": "processing"}


@router.post("/workspaces/{task_id}/stop", response_model=CancelTaskResponse)
async def stop_workspace_run(task_id: str) -> CancelTaskResponse:
    """Stop a running GUI workspace task."""
    safe_task_id = _require_safe_task_id(task_id)
    if safe_task_id not in _active_tasks:
        return CancelTaskResponse(success=False, message="任务不存在或已完成")
    _, cancel_event = _active_tasks[safe_task_id]
    cancel_event.set()
    append_progress_event(
        safe_task_id,
        stage="task.stop_requested",
        message="停止指令已发送",
        level="warning",
    )
    return CancelTaskResponse(success=True, message="停止指令已发送")


@router.post("/workspaces/{task_id}/resume")
async def resume_workspace_run(
    task_id: str,
    request: WorkspaceResumeRequest,
) -> dict:
    """Record a resume request for the GUI revision loop MVP."""
    safe_task_id = _require_safe_task_id(task_id)
    root = _workspace_root(safe_task_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    append_progress_event(
        safe_task_id,
        stage="task.resume_requested",
        message="用户请求继续或修改任务",
        metadata={"instruction": request.instruction},
        work_dir=root,
    )
    return {
        "task_id": safe_task_id,
        "status": "resume_requested",
        "message": "已记录修改意见；完整断点续跑将在交互式规划路线中扩展。",
    }
