"""P19 deterministic intelligence fixtures; no source or production data access."""
import unittest
from app.services.computer_intelligence_service import ComputerIntelligenceService

class ComputerIntelligenceLayerTests(unittest.TestCase):
    def setUp(self): self.service=ComputerIntelligenceService.__new__(ComputerIntelligenceService)
    def test_code_review_warning_and_diff_summary(self):
        change={"file_path":"frontend/app.js","operation":"APPEND","diff":"+console.log('debug')\n"}
        self.assertEqual(self.service.review(change)["status"],"WARNING")
        self.assertEqual(self.service.diff_summary([change])["impact"],"Frontend only")
    def test_verification_planner_selects_frontend_and_python(self):
        plan=self.service.verification_plan([{ "file_path":"frontend/app.js"},{"file_path":"app/main.py"}])
        self.assertEqual(len(plan),2)
    def test_skill_catalog_has_risk_metadata(self):
        self.assertTrue(all("risk" in skill for skill in self.service.skills()))

    def test_sensitive_memory_is_rejected_before_persistence(self):
        with self.assertRaises(ValueError):
            self.service.remember("workspace-a", "USER_PREFERENCE", "api_key=not-allowed")

if __name__ == "__main__": unittest.main()
