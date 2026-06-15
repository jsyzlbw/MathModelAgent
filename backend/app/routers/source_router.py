"""Workspace source registry and provider query routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.source_provider_service import SourceProviderService
from app.services.source_registry_service import SourceRegistryService
from app.utils.common_utils import ensure_safe_task_id

router = APIRouter(tags=["gui-sources"])


class SourceQueryRequest(BaseModel):
    """Provider query request."""

    provider_type: str
    provider: str
    query: str = Field(min_length=1)
    limit: int = 5


def _workspace_root(task_id: str) -> Path:
    try:
        safe_task_id = ensure_safe_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="非法任务ID") from exc
    root = Path("project") / "work_dir" / safe_task_id
    if not root.exists():
        raise HTTPException(status_code=404, detail="工作区不存在")
    return root


@router.post("/workspaces/{task_id}/sources/query")
async def query_workspace_sources(
    task_id: str,
    request: SourceQueryRequest,
) -> dict:
    """Query a source provider and register results in the workspace."""
    root = _workspace_root(task_id)
    try:
        return {
            "task_id": task_id,
            **SourceProviderService(root).query(
                request.provider_type,
                request.provider,
                request.query,
                limit=request.limit,
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workspaces/{task_id}/sources")
async def list_workspace_sources(task_id: str) -> dict:
    """List registered workspace sources."""
    root = _workspace_root(task_id)
    return {"task_id": task_id, **SourceRegistryService(root).list_sources()}
