"""GUI interactive planning and HIL routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.progress_events import append_progress_event
from app.services.planning_service import PlanningService
from app.utils.common_utils import ensure_safe_task_id

router = APIRouter(tags=["gui-planning"])


class PlanDraftRequest(BaseModel):
    """Optional draft request body."""

    problem_text: str = ""


class PlanActionRequest(BaseModel):
    """HIL action request."""

    action: str
    content: str = ""


def _workspace_root(task_id: str) -> Path:
    try:
        safe_task_id = ensure_safe_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="非法任务ID") from exc
    root = Path("project") / "work_dir" / safe_task_id
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    return root


@router.post("/workspaces/{task_id}/planning/draft")
async def draft_workspace_plan(
    task_id: str,
    request: PlanDraftRequest | None = None,
) -> dict:
    """Create a plan draft for a GUI workspace."""
    root = _workspace_root(task_id)
    plan = PlanningService(root).create_plan(
        problem_text=request.problem_text if request else "",
    )
    append_progress_event(
        task_id,
        stage="planning.draft_created",
        message="执行计划草案已生成",
        work_dir=root,
    )
    return plan


@router.get("/workspaces/{task_id}/planning")
async def get_workspace_plan(task_id: str) -> dict:
    """Load the current workspace plan."""
    root = _workspace_root(task_id)
    return PlanningService(root).load_plan()


@router.post("/workspaces/{task_id}/planning/action")
async def apply_workspace_plan_action(
    task_id: str,
    request: PlanActionRequest,
) -> dict:
    """Apply one human-in-the-loop action to the plan."""
    root = _workspace_root(task_id)
    try:
        plan = PlanningService(root).apply_action(request.action, content=request.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_progress_event(
        task_id,
        stage=f"planning.{request.action}",
        message=f"计划动作已记录: {request.action}",
        metadata={"content": request.content},
        work_dir=root,
    )
    return plan
