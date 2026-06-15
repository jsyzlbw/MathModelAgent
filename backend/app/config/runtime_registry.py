"""Typed accessors for the GUI-managed runtime JSON config."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config.runtime_config import RuntimeConfigStore
from app.config.setting import ApiType, settings


LLM_ROLE_NAMES = ("coordinator", "modeler", "coder", "writer")


@dataclass(frozen=True)
class LLMRoleConfig:
    """Resolved configuration for one LLM role."""

    api_type: ApiType | None
    api_key: str | None
    model: str | None
    base_url: str | None
    context_window: int
    max_tokens: int | None


class RuntimeConfigRegistry:
    """Resolve runtime settings from JSON with `.env` fallback."""

    def __init__(self, store: RuntimeConfigStore | None = None) -> None:
        self.store = store or RuntimeConfigStore()

    def load(self) -> dict[str, Any]:
        """Return merged raw runtime config."""
        return self.store.load_raw()

    def llm_role(
        self,
        role: str,
        fallback_settings: Any = settings,
    ) -> LLMRoleConfig:
        """Resolve a single LLM role config from JSON, then settings fallback."""
        normalized = role.strip().lower()
        if normalized not in LLM_ROLE_NAMES:
            raise ValueError(f"Unknown LLM role: {role}")

        data = self.load().get("llm", {}).get(normalized, {})
        prefix = normalized.upper()
        api_type = self._api_type(
            self._first_non_empty(data.get("api_type"), getattr(fallback_settings, f"{prefix}_API_TYPE", None))
        )
        return LLMRoleConfig(
            api_type=api_type,
            api_key=self._first_non_empty(
                data.get("api_key"),
                getattr(fallback_settings, f"{prefix}_API_KEY", None),
            ),
            model=self._first_non_empty(
                data.get("model"),
                getattr(fallback_settings, f"{prefix}_MODEL", None),
            ),
            base_url=self._first_non_empty(
                data.get("base_url"),
                getattr(fallback_settings, f"{prefix}_BASE_URL", None),
            ),
            context_window=self._int_or_default(
                data.get("context_window"),
                getattr(fallback_settings, f"{prefix}_CONTEXT_WINDOW", 128000),
            ),
            max_tokens=self._optional_int(
                self._first_non_empty(
                    data.get("max_tokens"),
                    getattr(fallback_settings, f"{prefix}_MAX_TOKENS", None),
                )
            ),
        )

    def runtime_int(self, name: str, fallback: int | None) -> int | None:
        """Read an integer from the runtime section."""
        value = self.load().get("runtime", {}).get(name)
        if value is None or value == "":
            return fallback
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def openalex(self) -> dict[str, str | None]:
        """Return OpenAlex credentials from runtime JSON with settings fallback."""
        node = self.load().get("academic", {}).get("openalex", {})
        return {
            "email": self._first_non_empty(node.get("email"), settings.OPENALEX_EMAIL),
            "api_key": self._first_non_empty(node.get("api_key"), settings.OPENALEX_API_KEY),
        }

    def rag(self) -> dict[str, Any]:
        """Return the raw RAG configuration section."""
        node = self.load().get("rag", {})
        return node if isinstance(node, dict) else {}

    def provider_node(self, path: tuple[str, ...]) -> dict[str, Any]:
        """Return a provider config node by path, or an empty dict."""
        node: Any = self.load()
        for key in path:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        return node if isinstance(node, dict) else {}

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    @staticmethod
    def _api_type(value: Any) -> ApiType | None:
        if isinstance(value, ApiType):
            return value
        if not value:
            return None
        try:
            return ApiType(str(value))
        except ValueError:
            return ApiType.OPENAI_CHAT

    @staticmethod
    def _int_or_default(value: Any, fallback: int) -> int:
        if value is None or value == "":
            return fallback
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


def get_runtime_registry() -> RuntimeConfigRegistry:
    """Dependency-style factory for runtime config access."""
    return RuntimeConfigRegistry()
