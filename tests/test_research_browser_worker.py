import unittest
from app.services.research_browser_worker import ResearchBrowserWorker

class Engine:
    def execute(self, action, *, permission_granted):
        if not permission_granted: return {"status":"WAITING_APPROVAL", "summary":"permission"}
        return {"status":"COMPLETED", "summary":"found", "result":{"candidates":[{"title":action["input"], "url":"https://doi.org/10." + str(abs(hash(action["input"]))), "status":"CANDIDATE"}]}}

class ResearchBrowserWorkerTests(unittest.TestCase):
    def test_multi_step_research_yields_candidates_not_approved_evidence(self):
        result=ResearchBrowserWorker(engine=Engine()).run("mission-1", "Analyze low carbon materials future direction", permission_granted=True)
        self.assertEqual(result["status"], "READY_FOR_EVIDENCE_VALIDATION")
        self.assertTrue(result["candidate_evidence"])
        self.assertTrue(all(item["validation_required"] for item in result["candidate_evidence"]))
        self.assertIsNone(result["artifact"])
    def test_permission_stops_worker_before_search(self):
        result=ResearchBrowserWorker(engine=Engine()).run("mission-1", "Analyze low carbon materials", permission_granted=False)
        self.assertEqual(result["status"], "WAITING_APPROVAL")
