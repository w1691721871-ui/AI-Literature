"""Long-running Mission controls remain Workspace-bound and review-safe."""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.mission_control import MissionControlState
from app.services.database import Base
from app.services.mission_lifecycle_service import MissionLifecycleError, MissionLifecycleService


class MissionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        session = self.sessions()
        try:
            session.add_all([
                AIMission(id="mission-a", title="Long mission", goal="Evidence review", workspace_id="workspace-a", status="PLANNING"),
                AIMission(id="mission-b", title="Foreign mission", goal="Other", workspace_id="workspace-b", status="PLANNING"),
            ])
            session.commit()
        finally:
            session.close()
        self.lifecycle = MissionLifecycleService(self.sessions, initialize=False)

    def tearDown(self):
        self.engine.dispose()

    def test_pause_and_resume_preserve_the_existing_mission_boundary(self):
        paused = self.lifecycle.pause("mission-a", "workspace-a", "user-a", "Waiting for customer materials")
        self.assertEqual(paused["status"], "PAUSED")
        self.assertEqual(paused["pause_reason"], "Waiting for customer materials")
        resumed = self.lifecycle.resume("mission-a", "workspace-a", "user-a")
        self.assertEqual(resumed["status"], "PLANNING")
        self.assertEqual(resumed["next_action"], "Continue within existing controls")

    def test_failed_mission_recovery_is_bounded_and_requires_revision(self):
        session = self.sessions()
        try:
            session.get(AIMission, "mission-a").status = "FAILED"; session.commit()
        finally:
            session.close()
        first = self.lifecycle.recover("mission-a", "workspace-a", "user-a")
        self.assertEqual(first["status"], "NEEDS_REVISION")
        self.assertEqual(first["recovery_count"], 1)
        session = self.sessions()
        try:
            mission = session.get(AIMission, "mission-a")
            mission.status = "FAILED"; session.commit()
        finally:
            session.close()
        self.lifecycle.recover("mission-a", "workspace-a", "user-a")
        session = self.sessions()
        try:
            session.get(AIMission, "mission-a").status = "FAILED"; session.commit()
        finally:
            session.close()
        with self.assertRaises(MissionLifecycleError):
            self.lifecycle.recover("mission-a", "workspace-a", "user-a")

    def test_control_state_cannot_cross_workspace(self):
        with self.assertRaises(PermissionError):
            self.lifecycle.pause("mission-b", "workspace-a", "user-a")

    def test_control_state_is_persisted_without_prompt_or_reasoning_fields(self):
        self.lifecycle.snapshot("mission-a", "workspace-a")
        self.assertEqual(set(MissionControlState.__table__.columns.keys()), {
            "id", "mission_id", "workspace_id", "prior_status", "paused_by_id", "pause_reason",
            "recovery_count", "max_recoveries", "created_at", "updated_at",
        })


if __name__ == "__main__":
    unittest.main()
