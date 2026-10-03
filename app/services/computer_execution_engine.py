"""Single, bounded execution entry point for read-only Computer research."""
from __future__ import annotations

from collections.abc import Mapping

from app.services.browser_adapter import BrowserAdapter, BrowserAdapterError


class ComputerExecutionEngine:
    """Executes only declared read-only Browser actions and verifies outcomes."""
    READ_ONLY_ACTIONS = {"SEARCH", "NAVIGATE", "EXTRACT", "VERIFY"}

    def __init__(self, browser: BrowserAdapter | None = None) -> None:
        self.browser = browser or BrowserAdapter()

    def execute(self, action: Mapping[str, object], *, permission_granted: bool, environment_ready: bool = True) -> dict[str, object]:
        kind = str(action.get("action_type") or "").upper()
        if kind not in self.READ_ONLY_ACTIONS:
            return self._result("BLOCKED", "This action is not available to the read-only Computer Worker.")
        if not permission_granted:
            return self._result("WAITING_APPROVAL", "Workspace permission is required before Computer execution.")
        if not environment_ready:
            return self._result("WAITING_REVIEW", "The authorized environment is not ready for a controlled action.")
        try:
            if kind == "SEARCH":
                payload = self.browser.search_public_research(str(action.get("input") or action.get("query") or ""))
                success = bool(payload.get("candidates"))
                return {**self._result("COMPLETED" if success else "NEEDS_REVIEW", "Research candidates were discovered." if success else "No candidates were returned; refine the query or request review."), "result": payload, "verification": "CANDIDATES_PRESENT" if success else "NO_CANDIDATES"}
            if kind == "NAVIGATE":
                payload = self.browser.open_public_page(str(action.get("target") or ""))
                return {**self._result("COMPLETED", "Public source loaded for read-only review."), "result": payload, "verification": "PAGE_LOADED"}
            return self._result("WAITING_REVIEW", "This action requires an existing Evidence or verification workflow.")
        except BrowserAdapterError as error:
            return self._result("BLOCKED", str(error))
        except Exception:
            return self._result("NEEDS_REVIEW", "Public source access did not complete. No result was stored as Evidence.")

    @staticmethod
    def _result(status: str, summary: str) -> dict[str, object]:
        return {"status": status, "summary": summary, "boundary": "Execution is read-only. Results remain candidates until the existing Evidence validation workflow approves them."}
