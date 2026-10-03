"""P59 tests for finite autonomous decisions without production side effects."""

from __future__ import annotations

import unittest

from app.services.autonomous_execution_service import AutonomousExecutionService


class AutonomousExecutionTests(unittest.TestCase):
    def setUp(self):
        self.service = AutonomousExecutionService()
        self.contract = {
            "workspace_id": "workspace-p59",
            "evidence_refs": [{"paper_id": "paper-1", "chunk_id": "chunk-1"}],
            "approval_state": "HUMAN_REVIEW_REQUIRED",
        }

    def decide(self, observation, state=None, contract=None, workspace_id="workspace-p59"):
        return self.service.evaluate_current_state(
            contract or self.contract,
            state or {"completed_steps": 1},
            observation,
            workspace_id=workspace_id,
        )

    def test_normal_execution_continues_to_evidence_assessment(self):
        result = self.decide({"status": "SUCCESS", "action_type": "COLLECT_EVIDENCE"})
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["action"], "ANALYZE_GAP")
        self.assertEqual(result["skill"], "research")

    def test_evidence_insufficiency_stops_at_review_boundary(self):
        result = self.decide(
            {"status": "NEEDS_EVIDENCE", "action_type": "COLLECT_EVIDENCE"},
            contract={"workspace_id": "workspace-p59", "evidence_refs": []},
        )
        self.assertEqual(result["decision"], "REQUEST_REVIEW")
        self.assertEqual(result["stop_reason"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["action"], "REQUEST_APPROVAL")

    def test_max_step_limit_stops_before_more_work(self):
        result = self.decide(
            {"status": "SUCCESS", "action_type": "COLLECT_EVIDENCE"},
            state={"completed_steps": 5, "max_steps": 5},
        )
        self.assertEqual(result["decision"], "STOP")
        self.assertEqual(result["stop_reason"], "MAX_STEPS_REACHED")

    def test_review_boundary_is_never_auto_approved(self):
        result = self.decide({"status": "WAITING_REVIEW", "action_type": "REQUEST_APPROVAL"})
        self.assertEqual(result["decision"], "REQUEST_REVIEW")
        self.assertEqual(result["stop_reason"], "HUMAN_REVIEW_REQUIRED")

    def test_workspace_scope_is_rejected(self):
        result = self.decide(
            {"status": "SUCCESS", "action_type": "COLLECT_EVIDENCE"},
            workspace_id="other-workspace",
        )
        self.assertEqual(result["decision"], "STOP")
        self.assertEqual(result["stop_reason"], "WORKSPACE_SCOPE_DENIED")


if __name__ == "__main__":
    unittest.main()
