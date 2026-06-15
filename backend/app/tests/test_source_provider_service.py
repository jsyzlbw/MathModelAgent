"""Source provider and registry tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_source_registry_registers_stable_sources(tmp_path: Path) -> None:
    from app.services.source_registry_service import SourceRegistryService

    registry = SourceRegistryService(tmp_path / "workspace")
    first = registry.register_source(
        provider="openalex",
        source_type="academic",
        title="Water allocation model",
        url="https://example.test/work",
        summary="A paper about water allocation.",
        metadata={"year": 2024},
    )
    second = registry.register_source(
        provider="openalex",
        source_type="academic",
        title="Water allocation model",
        url="https://example.test/work",
        summary="A paper about water allocation.",
        metadata={"year": 2024},
    )

    assert first["source_id"] == second["source_id"]
    assert registry.registry_path.exists()
    assert len(registry.list_sources()["sources"]) == 1


def test_source_provider_queries_academic_and_official_data(tmp_path: Path) -> None:
    from app.services.source_provider_service import SourceProviderService

    service = SourceProviderService(tmp_path / "workspace")

    academic = service.query("academic", "openalex", "water allocation", limit=2)
    official = service.query("official_data", "world_bank", "population", limit=1)

    assert academic["sources"][0]["provider"] == "openalex"
    assert academic["sources"][0]["source_type"] == "academic"
    assert official["sources"][0]["provider"] == "world_bank"
    assert official["sources"][0]["source_type"] == "official_data"
    assert service.registry.query_log_path.exists()


def test_source_api_queries_and_lists_sources(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    task_id = "source-task"
    workspace = tmp_path / "project" / "work_dir" / task_id
    workspace.mkdir(parents=True)
    client = TestClient(app)

    query_response = client.post(
        f"/api/gui/workspaces/{task_id}/sources/query",
        json={
            "provider_type": "academic",
            "provider": "openalex",
            "query": "network optimization",
            "limit": 2,
        },
    )
    list_response = client.get(f"/api/gui/workspaces/{task_id}/sources")

    assert query_response.status_code == 200
    assert query_response.json()["sources"][0]["provider"] == "openalex"
    assert list_response.status_code == 200
    assert list_response.json()["sources"][0]["source_id"]
