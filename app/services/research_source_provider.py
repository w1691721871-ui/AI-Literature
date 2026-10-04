"""Controlled public research-source providers for the Computer Worker.

Providers discover public metadata only.  They never promote a result to
Evidence, persist source bodies, authenticate to a third-party site, or submit
data externally.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol
from urllib.parse import urlencode


class ResearchSourceProvider(Protocol):
    """A read-only provider returning normalized candidate source metadata."""

    provider_id: str
    label: str

    def search(self, query: str, limit: int) -> list[dict[str, object]]:
        """Return candidates only; Evidence validation happens downstream."""


class CrossrefMetadataProvider:
    """Public Crossref metadata discovery with a stable Worker-safe shape."""

    provider_id = "CROSSREF"
    label = "Crossref public metadata"
    endpoint = "https://api.crossref.org/works"

    def __init__(self, fetch_json: Callable[[str], object]) -> None:
        self._fetch_json = fetch_json

    def search(self, query: str, limit: int) -> list[dict[str, object]]:
        payload = self._fetch_json(f"{self.endpoint}?{urlencode({'query': query, 'rows': max(1, min(int(limit), 10))})}")
        items = payload.get("message", {}).get("items", []) if isinstance(payload, dict) else []
        candidates: list[dict[str, object]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = next(iter(item.get("title") or []), "")
            doi = str(item.get("DOI") or "")
            source_url = f"https://doi.org/{doi}" if doi else str(item.get("URL") or "")
            if not title or not source_url:
                continue
            candidates.append({
                "title": str(title)[:500], "url": source_url,
                "source_type": "PUBLIC_RESEARCH_METADATA", "source_provider": self.provider_id,
                "published": self._published(item),
                "relevance_reason": "Returned by public research metadata discovery; Evidence validation is required.",
                "status": "CANDIDATE",
            })
        return candidates

    @staticmethod
    def _published(item: dict[str, object]) -> str:
        published = item.get("published")
        parts = (published.get("date-parts") or [[]]) if isinstance(published, dict) else [[]]
        return "-".join(str(value) for value in parts[0]) if parts and parts[0] else ""


class ResearchSourceProviderRegistry:
    """Small explicit allow-list; no arbitrary external source URL is accepted."""

    def __init__(self, fetch_json: Callable[[str], object]) -> None:
        self._providers: dict[str, ResearchSourceProvider] = {
            "CROSSREF": CrossrefMetadataProvider(fetch_json),
        }

    def selected(self, provider_id: str = "CROSSREF") -> ResearchSourceProvider:
        provider = self._providers.get(str(provider_id or "CROSSREF").upper())
        if provider is None:
            raise ValueError("The requested research source provider is not enabled.")
        return provider

    def catalog(self) -> list[dict[str, str]]:
        return [{"id": provider.provider_id, "label": provider.label, "mode": "READ_ONLY_METADATA"} for provider in self._providers.values()]
