"""P62 tests for environment-aware, approval-bounded Computer Skill behavior."""

from __future__ import annotations

import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.computer_environment import ComputerEnvironmentState
from app.services.computer_action_planner import ComputerActionPlanner
from app.services.computer_environment_service import ComputerEnvironmentService
from app.services.computer_feedback_service import ComputerFeedbackService
from app.services.computer_observation_service import ComputerObservationService
from app.services.computer_recovery_service import ComputerRecoveryService
from app.services.identity_service import IdentityContext, IdentityError
from app.services.permission_middleware import PermissionMiddleware


class StubScanner:
    def scan(self):
        return {"workspace": {"root": "research_workspace", "file_count": 1, "document_count": 0},
                "project": {"project_name": "fixture", "technology": ["Python"]}}


class MissingIdentity:
    def context_for_token(self, _token):
        raise IdentityError("missing")


class ComputerEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        ComputerEnvironmentState.__table__.create(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.observer = ComputerObservationService(StubScanner())
        self.environments = ComputerEnvironmentService(self.sessions)
        self.feedback = ComputerFeedbackService(self.observer)
        self.recovery = ComputerRecoveryService()
        self.planner = ComputerActionPlanner()

    def tearDown(self):
        self.engine.dispose()

    def test_environment_state_is_created_with_safe_summary(self):
        result = self.environments.analyze_environment(
            self.observer.observe_environment(), mission_id="mission-1", workspace_id="workspace-1", goal="verify workspace"
        )
        stored = self.environments.get_state("mission-1", "workspace-1")
        self.assertEqual(result["vision_mode"], "demo_only")
        self.assertIsNotNone(stored)
        self.assertEqual(stored.page_state, "workspace_metadata_available")
        self.assertNotIn("prompt", stored.current_goal.lower())

    def test_environment_analysis_and_state_comparison(self):
        observation = self.observer.observe_environment()
        understanding = self.environments.analyze_environment(observation, mission_id="m", workspace_id=None, goal="browse")
        changed = self.observer.compare_environment({"page_state": understanding["current_state"]}, {"page_state": "verification_passed"})
        unchanged = self.observer.compare_environment({"page_state": "same"}, {"page_state": "same"})
        self.assertEqual(understanding["recommended_direction"], "先完成固定验证")
        self.assertEqual(changed["status"], "STATE_CHANGED")
        self.assertEqual(unchanged["status"], "NO_CHANGE")

    def test_semantic_environment_exposes_meaning_not_raw_content(self):
        semantic = self.environments.understand_environment(self.observer.observe_environment())
        self.assertIn("environment_type", semantic)
        self.assertIn("semantic_observations", semantic)
        self.assertEqual(semantic["risk_level"], "LOW")
        self.assertNotIn("profile", semantic)

    def test_success_feedback_and_failed_recovery(self):
        action = self.planner.plan_next_action(self.observer.observe_environment(), "browse authorized workspace")
        success = self.feedback.evaluate_action_result(action, {"page_state": "before"}, {"page_state": "after", "verification_status": "PASS"})
        failed = self.feedback.evaluate_action_result(action, {"page_state": "before"}, {"page_state": "after", "verification_status": "FAIL"})
        recovery = self.recovery.recover_failed_action(failed, action, 0)
        self.assertEqual(success["status"], "SUCCESS")
        self.assertEqual(failed["status"], "FAILED")
        self.assertIn(recovery["action"], {"ALTERNATIVE_ACTION", "STOP"})

    def test_recovery_is_limited_to_two_attempts(self):
        result = self.recovery.recover_failed_action({"status": "RETRY"}, {"fallback_action": "WAIT"}, 2)
        self.assertEqual(result["action"], "REQUEST_REVIEW")

    def test_high_risk_plan_requires_approval(self):
        plan = self.planner.plan_next_action(self.observer.observe_environment(), "upload report")
        self.assertTrue(plan["requires_approval"])
        self.assertEqual(plan["expected_change"], "FILE_AVAILABLE")
        self.assertEqual(plan["verification_method"], "CHECK_FILE_LIST")

    def test_workspace_isolation_and_identity_boundaries(self):
        self.environments.analyze_environment(self.observer.observe_environment(), mission_id="m", workspace_id="workspace-a", goal="verify")
        self.assertIsNone(self.environments.get_state("m", "workspace-b"))
        middleware = PermissionMiddleware(identities=MissingIdentity())
        with self.assertRaises(HTTPException) as missing:
            middleware.current(None)
        self.assertEqual(missing.exception.status_code, 401)
        context = IdentityContext("u", "u@example.test", "U", "workspace-a", "MEMBER", "s")
        with self.assertRaises(HTTPException) as denied:
            middleware._assert_workspace(context, "workspace-b", "COMPUTER_EXECUTE")
        self.assertEqual(denied.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
