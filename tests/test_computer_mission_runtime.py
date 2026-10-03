import unittest

from app.services.computer_mission_runtime import ComputerMissionRuntime


class ComputerMissionRuntimeTests(unittest.TestCase):
    def test_waiting_approval_is_presented_as_controlled_worker_state(self):
        snapshot = ComputerMissionRuntime().summarize([{
            "id": "computer-1", "task": "Prepare research sources", "status": "WAITING_APPROVAL",
            "approval_status": "PENDING", "action_plan": {"normalized_observation": {"vision_mode": "demo_only", "page_state": "workspace_metadata_available", "available_actions": ["VERIFY"]}, "controlled_action": {"action_type": "INPUT"}},
            "verification": {},
        }])
        self.assertEqual(snapshot["status"], "WAITING_APPROVAL")
        self.assertEqual(snapshot["stages"][2]["status"], "REQUIRED")
        self.assertNotIn("diff_content", str(snapshot))

    def test_failed_verification_requires_review_not_a_false_success(self):
        snapshot = ComputerMissionRuntime().summarize([{
            "id": "computer-1", "task": "Prepare report", "status": "NEEDS_REVISION", "approval_status": "APPROVED",
            "action_plan": {}, "verification": {"controlled_verification": {"status": "FAILED", "summary": "Verification did not pass."}, "recovery": {"action": "REQUEST_REVIEW", "summary": "Human choice required."}},
        }])
        self.assertEqual(snapshot["status"], "NEEDS_REVIEW")
        self.assertEqual(snapshot["verification"]["status"], "NEEDS_REVIEW")
        self.assertEqual(snapshot["recovery"]["status"], "REQUEST_REVIEW")

    def test_no_mission_has_no_synthesized_execution(self):
        self.assertIsNone(ComputerMissionRuntime().summarize([]))
