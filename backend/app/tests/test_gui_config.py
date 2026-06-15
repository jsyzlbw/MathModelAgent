"""GUI runtime configuration tests."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config.runtime_config import RuntimeConfigStore, mask_secret
from app.main import app


def make_config_client(tmp_path: Path) -> TestClient:
    from app.routers.config_router import get_runtime_config_store

    example = tmp_path / "mcm_agent_config.example.json"
    local = tmp_path / "mcm_agent_config.local.json"
    example.write_text(
        json.dumps(
            {
                "llm": {
                    "coordinator": {
                        "api_type": "openai-chat",
                        "api_key": "",
                        "base_url": "https://api.openai.com/v1",
                        "model": "",
                    }
                },
                "search": {"tavily": {"api_key": ""}},
                "academic": {"openalex": {"email": "", "api_key": ""}},
            }
        ),
        encoding="utf-8",
    )

    def override_store() -> RuntimeConfigStore:
        return RuntimeConfigStore(example_path=example, local_path=local)

    app.dependency_overrides[get_runtime_config_store] = override_store
    return TestClient(app)


def test_gui_config_endpoint_masks_api_keys(tmp_path: Path) -> None:
    client = make_config_client(tmp_path)

    response = client.put(
        "/api/gui/config",
        json={"llm": {"coordinator": {"api_key": "sk-secret", "model": "gpt-4o"}}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["llm"]["coordinator"]["api_key_configured"] is True
    assert body["llm"]["coordinator"]["api_key_preview"].endswith("cret")
    assert body["llm"]["coordinator"]["model"] == "gpt-4o"
    assert "sk-secret" not in response.text

    get_response = client.get("/api/gui/config")
    assert get_response.status_code == 200
    assert "sk-secret" not in get_response.text

    app.dependency_overrides.clear()


def test_gui_config_test_provider_reports_missing_key(tmp_path: Path) -> None:
    client = make_config_client(tmp_path)

    response = client.post(
        "/api/gui/config/test-provider",
        json={"provider": "coordinator"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "coordinator"
    assert body["ok"] is False
    assert body["status"] == "missing_config"
    assert "API Key" in body["message"]

    app.dependency_overrides.clear()


def test_gui_config_test_provider_accepts_config_payload_without_persisting(
    tmp_path: Path,
) -> None:
    client = make_config_client(tmp_path)

    response = client.post(
        "/api/gui/config/test-provider",
        json={
            "provider": "tavily",
            "config": {"search": {"tavily": {"api_key": "tvly-secret"}}},
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "tavily"
    assert body["status"] == "configured"
    assert body["ok"] is True
    assert "tvly-secret" not in response.text

    stored = client.get("/api/gui/config").json()
    assert stored["search"]["tavily"]["api_key_configured"] is False

    app.dependency_overrides.clear()


def test_runtime_config_store_writes_local_json_and_masks_secrets(
    tmp_path: Path,
) -> None:
    example = tmp_path / "example.json"
    local = tmp_path / "local.json"
    example.write_text(
        json.dumps(
            {
                "llm": {
                    "coordinator": {
                        "api_type": "openai-chat",
                        "api_key": "",
                        "model": "gpt-test",
                        "base_url": "",
                    }
                },
                "search": {"tavily": {"api_key": ""}},
            }
        ),
        encoding="utf-8",
    )

    store = RuntimeConfigStore(example_path=example, local_path=local)
    saved = store.save({"llm": {"coordinator": {"api_key": "sk-secret"}}})

    assert local.exists()
    assert saved["llm"]["coordinator"]["api_key_configured"] is True
    assert saved["llm"]["coordinator"]["api_key_preview"].endswith("cret")
    assert saved["llm"]["coordinator"]["model"] == "gpt-test"
    assert "sk-secret" not in str(saved)


def test_runtime_config_store_deep_merges_local_over_example(tmp_path: Path) -> None:
    example = tmp_path / "example.json"
    local = tmp_path / "local.json"
    example.write_text(
        json.dumps(
            {
                "llm": {
                    "coordinator": {
                        "api_type": "openai-chat",
                        "api_key": "",
                        "model": "gpt-default",
                    },
                    "writer": {"api_key": "", "model": "writer-default"},
                },
                "rag": {"knowledge_base_dir": "data/rag_cases"},
            }
        ),
        encoding="utf-8",
    )
    local.write_text(
        json.dumps({"llm": {"coordinator": {"model": "gpt-custom"}}}),
        encoding="utf-8",
    )

    loaded = RuntimeConfigStore(example_path=example, local_path=local).load_raw()

    assert loaded["llm"]["coordinator"]["api_type"] == "openai-chat"
    assert loaded["llm"]["coordinator"]["model"] == "gpt-custom"
    assert loaded["llm"]["writer"]["model"] == "writer-default"
    assert loaded["rag"]["knowledge_base_dir"] == "data/rag_cases"


def test_mask_secret_keeps_empty_values_unconfigured() -> None:
    assert mask_secret("") == {"configured": False, "preview": ""}
