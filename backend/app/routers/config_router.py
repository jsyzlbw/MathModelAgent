"""GUI configuration routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config.provider_smoke import ProviderSmokeTester
from app.config.runtime_config import RuntimeConfigStore, deep_merge

router = APIRouter(tags=["gui-config"])


class ProviderTestRequest(BaseModel):
    """Request body for one provider connectivity check."""

    provider: str
    config: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


def get_runtime_config_store() -> RuntimeConfigStore:
    """Dependency hook for tests and runtime config path overrides."""
    return RuntimeConfigStore()


@router.get("/config")
async def get_config(
    store: RuntimeConfigStore = Depends(get_runtime_config_store),
) -> dict[str, Any]:
    """Return runtime config with secrets masked."""
    return store.load_masked()


@router.put("/config")
async def save_config(
    patch: dict[str, Any],
    store: RuntimeConfigStore = Depends(get_runtime_config_store),
) -> dict[str, Any]:
    """Persist a runtime config patch to the ignored local JSON file."""
    return store.save(patch)


@router.post("/config/test-provider")
async def test_provider(
    request: ProviderTestRequest,
    store: RuntimeConfigStore = Depends(get_runtime_config_store),
) -> dict[str, Any]:
    """Test one configured provider for the GUI row-level test buttons."""
    config = deep_merge(store.load_raw(), request.config)
    tester = ProviderSmokeTester(config)
    return await tester.check(request.provider, dry_run=request.dry_run)
