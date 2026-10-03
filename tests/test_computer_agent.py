"""P60 tests for the controlled Computer Skill decision layer."""

from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.services.computer_action_planner import ComputerActionPlanner
from app.services.computer_observation_service import ComputerObservationService
from app.services.computer_verification_service import ComputerVerificationService
from app.services.identity_service import IdentityContext, IdentityError
from app.services.permission_middleware import PermissionMiddleware


class StubScanner:
    def scan(self):
        return {
            "workspace": {"root": "research_workspace", "file_count": 2, "document_count": 1},
            "project": {"project_name": "fixture", "technology": ["Python", "FastAPI"]},
        }


class MissingIdentity:
    def context_for_token(self, _token):
        raise IdentityError("missing session")


class ComputerAgentTests(unittest.TestCase):
    def setUp(self):
        self.observer = ComputerObservationService(StubScanner())
        self.planner = ComputerActionPlanner()
        self.verifier = ComputerVerificationService()

    def test_observation_is_explicitly_demo_only_without_visual_input(self):
        observation = self.observer.observe_environment({"goal": "browse research workspace"})
        self.assertEqual(observation["status"], "OBSERVED")
        self.assertEqual(observation["vision_mode"], "demo_only")
        self.assertIn("VERIFY", observation["available_actions"])
        self.assertNotIn("DELETE", observation["available_actions"])

    def test_normalized_observation_omits_raw_environment_profile(self):
        normalized = self.observer.normalize_observation(self.observer.observe_environment({"goal": "browse research workspace"}))
        self.assertEqual(normalized["vision_mode"], "demo_only")
        self.assertIn("document_state", normalized)
        self.assertNotIn("profile", normalized)
        self.assertNotIn("workspace", normalized)

    def test_high_risk_action_requires_approval(self):
        plan = self.planner.plan_next_action(self.observer.observe_environment(), "上传 a report to an external portal")
        self.assertEqual(plan["action_type"], "UPLOAD")
        self.assertTrue(plan["requires_approval"])
        self.assertEqual(plan["risk_level"], "HIGH")

    def test_low_risk_navigation_is_planned_without_approval(self):
        plan = self.planner.plan_next_action(self.observer.observe_environment(), "browse the authorized research workspace")
        self.assertEqual(plan["action_type"], "NAVIGATE")
        self.assertFalse(plan["requires_approval"])

    def test_failed_verification_requests_rollback_boundary(self):
        verification = self.verifier.verify_action_result({"status": "APPROVED"}, {"status": "FAIL"}, "update a controlled file")
        self.assertEqual(verification["status"], "FAILED")
        self.assertTrue(verification["rollback_required"])

    def test_cross_workspace_resource_is_rejected_before_permission_check(self):
        context = IdentityContext("user-1", "user@example.com", "User", "workspace-a", "MEMBER", "session-1")
        middleware = PermissionMiddleware(identities=MissingIdentity())
        with self.assertRaises(HTTPException) as raised:
            middleware._assert_workspace(context, "workspace-b", "COMPUTER_EXECUTE")
        self.assertEqual(raised.exception.status_code, 403)

    def test_missing_identity_returns_401(self):
        middleware = PermissionMiddleware(identities=MissingIdentity())
        with self.assertRaises(HTTPException) as raised:
            middleware.current(None)
        self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
