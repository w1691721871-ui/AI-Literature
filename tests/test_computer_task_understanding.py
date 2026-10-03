import unittest

from app.services.computer_task_understanding_service import ComputerTaskUnderstandingService


class ComputerTaskUnderstandingTests(unittest.TestCase):
    def test_research_goal_requires_traceable_evidence_boundary(self):
        result = ComputerTaskUnderstandingService().understand("Organize recent low carbon concrete research trends")
        self.assertEqual(result["task_type"], "RESEARCH_COLLECTION")
        self.assertIn("browser_research", result["required_skills"])
        self.assertIn("Evidence", result["required_environment"])
        self.assertNotIn("prompt", str(result).lower())

    def test_modifying_goal_requires_human_approval(self):
        result = ComputerTaskUnderstandingService().understand("Update the approved project document")
        self.assertEqual(result["risk_level"], "HIGH")
        self.assertTrue(result["approval_required"])
