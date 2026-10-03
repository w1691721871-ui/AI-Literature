"""Computer Skill catalog must remain bounded and approval-aware."""

import unittest

from app.services.computer_skill_registry import ComputerSkillRegistry


class ComputerSkillRegistryTests(unittest.TestCase):
    def test_catalog_is_explicit_and_never_claims_unbounded_computer_use(self):
        catalog = ComputerSkillRegistry().catalog()
        self.assertEqual({item["id"] for item in catalog}, {"browser_research", "document_preparation", "data_operation", "report_preparation"})
        self.assertTrue(all("permission" in item and "risk_level" in item for item in catalog))
        self.assertNotIn("shell", str(catalog).lower())

    def test_goal_matching_selects_existing_skills_only(self):
        selected = ComputerSkillRegistry().match("Analyze a data table and prepare a research report")
        self.assertEqual([item["id"] for item in selected], ["browser_research", "data_operation", "report_preparation"])
        self.assertTrue(all(item["id"] != "browser_research" or not item["approval_required"] for item in selected))


if __name__ == "__main__":
    unittest.main()
