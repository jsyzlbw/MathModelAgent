"""JSON runtime configuration store for GUI-managed settings."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_EXAMPLE_CONFIG_PATH = Path("mcm_agent_config.example.json")
DEFAULT_LOCAL_CONFIG_PATH = Path("mcm_agent_config.local.json")

SECRET_KEY_PARTS = ("api_key", "token", "secret", "password")


def mask_secret(value: Any) -> dict[str, str | bool]:
    """Return a non-sensitive preview for a secret value."""
    if not isinstance(value, str) or not value:
        return {"configured": False, "preview": ""}
    if len(value) <= 8:
        preview = "*" * len(value)
    else:
        preview = f"{value[:3]}...{value[-4:]}"
    return {"configured": True, "preview": preview}


def _is_secret_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in SECRET_KEY_PARTS)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries without mutating either input."""
    merged = deepcopy(base)
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def mask_config(data: Any) -> Any:
    """Recursively mask secret fields while preserving non-secret settings."""
    if isinstance(data, list):
        return [mask_config(item) for item in data]
    if not isinstance(data, dict):
        return data

    masked: dict[str, Any] = {}
    for key, value in data.items():
        if _is_secret_key(key):
            secret = mask_secret(value)
            masked[f"{key}_configured"] = secret["configured"]
            masked[f"{key}_preview"] = secret["preview"]
        else:
            masked[key] = mask_config(value)
    return masked


class RuntimeConfigStore:
    """Load, save, and mask GUI runtime configuration JSON files."""

    def __init__(
        self,
        example_path: Path | str = DEFAULT_EXAMPLE_CONFIG_PATH,
        local_path: Path | str = DEFAULT_LOCAL_CONFIG_PATH,
    ) -> None:
        self.example_path = Path(example_path)
        self.local_path = Path(local_path)

    def load_raw(self) -> dict[str, Any]:
        """Load example defaults merged with ignored local overrides."""
        example = self._read_json(self.example_path)
        local = self._read_json(self.local_path)
        return deep_merge(example, local)

    def load_masked(self) -> dict[str, Any]:
        """Load config with all secret values replaced by previews."""
        return mask_config(self.load_raw())

    def save(self, patch: dict[str, Any]) -> dict[str, Any]:
        """Merge a patch into local JSON and return the masked full config."""
        current = self.load_raw()
        merged = deep_merge(current, patch)
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return mask_config(merged)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a JSON object: {path}")
        return data
