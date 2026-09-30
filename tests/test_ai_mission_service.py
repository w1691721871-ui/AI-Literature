"""P22 Mission Center tests use only a disposable in-memory SQLite database."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.computer_mission import ComputerMission
from app.models.agent_trace import AgentTrace
from app.models.notification import Notification
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.solution_deliverable import SolutionDeliverable
from app.models.solution_project import SolutionProject
from app.services.ai_mission_service import AIMissionService


class AIMissionServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        for table in (AIMission.__table__, AIMissionEvent.__table__, AgentTrace.__table__, ComputerMission.__table__, Notification.__table__, Paper.__table__, PaperChunk.__table__, SolutionProject.__table__, SolutionDeliverable.__table__):
            table.create(self.engine)
        self.service = AIMissionService(self.Session, initialize=False)

    def tearDown(self):
        self.engine.dispose()

    def test_create_mission_starts_auditable_planning_without_evidence(self):
        mission = self.service.create({"title": "Review RAG direction", "mission_type": "RESEARCH", "goal": "Compare methods"})
        self.assertEqual(mission["status"], "PLANNING")
        timeline = self.service.timeline(mission["id"])
        self.assertEqual(len(timeline), 2)
        self.assertTrue(all(item["evidence_count"] == 0 for item in timeline))
        self.assertIn("尚未发起检索", timeline[-1]["result"])

    def test_detail_has_team_and_non_fabricated_evidence_graph(self):
        mission = self.service.create({"title": "Research task", "mission_type": "RESEARCH", "goal": ""})
        detail = self.service.detail(mission["id"])
        self.assertEqual(len(detail["team"]), 6)
        self.assertEqual(detail["evidence_graph"]["nodes"][1]["label"], "尚未关联 Evidence")

    def test_notifications_are_persisted_and_markable(self):
        self.service.create({"title": "Notify", "mission_type": "RESEARCH", "goal": ""})
        notification = self.service.notifications()[0]
        self.assertFalse(notification["read"])
        self.assertTrue(self.service.mark_notification_read(notification["id"])["read"])

    def test_dashboard_uses_real_fixture_counts(self):
        session = self.Session()
        session.add(Paper(paper_id="fixture-paper", title="Authorized fixture", filename="fixture.pdf", file_path="/fixture.pdf", text_content="text", analysis_status="ready", quality_status="ready"))
        session.add(PaperChunk(id="fixture-chunk", paper_id="fixture-paper", chunk_index=0, section_title="Method", content="fixture", embedding="[0.1]"))
        session.commit(); session.close()
        self.service.create({"title": "Count", "mission_type": "RESEARCH", "goal": ""})
        dashboard = self.service.dashboard()
        self.assertEqual(dashboard["metrics"]["knowledge_size"], 1)
        self.assertEqual(dashboard["metrics"]["evidence_count"], 1)
        self.assertEqual(dashboard["metrics"]["active_missions"], 1)


if __name__ == "__main__":
    unittest.main()
