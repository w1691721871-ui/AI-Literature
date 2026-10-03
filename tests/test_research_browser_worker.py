import unittest
from app.services.research_browser_worker import ResearchBrowserWorker

class Engine:
    def execute(self, action, *, permission_granted):
        if not permission_granted: return {"status":"WAITING_APPROVAL", "summary":"permission"}
        return {"status":"COMPLETED", "summary":"found", "result":{"candidates":[{"title":action["input"], "url":"https://doi.org/10." + str(abs(hash(action["input"]))), "status":"CANDIDATE"}]}}

class SparseEngine:
    def __init__(self): self.calls=[]
    def execute(self, action, *, permission_granted):
        self.calls.append(action["input"])
        return {"status":"COMPLETED", "summary":"no matching source", "result":{"candidates":[]}}

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
    def test_sparse_research_uses_bounded_query_adjustments_then_stops(self):
        engine=SparseEngine()
        result=ResearchBrowserWorker(engine=engine).run("mission-2", "Analyze low carbon materials", permission_granted=True)
        self.assertEqual(result["status"], "NEEDS_REVIEW")
        self.assertEqual(len(result["adjustments"]), 2)
        self.assertLessEqual(len(engine.calls), 9)
