"""P61 tests for finite, workspace-scoped Mission Intelligence."""

from __future__ import annotations

import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.autonomous_execution_service import AutonomousExecutionService
from app.services.database import Base
from app.services.identity_service import IdentityContext, IdentityError
from app.services.mission_intelligence_service import MissionIntelligenceService
from app.services.permission_middleware import PermissionMiddleware


class MissingIdentity:
    def context_for_token(self, _token):
        raise IdentityError("no session")


class MissionIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.service = MissionIntelligenceService(self.sessions, initialize=False)
        self.decisions = AutonomousExecutionService()
        self.mission_id = "mission-p61"; self.workspace_id = "workspace-p61"

    def tearDown(self):
        self.engine.dispose()

    def plan(self, goal="Analyze RAG research and prepare a proposal"):
        understanding = self.service.analyze_mission_goal(goal)
        return understanding, self.service.build_task_plan(self.mission_id, understanding)

    def test_goal_understanding_is_user_readable_and_has_no_reasoning_trace(self):
        understanding, _ = self.plan()
        self.assertIn("research", understanding["required_capabilities"])
        self.assertIn("delivery", understanding["required_capabilities"])
        self.assertNotIn("prompt", understanding)
        self.assertNotIn("chain_of_thought", understanding)

    def test_task_plan_uses_only_existing_skill_capabilities(self):
        _, plan = self.plan()
        self.assertEqual(plan[0]["required_skill"], "research")
        self.assertTrue(all(item["status"] in {"PENDING", "REVIEW_REQUIRED"} for item in plan))
        self.assertEqual(plan[-1]["required_skill"], "review")

    def test_evidence_insufficiency_creates_a_bounded_replan(self):
        _, plan = self.plan()
        self.service.ensure_state(self.mission_id, self.workspace_id, plan)
        state = self.service.replan_mission(self.mission_id, self.workspace_id, {"status": "NEEDS_EVIDENCE"}, 0)
        self.assertEqual(state["current_phase"], "REPLAN")
        self.assertEqual(state["replan_count"], 1)
        self.assertTrue(any(item["task_type"] == "RETRIEVE_EVIDENCE" for item in state["pending_tasks"]))

    def test_replan_limit_routes_to_human_review(self):
        _, plan = self.plan()
        self.service.ensure_state(self.mission_id, self.workspace_id, plan)
        self.service.replan_mission(self.mission_id, self.workspace_id, {}, 0)
        self.service.replan_mission(self.mission_id, self.workspace_id, {}, 0)
        state = self.service.replan_mission(self.mission_id, self.workspace_id, {}, 0)
        self.assertEqual(state["replan_count"], 2)
        self.assertEqual(state["current_phase"], "WAITING_REVIEW")
        self.assertEqual(state["blocked_reason"], "REPLAN_LIMIT_REACHED")

    def test_autonomous_decision_replans_then_requires_review(self):
        contract = {"workspace_id": self.workspace_id, "evidence_refs": []}
        first = self.decisions.decide_next_step(contract, {"replan_count": 0, "max_replan_count": 2}, {"status": "NEEDS_EVIDENCE"}, workspace_id=self.workspace_id)
        final = self.decisions.decide_next_step(contract, {"replan_count": 2, "max_replan_count": 2}, {"status": "NEEDS_EVIDENCE"}, workspace_id=self.workspace_id)
        self.assertEqual(first["decision"], "REPLAN")
        self.assertEqual(final["decision"], "REQUEST_REVIEW")

    def test_workspace_isolation_rejects_foreign_state(self):
        _, plan = self.plan(); self.service.ensure_state(self.mission_id, self.workspace_id, plan)
        with self.assertRaises(PermissionError):
            self.service.snapshot(self.mission_id, "workspace-other")

    def test_missing_identity_is_401(self):
        with self.assertRaises(HTTPException) as raised:
            PermissionMiddleware(identities=MissingIdentity()).current(None)
        self.assertEqual(raised.exception.status_code, 401)

    def test_cross_workspace_is_403_before_resource_access(self):
        context = IdentityContext("user", "user@example.com", "User", self.workspace_id, "MEMBER", "session")
        with self.assertRaises(HTTPException) as raised:
            PermissionMiddleware(identities=MissingIdentity())._assert_workspace(context, "foreign", "MISSION_VIEW")
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
