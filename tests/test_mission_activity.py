"""Mission Activity Timeline exposes persisted product summaries only."""

from __future__ import annotations

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission, AIMissionEvent
from app.services.database import Base
from app.services.mission_activity_service import MissionActivityService


class MissionActivityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine); self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        session = self.sessions()
        session.add(AIMission(id="activity-a", title="Activity", goal="Evidence", workspace_id="workspace-a", status="WAITING_REVIEW", current_step="Human Review"))
        session.add(AIMissionEvent(mission_id="activity-a", stage="Evidence Retrieval", action="Evidence ready", status="WAITING_REVIEW", evidence_count=2, result_summary="Two traceable Evidence references are ready for review."))
        session.commit(); session.close(); self.service = MissionActivityService(self.sessions, initialize=False)

    def tearDown(self): self.engine.dispose()

    def test_activity_is_workspace_scoped_and_user_readable(self):
        result = self.service.timeline("activity-a", "workspace-a")
        self.assertEqual(result["current_phase"], "Needs review")
        self.assertEqual(result["activities"][0]["status"], "WAITING")
        self.assertNotIn("prompt", result["activities"][0])
        self.assertNotIn("reasoning", result["activities"][0])
        with self.assertRaises(PermissionError): self.service.timeline("activity-a", "workspace-b")

    def test_next_best_action_is_derived_from_reviewable_state(self):
        result = self.service.timeline("activity-a", "workspace-a")
        recommendation = result["next_best_action"]
        self.assertEqual(recommendation["action"], "OPEN_REVIEW")
        self.assertIn("review", recommendation["label"].lower())
        self.assertNotIn("prompt", recommendation)
        self.assertNotIn("reasoning", recommendation)


if __name__ == "__main__": unittest.main()
