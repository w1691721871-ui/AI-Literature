"""Durability tests: checkpoints survive a new service instance and never replay uncertainty."""

from __future__ import annotations

import unittest
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.database import Base
from app.services.persistent_mission_execution_service import PersistentMissionExecutionService
from app.models.mission_execution_checkpoint import MissionExecutionLease


class PersistentMissionExecutionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.mission = {"id": "durable-mission", "workspace_id": "durable-workspace", "goal": "Collect verified public research evidence"}

    def tearDown(self):
        self.engine.dispose()

    def test_checkpoint_survives_new_worker_and_completed_action_is_idempotent(self):
        first = PersistentMissionExecutionService(self.sessions, initialize=False, worker_id="one")
        first.checkpoint(self.mission, phase="PLANNING", objective="Plan research", next_action="Research")
        started = first.begin_action(self.mission, "research-1", "SKILL", objective="Collect evidence")
        self.assertTrue(started["execute"])
        first.observe_action(self.mission["id"], "Public candidates were collected.")
        first.verify_action(self.mission["id"], step_id="research-1", observation="Candidates collected.", evaluation="Ready for review.", success=True)

        restarted = PersistentMissionExecutionService(self.sessions, initialize=False, worker_id="two")
        checkpoint = restarted.snapshot(self.mission["id"], self.mission["workspace_id"])
        self.assertEqual(checkpoint["completed_steps"], ["research-1"])
        replay = restarted.begin_action(self.mission, "research-1", "SKILL", objective="Collect evidence")
        self.assertFalse(replay["execute"])

    def test_started_action_after_restart_requires_review_not_replay(self):
        service = PersistentMissionExecutionService(self.sessions, initialize=False)
        service.checkpoint(self.mission, phase="EXECUTING", objective="Collect evidence")
        service.begin_action(self.mission, "research-1", "SKILL", objective="Collect evidence")
        result = PersistentMissionExecutionService(self.sessions, initialize=False).recovery_scan()
        checkpoint = service.snapshot(self.mission["id"], self.mission["workspace_id"])
        self.assertEqual(result["waiting_review"], 1)
        self.assertEqual(checkpoint["resume_policy"], "NEEDS_REVIEW")
        self.assertIn("restarted", checkpoint["waiting_reason"].lower())

    def test_paused_or_completed_work_is_not_selected_for_restart_recovery(self):
        service = PersistentMissionExecutionService(self.sessions, initialize=False)
        service.checkpoint(self.mission, phase="COMPLETED", objective="Completed", resume_policy="RESUME_ELIGIBLE")
        result = service.recovery_scan()
        checkpoint = service.snapshot(self.mission["id"], self.mission["workspace_id"])
        self.assertEqual(result, {"resume_eligible": 0, "waiting_review": 0})
        self.assertEqual(checkpoint["phase"], "COMPLETED")

    def test_duplicate_active_worker_cannot_claim_mission(self):
        first = PersistentMissionExecutionService(self.sessions, initialize=False, worker_id="one")
        second = PersistentMissionExecutionService(self.sessions, initialize=False, worker_id="two")
        self.assertTrue(first.claim(self.mission))
        self.assertFalse(second.claim(self.mission))
        first.release(self.mission["id"])
        self.assertTrue(second.claim(self.mission))

    def test_expired_lease_can_be_safely_claimed_by_new_worker(self):
        first = PersistentMissionExecutionService(self.sessions, initialize=False, worker_id="one")
        second = PersistentMissionExecutionService(self.sessions, initialize=False, worker_id="two")
        self.assertTrue(first.claim(self.mission))
        session = self.sessions()
        try:
            row = session.query(MissionExecutionLease).filter_by(mission_id=self.mission["id"]).one()
            row.lease_expires_at = PersistentMissionExecutionService._now() - timedelta(seconds=1)
            session.commit()
        finally:
            session.close()
        self.assertTrue(second.claim(self.mission))

    def test_recovery_marks_safe_boundary_resumable_without_executing_it(self):
        service = PersistentMissionExecutionService(self.sessions, initialize=False)
        service.checkpoint(self.mission, phase="PLANNING", objective="Plan a bounded read-only step")
        result = PersistentMissionExecutionService(self.sessions, initialize=False).recovery_scan()
        checkpoint = service.snapshot(self.mission["id"], self.mission["workspace_id"])
        self.assertEqual(result["resume_eligible"], 1)
        self.assertEqual(checkpoint["phase"], "RECOVERING")
        self.assertEqual(checkpoint["resume_policy"], "RESUME_ELIGIBLE")

    def test_checkpoint_is_workspace_isolated(self):
        service = PersistentMissionExecutionService(self.sessions, initialize=False)
        service.checkpoint(self.mission, phase="PLANNING")
        self.assertIsNone(service.snapshot(self.mission["id"], "another-workspace"))


if __name__ == "__main__":
    unittest.main()
