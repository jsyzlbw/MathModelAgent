"""Provider facade for search, academic, and official data source discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config.runtime_registry import RuntimeConfigRegistry
from app.services.source_registry_service import SourceRegistryService


SUPPORTED_PROVIDERS = {
    "search": {"tavily", "brave", "exa", "firecrawl"},
    "academic": {"openalex", "semantic_scholar", "crossref", "arxiv"},
    "official_data": {
        "world_bank",
        "fred",
        "us_census",
        "noaa",
        "open_meteo",
        "overpass",
        "oecd",
        "undata",
        "nasa_power",
    },
}


class SourceProviderService:
    """Query configured providers and register traceable source records."""

    def __init__(
        self,
        workspace: Path | str,
        registry: SourceRegistryService | None = None,
        runtime: RuntimeConfigRegistry | None = None,
    ) -> None:
        self.workspace = Path(workspace)
        self.registry = registry or SourceRegistryService(workspace)
        self.runtime = runtime or RuntimeConfigRegistry()

    def query(
        self,
        provider_type: str,
        provider: str,
        query: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Return registered source records for a provider query."""
        normalized_type = provider_type.strip().lower()
        normalized_provider = provider.strip().lower()
        if normalized_provider not in SUPPORTED_PROVIDERS.get(normalized_type, set()):
            raise ValueError(f"Unsupported provider: {provider_type}/{provider}")
        records = [
            self.registry.register_source(
                provider=normalized_provider,
                source_type=normalized_type,
                title=self._title(normalized_type, normalized_provider, query, index),
                url=self._url(normalized_type, normalized_provider, query, index),
                summary=self._summary(normalized_type, normalized_provider, query),
                metadata={
                    "query": query,
                    "rank": index + 1,
                    "mode": "offline_stub",
                    "configured": self._provider_configured(normalized_type, normalized_provider),
                },
            )
            for index in range(max(1, min(limit, 10)))
        ]
        self.registry.append_query_log(
            normalized_type,
            normalized_provider,
            query,
            [record["source_id"] for record in records],
        )
        return {
            "provider_type": normalized_type,
            "provider": normalized_provider,
            "query": query,
            "sources": records,
            "registry_path": str(self.registry.registry_path),
            "query_log_path": str(self.registry.query_log_path),
        }

    @staticmethod
    def _title(provider_type: str, provider: str, query: str, index: int) -> str:
        label = provider.replace("_", " ").title()
        return f"{label} {provider_type} source {index + 1}: {query}"

    @staticmethod
    def _summary(provider_type: str, provider: str, query: str) -> str:
        return (
            f"Offline-safe {provider_type} discovery record from {provider} for "
            f"query `{query}`. Real provider adapters can replace this record."
        )

    @staticmethod
    def _url(provider_type: str, provider: str, query: str, index: int) -> str:
        slug = query.strip().replace(" ", "+")
        match provider:
            case "openalex":
                return f"https://openalex.org/works?search={slug}&rank={index + 1}"
            case "semantic_scholar":
                return f"https://www.semanticscholar.org/search?q={slug}&rank={index + 1}"
            case "world_bank":
                return f"https://data.worldbank.org/search?q={slug}&rank={index + 1}"
            case "open_meteo":
                return f"https://open-meteo.com/en/docs?query={slug}&rank={index + 1}"
            case "overpass":
                return f"https://overpass-turbo.eu/?q={slug}&rank={index + 1}"
            case _:
                return f"https://example.local/{provider_type}/{provider}?q={slug}&rank={index + 1}"

    def _provider_configured(self, provider_type: str, provider: str) -> bool:
        if provider_type == "search":
            return bool(self.runtime.provider_node(("search", provider)).get("api_key"))
        if provider_type == "academic":
            node = self.runtime.provider_node(("academic", provider))
            return bool(node.get("api_key") or node.get("email") or provider in {"crossref", "arxiv"})
        if provider_type == "official_data":
            node = self.runtime.provider_node(("official_data", provider))
            return bool(node.get("api_key") or provider in {"world_bank", "open_meteo", "overpass", "oecd", "undata", "nasa_power"})
        return False
