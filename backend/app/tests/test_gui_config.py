"""GUI runtime configuration tests."""

import json
from pathlib import Path

from app.config.runtime_config import RuntimeConfigStore, mask_secret


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
