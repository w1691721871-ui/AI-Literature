import unittest

from app.services.computer_strategy_service import ComputerStrategyService


class ComputerStrategyServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = ComputerStrategyService()
        self.mission = {"id": "mission-a", "workspace_id": "workspace-a", "goal": "Organize research papers and prepare a report", "evidence_refs": ["e-1"], "source_materials": [{"id": "file-a"}]}
        self.context = {
            "workspace": {"id": "workspace-a"},
            "knowledge": {"traceable_evidence_refs": ["e-1"]},
            "computer_memory": [{"memory_type": "USER_PREFERENCE", "summary": "Use a concise brief."}],
            "artifacts": [],
        }

    def test_strategy_selects_authorized_material_before_public_discovery(self):
        result = self.service.build(self.mission, self.context, {"status": "READY", "observation": {"state": "workspace metadata", "vision_mode": "demo_only"}})
        self.assertEqual(result["strategy"]["id"], "AUTHORIZED_MATERIAL")
        self.assertEqual(result["decision"]["action"], "EXECUTE")
        self.assertEqual(result["workspace_state"]["available_resources"]["authorized_computer_memory"], 1)
        self.assertEqual(result["employee_summary"]["quality_status"], "IN_PROGRESS")
        self.assertNotIn("concise brief", str(result))

    def test_strategy_does_not_claim_authorized_material_when_none_is_attached(self):
        mission = {key: value for key, value in self.mission.items() if key != "source_materials"}
        result = self.service.build(mission, self.context, {"status": "READY", "observation": {}})
        self.assertEqual(result["strategy"]["id"], "PUBLIC_DISCOVERY")

    def test_existing_review_boundary_cannot_be_bypassed(self):
        result = self.service.build(self.mission, self.context, {"status": "WAITING_APPROVAL", "observation": {}})
        self.assertEqual(result["strategy"]["id"], "HUMAN_REVIEW")
        self.assertEqual(result["decision"]["action"], "WAIT_REVIEW")

    def test_quality_does_not_claim_unreviewed_delivery_is_final(self):
        result = self.service.build(self.mission, self.context, {"status": "COMPLETED", "artifact": {"title": "Brief", "evidence_count": 1}, "observation": {}})
        self.assertEqual(result["quality"]["status"], "REVIEWABLE")
        self.assertIn("review", result["quality"]["summary"].lower())

    def test_experience_guidance_reports_only_safe_memory_metadata(self):
        self.context["computer_memory"].append({"memory_type": "FAILURE_LEARNING", "summary": "No raw detail."})
        result = self.service.build(self.mission, self.context, {"status": "READY", "observation": {}})
        self.assertEqual(result["experience_guidance"]["available"], 1)
        self.assertNotIn("No raw detail", str(result))


if __name__ == "__main__":
    unittest.main()
