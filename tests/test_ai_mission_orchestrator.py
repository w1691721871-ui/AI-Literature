"""P23 Mission orchestration tests use only disposable in-memory fixtures.

The retrieval stub models the shape of an existing RAG response.  It never
writes a Paper, chunk, FAISS index, or embedding into the running product.
"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.computer_mission import ComputerMission
from app.models.agent_trace import AgentTrace
from app.models.execution_graph import ExecutionGraph
from app.models.planner_trace import PlannerTrace
from app.models.agent_memory import AgentMemory
from app.models.notification import Notification
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.solution_computer_mission import SolutionComputerMission
from app.models.solution_deliverable import SolutionDeliverable
from app.models.solution_project import SolutionProject
from app.models.solution_requirement import SolutionRequirement
from app.models.solution_version import SolutionVersion
from app.services.ai_mission_service import AIMissionService
from app.services.fde_solution_service import FDESolutionService


class FixtureRetrieval:
    def retrieve(self, _question, top_k=5):
        self.top_k = top_k
        return [{
            "paper_id": "authorized-paper",
            "chunk_id": "authorized-chunk",
            "filename": "authorized.pdf",
            "section": "Evaluation",
        }]


class FailingRetrieval:
    def retrieve(self, _question, top_k=5):
        raise RuntimeError("fixture retrieval unavailable")


class AIMissionOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        self.tables = (
            AIMission.__table__, AIMissionEvent.__table__, AgentTrace.__table__, ExecutionGraph.__table__, PlannerTrace.__table__, AgentMemory.__table__, ComputerMission.__table__, Notification.__table__,
            Paper.__table__, PaperChunk.__table__, SolutionProject.__table__,
            SolutionRequirement.__table__, SolutionDeliverable.__table__,
            SolutionComputerMission.__table__, SolutionVersion.__table__,
        )
        for table in self.tables:
            table.create(self.engine)
        self.fde = FDESolutionService(self.Session, initialize=False)

    def tearDown(self):
        self.engine.dispose()

    def _service(self, retrieval=None):
        return AIMissionService(self.Session, initialize=False, fde_service=self.fde,
                                retrieval_service=retrieval or FixtureRetrieval())

    def _created(self, service):
        return service.create({
            "title": "Customer research mission",
            "mission_type": "SOLUTION",
            "goal": "Assess authorized research evidence for a customer need.",
        })

    def test_run_creates_requirements_and_persists_only_retrieved_references(self):
        service = self._service()
        mission = service.run(self._created(service)["id"])
        self.assertEqual(mission["status"], "WAITING_REVIEW")
        self.assertEqual(len(mission["requirements"]), 6)
        self.assertTrue(all(item["status"] == "NEEDS_CONFIRMATION" for item in mission["requirements"]))
        self.assertEqual(mission["evidence_refs"], [{
            "paper_id": "authorized-paper", "chunk_id": "authorized-chunk",
            "source": "authorized.pdf", "section": "Evaluation",
        }])
        actions = [item["action"] for item in mission["timeline"]]
        self.assertIn("Evidence Retrieved", actions)
        self.assertIn("Waiting Human Review", actions)
        evidence_nodes = [node for node in mission["evidence_graph"]["nodes"] if node["type"] == "evidence"]
        self.assertEqual(evidence_nodes[0]["chunk_id"], "authorized-chunk")
        self.assertTrue(any(node["type"] == "blueprint" for node in mission["evidence_graph"]["nodes"]))

    def test_delivery_is_gated_then_revision_approval_and_completion_are_auditable(self):
        service = self._service()
        mission = service.run(self._created(service)["id"])
        with self.assertRaises(ValueError):
            service.delivery(mission["id"])
        revision = service.review(mission["id"], "NEEDS_REVISION", "Clarify the delivery scope.")
        self.assertEqual(revision["mission"]["status"], "NEEDS_REVISION")
        revised = service.revise(mission["id"], "Clarify scope without adding unsupported claims.")
        self.assertEqual(revised["status"], "WAITING_REVIEW")
        approved = service.review(mission["id"], "APPROVED", "Approved by reviewer.")
        self.assertEqual(approved["mission"]["status"], "APPROVED")
        delivery = service.delivery(mission["id"])
        self.assertEqual(delivery["mission"]["status"], "COMPLETED")
        self.assertIn("AI Generated Draft", delivery["delivery_package"]["label"])
        self.assertIn("NEEDS_CONFIRMATION", delivery["delivery_package"]["label"])
        self.assertEqual(delivery["delivery_package"]["evidence_references"][0]["chunk_id"], "authorized-chunk")
        detail = service.detail(mission["id"])
        self.assertGreaterEqual(len(detail["deliverables"]), 6)

    def test_retrieval_failure_stops_after_three_retries_without_evidence(self):
        service = self._service(FailingRetrieval())
        mission = self._created(service)
        with self.assertRaises(RuntimeError):
            service.run(mission["id"])
        detail = service.detail(mission["id"])
        self.assertEqual(detail["status"], "FAILED")
        self.assertEqual(detail["retry_count"], 3)
        self.assertEqual(detail["evidence_refs"], [])
        retries = [item for item in detail["timeline"] if item["action"] == "Evidence Retrieval Retry"]
        self.assertEqual(len(retries), 3)

    def test_dashboard_counts_persisted_records_only(self):
        service = self._service()
        mission = service.run(self._created(service)["id"])
        dashboard = service.dashboard()
        self.assertEqual(dashboard["metrics"]["projects"], 1)
        self.assertEqual(dashboard["metrics"]["active_missions"], 1)
        self.assertEqual(dashboard["metrics"]["evidence_count"], 0)
        self.assertEqual(mission["evidence_refs"][0]["paper_id"], "authorized-paper")


if __name__ == "__main__":
    unittest.main()
