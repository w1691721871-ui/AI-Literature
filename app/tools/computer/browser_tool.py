"""Bounded external-source inspection for Research Operator.

External pages are *candidates*, never formal ResearchOS Evidence. Search
remains connector-based; opening requires an explicit public HTTPS URL supplied
by the user or an approved integration.
"""

from __future__ import annotations

import html
import ipaddress
import re
import socket
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class BrowserTool:
    name = "computer_browser_connector"
    description = "Records a browser-research request without browsing, downloading, or inventing sources."

    def request(self, topic: str, operation: str = "search") -> dict[str, object]:
        if operation not in {"search", "open", "extract", "download"}:
            raise ValueError("浏览器连接器只接受 search、open、extract 或 download 请求。")
        return {"status": "connector_not_configured", "operation": operation, "topic": topic, "candidate_sources": [], "boundary": "当前版本未连接浏览器；不会搜索、打开、提取、下载或伪造网页来源。"}

    def open_and_extract(self, source_url: str) -> dict[str, object]:
        """Read a small public HTML preview as an unverified external candidate."""
        parsed = urlparse(source_url.strip())
        if parsed.scheme != "https" or not parsed.hostname or not self._public_host(parsed.hostname):
            return self._blocked(source_url, "仅允许用户明确提供的公共 HTTPS 来源；不访问本地、私有或非 HTTPS 地址。")
        try:
            request = Request(source_url, headers={"User-Agent": "ResearchOS-ExternalCandidate/1.0"})
            with urlopen(request, timeout=8) as response:  # nosec B310 - URL is validated above
                content_type = str(response.headers.get("Content-Type", "")).lower()
                if "text/html" not in content_type:
                    return self._blocked(source_url, "仅提取公开 HTML 页面摘要；PDF、下载文件和二进制内容需走人工审核与正式上传流程。")
                raw = response.read(200_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        except Exception as error:
            return self._blocked(source_url, f"无法读取该外部来源：{type(error).__name__}。")
        title = self._clean(self._first(r"<title[^>]*>(.*?)</title>", raw)) or parsed.hostname
        text = self._clean(re.sub(r"<[^>]+>", " ", raw))
        return {
            "status": "external_candidate_ready",
            "candidate_sources": [{
                "source_type": "External Source",
                "url": source_url,
                "title": title[:240],
                "excerpt": text[:700],
                "human_verification_required": True,
                "formal_evidence_eligible": False,
            }],
            "boundary": "外部来源仅作为待核验候选，不会自动写入论文库、FAISS 或 Evidence Center。",
        }

    @staticmethod
    def _first(pattern: str, value: str) -> str:
        match = re.search(pattern, value, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else ""

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"\s+", " ", html.unescape(value)).strip()

    @staticmethod
    def _public_host(hostname: str) -> bool:
        if hostname.lower() in {"localhost", "localhost.localdomain"}:
            return False
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None)}
            return bool(addresses) and all(not ipaddress.ip_address(address).is_private and not ipaddress.ip_address(address).is_loopback and not ipaddress.ip_address(address).is_link_local for address in addresses)
        except (OSError, ValueError):
            return False

    @staticmethod
    def _blocked(source_url: str, message: str) -> dict[str, object]:
        return {"status": "external_candidate_unavailable", "candidate_sources": [], "url": source_url, "boundary": message}
