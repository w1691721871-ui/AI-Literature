import unittest

from app.services.browser_adapter import BrowserAdapterError
from app.services.computer_execution_engine import ComputerExecutionEngine


class StubBrowser:
    def search_public_research(self, query):
        return {"candidates": [{"title": "Actual metadata candidate", "url": "https://doi.org/example", "status": "CANDIDATE"}]}
    def open_public_page(self, url):
        return {"url": url, "page_state": "public_page_loaded"}

class ComputerExecutionEngineTests(unittest.TestCase):
    def setUp(self): self.engine = ComputerExecutionEngine(StubBrowser())
    def test_search_returns_candidates_not_evidence(self):
        result = self.engine.execute({"action_type": "SEARCH", "input": "low carbon concrete"}, permission_granted=True)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["result"]["candidates"][0]["status"], "CANDIDATE")
        self.assertIn("Evidence validation", result["boundary"])
    def test_permission_and_unsafe_actions_are_blocked(self):
        self.assertEqual(self.engine.execute({"action_type": "SEARCH", "input": "x"}, permission_granted=False)["status"], "WAITING_APPROVAL")
        self.assertEqual(self.engine.execute({"action_type": "UPLOAD"}, permission_granted=True)["status"], "BLOCKED")
    def test_adapter_rejects_non_public_url(self):
        from app.services.browser_adapter import BrowserAdapter
        with self.assertRaises(BrowserAdapterError): BrowserAdapter._assert_public_https("http://127.0.0.1/admin")
