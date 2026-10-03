"""Read-only adapter tests for the unified AI Worker product contract."""

from __future__ import annotations

import unittest

from app.services.ai_worker_service import AIWorkerService


class AIWorkerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AIWorkerService()

    def test_capability_catalog_has_one_worker_and_four_skills(self) -> None:
        catalog = self.service.capabilities()
        self.assertEqual(catalog["worker"]["name"], "AI Worker")
        self.assertEqual(
            [item["name"] for item in catalog["skills"]],
            ["Research Skill", "Computer Skill", "Delivery Skill", "Review Skill"],
        )

    def test_contract_adapts_existing_mission_without_exposing_internal_agents(self) -> None:
        contract = self.service.contract_for_mission({
            "id": "mission-1",
            "title": "Compare indexed research methods",
            "status": "WAITING_REVIEW",
            "current_step": "Human Review",
            "evidence_refs": [{"paper_id": "paper-1", "chunk_id": "chunk-1"}],
        })
        self.assertEqual(contract.objective, "Compare indexed research methods")
        self.assertEqual(contract.context["evidence_count"], 1)
        self.assertEqual(contract.approval_requirement, "HUMAN_REVIEW_REQUIRED")
        self.assertNotIn("Research Agent", str(contract.model_dump()))

    def test_failed_mission_preserves_stop_reason(self) -> None:
        contract = self.service.contract_for_mission({"title": "Blocked", "status": "FAILED"})
        self.assertEqual(contract.stop_reason, "FAILED")
        self.assertEqual(contract.status, "FAILED")


if __name__ == "__main__":
    unittest.main()
