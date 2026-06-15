"""GUI runtime configuration tests."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config.setting import ApiType
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


def test_runtime_registry_reads_llm_role_from_json(tmp_path: Path) -> None:
    from app.config.runtime_registry import RuntimeConfigRegistry

    example = tmp_path / "example.json"
    local = tmp_path / "local.json"
    example.write_text(
        json.dumps(
            {
                "llm": {
                    "coordinator": {
                        "api_type": "openai-chat",
                        "api_key": "",
                        "base_url": "",
                        "model": "",
                        "context_window": 128000,
                        "max_tokens": None,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    local.write_text(
        json.dumps(
            {
                "llm": {
                    "coordinator": {
                        "api_key": "sk-local",
                        "model": "deepseek",
                        "base_url": "https://api.deepseek.com/v1",
                        "context_window": 64000,
                        "max_tokens": 2048,
                    }
                },
                "runtime": {"max_chat_turns": 9, "max_retries": 4},
                "academic": {"openalex": {"email": "agent@example.com", "api_key": "oa"}},
            }
        ),
        encoding="utf-8",
    )

    registry = RuntimeConfigRegistry(RuntimeConfigStore(example, local))
    role = registry.llm_role("coordinator")

    assert role.api_type == ApiType.OPENAI_CHAT
    assert role.api_key == "sk-local"
    assert role.model == "deepseek"
    assert role.base_url == "https://api.deepseek.com/v1"
    assert role.context_window == 64000
    assert role.max_tokens == 2048
    assert registry.runtime_int("max_chat_turns", 20) == 9
    assert registry.runtime_int("max_retries", 2) == 4
    assert registry.openalex() == {"email": "agent@example.com", "api_key": "oa"}


def test_runtime_registry_falls_back_to_settings_for_empty_json(tmp_path: Path) -> None:
    from app.config.runtime_registry import RuntimeConfigRegistry

    class FallbackSettings:
        COORDINATOR_API_TYPE = ApiType.ANTHROPIC
        COORDINATOR_API_KEY = "anthropic-key"
        COORDINATOR_MODEL = "claude-test"
        COORDINATOR_BASE_URL = "https://example.test"
        COORDINATOR_CONTEXT_WINDOW = 32000
        COORDINATOR_MAX_TOKENS = 1024

    example = tmp_path / "example.json"
    local = tmp_path / "local.json"
    example.write_text(
        json.dumps(
            {
                "llm": {
                    "coordinator": {
                        "api_type": "",
                        "api_key": "",
                        "base_url": "",
                        "model": "",
                        "context_window": None,
                        "max_tokens": None,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    registry = RuntimeConfigRegistry(RuntimeConfigStore(example, local))
    role = registry.llm_role("coordinator", fallback_settings=FallbackSettings)

    assert role.api_type == ApiType.ANTHROPIC
    assert role.api_key == "anthropic-key"
    assert role.model == "claude-test"
    assert role.base_url == "https://example.test"
    assert role.context_window == 32000
    assert role.max_tokens == 1024


def test_llm_factory_uses_runtime_registry() -> None:
    from app.config.runtime_registry import LLMRoleConfig
    from app.core.llm.llm_factory import LLMFactory

    class Registry:
        def llm_role(self, role: str) -> LLMRoleConfig:
            return LLMRoleConfig(
                api_type=ApiType.OPENAI_CHAT,
                api_key=f"{role}-key",
                model=f"{role}-model",
                base_url=f"https://{role}.example.test/v1",
                context_window=12345,
                max_tokens=111,
            )

    coordinator, modeler, coder, writer = LLMFactory(
        "runtime-task",
        registry=Registry(),
    ).get_all_llms()

    assert coordinator.api_key == "coordinator-key"
    assert coordinator.model == "coordinator-model"
    assert coordinator.base_url == "https://coordinator.example.test/v1"
    assert coordinator.max_tokens == 111
    assert modeler.api_key == "modeler-key"
    assert coder.api_key == "coder-key"
    assert writer.api_key == "writer-key"


def test_provider_smoke_supports_embedding_and_reranker() -> None:
    from app.config.provider_smoke import ProviderSmokeTester

    missing = ProviderSmokeTester({"rag": {}})
    assert missing.check_sync("embedding", dry_run=True)["status"] == "missing_config"
    assert missing.check_sync("reranker", dry_run=True)["status"] == "missing_config"

    configured = ProviderSmokeTester(
        {
            "rag": {
                "embedding_provider": "voyage",
                "embedding_model": "voyage-4-large",
                "embedding_api_key": "pa-secret",
                "embedding_base_url": "https://api.voyageai.com/v1",
                "reranker_provider": "voyage",
                "reranker_model": "rerank-2.5",
                "reranker_api_key": "pa-secret",
                "reranker_base_url": "https://api.voyageai.com/v1",
            }
        }
    )

    embedding = configured.check_sync("embedding", dry_run=True)
    reranker = configured.check_sync("reranker", dry_run=True)

    assert embedding["ok"] is True
    assert embedding["status"] == "configured"
    assert "pa-secret" not in str(embedding)
    assert reranker["ok"] is True
    assert reranker["status"] == "configured"
    assert "pa-secret" not in str(reranker)


def test_provider_smoke_supports_semantic_scholar_and_public_data_sources() -> None:
    from app.config.provider_smoke import ProviderSmokeTester

    tester = ProviderSmokeTester(
        {
            "academic": {"semantic_scholar": {"api_key": "s2-secret"}},
            "official_data": {"open_meteo": {}, "overpass": {}, "fred": {}},
        }
    )

    semantic = tester.check_sync("semantic_scholar", dry_run=True)
    open_meteo = tester.check_sync("open_meteo", dry_run=True)
    fred = tester.check_sync("fred", dry_run=True)

    assert semantic["ok"] is True
    assert semantic["status"] == "configured"
    assert "s2-secret" not in str(semantic)
    assert open_meteo["ok"] is True
    assert open_meteo["status"] == "configured"
    assert fred["ok"] is False
    assert fred["status"] == "missing_config"
