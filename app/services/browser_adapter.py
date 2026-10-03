"""Read-only public-web adapter for controlled research discovery."""
from __future__ import annotations

import ipaddress
import json
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class BrowserAdapterError(ValueError):
    pass


class BrowserAdapter:
    """Access public HTTPS research metadata; never logs in or submits data."""
    CROSSREF = "https://api.crossref.org/works"

    def __init__(self, opener=urlopen, timeout: int = 8) -> None:
        self._opener, self._timeout = opener, timeout

    def search_public_research(self, query: str, limit: int = 5) -> dict[str, object]:
        phrase = str(query or "").strip()
        if not phrase:
            raise BrowserAdapterError("A research query is required.")
        endpoint = f"{self.CROSSREF}?{urlencode({'query': phrase, 'rows': max(1, min(int(limit), 10))})}"
        payload = self._json(endpoint)
        items = payload.get("message", {}).get("items", []) if isinstance(payload, dict) else []
        candidates = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = next(iter(item.get("title") or []), "")
            doi = str(item.get("DOI") or "")
            source_url = f"https://doi.org/{doi}" if doi else str(item.get("URL") or "")
            if not title or not source_url:
                continue
            candidates.append({"title": str(title)[:500], "url": source_url, "source_type": "PUBLIC_RESEARCH_METADATA", "published": self._published(item), "relevance_reason": "Returned by the public research metadata search; requires Evidence validation.", "status": "CANDIDATE"})
        return {"status": "COMPLETED", "query": phrase, "candidates": candidates, "verification": "SOURCE_VALIDATION_REQUIRED", "boundary": "Read-only public metadata discovery only. Candidates are not Evidence and are never written to Memory directly."}

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

    @staticmethod
    def _published(item: dict[str, object]) -> str:
        parts = ((item.get("published") or {}).get("date-parts") or [[]]) if isinstance(item.get("published"), dict) else [[]]
        return "-".join(str(value) for value in parts[0]) if parts and parts[0] else ""
