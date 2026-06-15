"""Connectivity checks for GUI-managed provider configuration."""

from __future__ import annotations

from typing import Any

import httpx

from app.config.setting import ApiType
from app.core.llm.providers.anthropic import AnthropicProvider
from app.core.llm.providers.base import BaseProvider
from app.core.llm.providers.openai_chat import OpenAIChatProvider
from app.core.llm.providers.openai_responses import OpenAIResponsesProvider


LLM_PROVIDER_KEYS = {"coordinator", "modeler", "coder", "writer"}


class ProviderSmokeTester:
    """Run small provider checks without exposing secret values."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def check(self, provider: str, dry_run: bool = False) -> dict[str, Any]:
        normalized = provider.strip().lower()
        if normalized in LLM_PROVIDER_KEYS:
            return await self._check_llm(normalized, dry_run=dry_run)
        if normalized == "openalex":
            return await self._check_openalex(dry_run=dry_run)
        if normalized in {"tavily", "brave", "exa", "firecrawl"}:
            return self._check_keyed_provider(normalized, ("search", normalized))
        if normalized in {"mineru"}:
            return self._check_keyed_provider(normalized, ("document", "mineru"))
        if normalized in {"humanizer"}:
            return self._check_keyed_provider(normalized, ("humanizer",))
        if normalized in {
            "world_bank",
            "oecd",
            "undata",
            "fred",
            "us_census",
            "noaa",
            "nasa_power",
            "open_meteo",
            "overpass",
        }:
            return {
                "provider": normalized,
                "ok": True,
                "status": "configured",
                "message": "该官方数据源无需 API Key 或将在实际查询时验证。",
            }
        return {
            "provider": normalized,
            "ok": False,
            "status": "unknown_provider",
            "message": f"未知 provider: {provider}",
        }

    async def _check_llm(self, provider: str, dry_run: bool) -> dict[str, Any]:
        llm_config = self.config.get("llm", {}).get(provider, {})
        api_key = str(llm_config.get("api_key") or "")
        model = str(llm_config.get("model") or "")
        if not api_key:
            return self._missing(provider, "API Key 未配置")
        if not model:
            return self._missing(provider, "模型 ID 未配置")
        if dry_run:
            return self._configured(provider, "配置字段完整，已跳过真实联网请求。")

        try:
            llm_provider = self._make_llm_provider(str(llm_config.get("api_type") or ""))
            await llm_provider.call(
                messages=[{"role": "user", "content": "Hi"}],
                model=model,
                api_key=api_key,
                base_url=llm_config.get("base_url") or None,
                max_tokens=1,
            )
        except Exception as exc:
            return {
                "provider": provider,
                "ok": False,
                "status": "failed",
                "message": f"连接测试失败: {str(exc)[:160]}",
            }
        return self._configured(provider, "模型 API 连接成功。")

    async def _check_openalex(self, dry_run: bool) -> dict[str, Any]:
        openalex_config = self.config.get("academic", {}).get("openalex", {})
        email = str(openalex_config.get("email") or "")
        if not email:
            return self._missing("openalex", "OpenAlex email 未配置")
        if dry_run:
            return self._configured("openalex", "OpenAlex email 已配置，已跳过真实请求。")

        params = {"mailto": email, "per-page": 1}
        if openalex_config.get("api_key"):
            params["api_key"] = openalex_config["api_key"]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get("https://api.openalex.org/works", params=params)
                response.raise_for_status()
        except Exception as exc:
            return {
                "provider": "openalex",
                "ok": False,
                "status": "failed",
                "message": f"OpenAlex 连接失败: {str(exc)[:160]}",
            }
        return self._configured("openalex", "OpenAlex 连接成功。")

    def _check_keyed_provider(
        self,
        provider: str,
        path: tuple[str, ...],
    ) -> dict[str, Any]:
        node: Any = self.config
        for key in path:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        api_key = str(node.get("api_key") or "") if isinstance(node, dict) else ""
        if not api_key:
            return self._missing(provider, "API Key 未配置")
        return self._configured(provider, "API Key 已配置；真实请求将在对应功能调用时验证。")

    @staticmethod
    def _make_llm_provider(api_type: str) -> BaseProvider:
        match api_type:
            case ApiType.OPENAI_RESPONSES:
                return OpenAIResponsesProvider()
            case ApiType.ANTHROPIC:
                return AnthropicProvider()
            case _:
                return OpenAIChatProvider()

    @staticmethod
    def _missing(provider: str, message: str) -> dict[str, Any]:
        return {
            "provider": provider,
            "ok": False,
            "status": "missing_config",
            "message": message,
        }

    @staticmethod
    def _configured(provider: str, message: str) -> dict[str, Any]:
        return {
            "provider": provider,
            "ok": True,
            "status": "configured",
            "message": message,
        }
