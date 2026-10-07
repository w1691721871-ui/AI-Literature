"""Experience can suggest, but never override, a safe Computer route."""

from __future__ import annotations

import unittest

from app.services.computer_strategy_service import ComputerStrategyService


class ComputerExperienceLearningTests(unittest.TestCase):
    def setUp(self):
        self.mission = {"id": "m1", "workspace_id": "w1", "goal": "Research recent low carbon materials papers"}
        self.execution = {"status": "READY", "observation": {"state": "public research", "vision_mode": "demo_only"}}

    def test_low_confidence_memory_does_not_change_safe_strategy_order(self):
        context = {"knowledge": {"traceable_evidence_refs": []}, "artifacts": [], "computer_memory": [{"memory_type": "TASK_EXPERIENCE", "strategy_hint": "PUBLIC_DISCOVERY", "confidence": "LOW"}]}
        result = ComputerStrategyService().build(self.mission, context, self.execution)
        self.assertEqual(result["strategy"]["id"], "PUBLIC_DISCOVERY")
        self.assertEqual(result["experience_guidance"]["suggested_strategy"], "")

    def test_repeatedly_validated_memory_can_suggest_matching_safe_route(self):
        context = {"knowledge": {"traceable_evidence_refs": []}, "artifacts": [], "computer_memory": [{"memory_type": "TASK_EXPERIENCE", "strategy_hint": "PUBLIC_DISCOVERY", "confidence": "MEDIUM"}]}
        result = ComputerStrategyService().build(self.mission, context, self.execution)
        self.assertEqual(result["strategy"]["id"], "PUBLIC_DISCOVERY")
        self.assertEqual(result["experience_guidance"]["suggested_strategy"], "PUBLIC_DISCOVERY")
        self.assertEqual(result["decision"]["action"], "EXECUTE")

    def test_memory_never_bypasses_existing_review_boundary(self):
        context = {"knowledge": {"traceable_evidence_refs": []}, "artifacts": [], "computer_memory": [{"memory_type": "TASK_EXPERIENCE", "strategy_hint": "PUBLIC_DISCOVERY", "confidence": "HIGH"}]}
        result = ComputerStrategyService().build(self.mission, context, {"status": "WAITING_APPROVAL", "observation": {}})
        self.assertEqual(result["strategy"]["id"], "HUMAN_REVIEW")
        self.assertEqual(result["decision"]["action"], "WAIT_REVIEW")


if __name__ == "__main__":
    unittest.main()
