"""GUI chat and revision loop routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.progress_events import append_progress_event
from app.services.revision_service import RevisionService
from app.utils.common_utils import ensure_safe_task_id

router = APIRouter(tags=["gui-revision"])


class ChatMessageRequest(BaseModel):
    """Persist one Studio chat message."""

    role: str
    content: str
    attachments: list[str] = []


class RevisionRequestCreate(BaseModel):
    """Queue one user revision request."""

    instruction: str
    target_artifacts: list[str] = []


def _workspace_root(task_id: str) -> tuple[str, Path]:
    try:
        safe_task_id = ensure_safe_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="非法任务ID") from exc
    root = Path("project") / "work_dir" / safe_task_id
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    return safe_task_id, root


@router.get("/workspaces/{task_id}/chat/messages")
async def list_chat_messages(task_id: str) -> dict:
    """List persisted chat messages for a workspace."""
    safe_task_id, root = _workspace_root(task_id)
    return {
        "task_id": safe_task_id,
        "messages": RevisionService(root).list_messages(),
    }


@router.post("/workspaces/{task_id}/chat/messages")
async def append_chat_message(task_id: str, request: ChatMessageRequest) -> dict:
    """Append one persisted chat message."""
    safe_task_id, root = _workspace_root(task_id)
    try:
        message = RevisionService(root).append_message(
            role=request.role,
            content=request.content,
            attachments=request.attachments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_progress_event(
        safe_task_id,
        stage="chat.message_added",
        message="对话消息已保存",
        metadata={"role": message["role"], "message_id": message["id"]},
        work_dir=root,
    )
    return {"task_id": safe_task_id, "message": message}


@router.get("/workspaces/{task_id}/revision/requests")
async def list_revision_requests(task_id: str) -> dict:
    """List queued revision requests for a workspace."""
    safe_task_id, root = _workspace_root(task_id)
    return {
        "task_id": safe_task_id,
        "requests": RevisionService(root).list_revision_requests(),
    }


@router.post("/workspaces/{task_id}/revision/requests")
async def create_revision_request(
    task_id: str,
    request: RevisionRequestCreate,
) -> dict:
    """Queue one revision request and emit a progress event."""
    safe_task_id, root = _workspace_root(task_id)
    try:
        revision_request = RevisionService(root).append_revision_request(
            instruction=request.instruction,
            target_artifacts=request.target_artifacts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_progress_event(
        safe_task_id,
        stage="revision.request_queued",
        message="用户修订请求已进入队列",
        metadata={
            "revision_id": revision_request["id"],
            "target_artifacts": revision_request["target_artifacts"],
        },
        work_dir=root,
    )
    return {"task_id": safe_task_id, "request": revision_request}
