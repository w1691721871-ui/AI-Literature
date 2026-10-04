"""Read-only public-web adapter for controlled research discovery."""
from __future__ import annotations

import ipaddress
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.services.research_source_provider import ResearchSourceProviderRegistry


class BrowserAdapterError(ValueError):
    pass


class BrowserAdapter:
    """Access public HTTPS research metadata; never logs in or submits data."""
    def __init__(self, opener=urlopen, timeout: int = 8, providers=None) -> None:
        self._opener, self._timeout = opener, timeout
        self._providers = providers or ResearchSourceProviderRegistry(self._json)

    def search_public_research(self, query: str, limit: int = 5) -> dict[str, object]:
        phrase = str(query or "").strip()
        if not phrase:
            raise BrowserAdapterError("A research query is required.")
        provider = self._providers.selected()
        candidates = provider.search(phrase, limit)
        return {"status": "COMPLETED", "query": phrase, "provider": provider.provider_id, "candidates": candidates, "verification": "SOURCE_VALIDATION_REQUIRED", "boundary": "Read-only public metadata discovery only. Candidates are not Evidence and are never written to Memory directly."}

    def open_public_page(self, url: str) -> dict[str, object]:
        self._assert_public_https(url)
        request = Request(url, headers={"User-Agent": "ResearchOS-ComputerWorker/1.0"})
        with self._opener(request, timeout=self._timeout) as response:
            content_type = str(response.headers.get("Content-Type") or "")
            return {"status": "COMPLETED", "url": url, "content_type": content_type, "page_state": "public_page_loaded", "boundary": "No credentials, form submission, cookies or page content are stored."}

    def _json(self, url: str) -> object:
        self._assert_public_https(url)
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "ResearchOS-ComputerWorker/1.0"})
        with self._opener(request, timeout=self._timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _assert_public_https(url: str) -> None:
        parsed = urlparse(str(url))
        if parsed.scheme != "https" or not parsed.hostname:
            raise BrowserAdapterError("Only public HTTPS sources are allowed.")
        host = parsed.hostname.lower()
        if host in {"localhost", "0.0.0.0"} or host.endswith(".local"):
            raise BrowserAdapterError("Local network sources are not allowed.")
        try:
            if ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback:
                raise BrowserAdapterError("Private network sources are not allowed.")
        except ValueError:
            pass
