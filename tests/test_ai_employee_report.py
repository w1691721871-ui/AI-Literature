from __future__ import annotations

import unittest

from app.services.ai_employee_report_service import AIEmployeeReportService


class AIEmployeeReportTests(unittest.TestCase):
    def setUp(self):
        self.service = AIEmployeeReportService()

    def test_report_is_evidence_bound_and_user_readable(self):
        report = self.service.build(
            {"id": "mission-1", "title": "Low-carbon materials", "status": "WAITING_REVIEW", "evidence_refs": [{"paper_id": "p1"}]},
            [{"skill": "Research Skill", "status": "SUCCESS", "result_summary": "Traceable sources were collected."}, {"skill": "Review Skill", "status": "WAITING_REVIEW"}],
        )
        self.assertEqual(report["status"], "Waiting for your review")
        self.assertEqual(report["evidence"]["count"], 1)
        self.assertEqual(report["completed"][0]["area"], "Research Skill")
        self.assertIn("review", report["next_step"].lower())

    def test_report_never_claims_grounded_research_without_evidence(self):
        report = self.service.build({"id": "mission-2", "status": "PLANNING", "evidence_refs": []}, [])
        self.assertIn("cannot make a grounded", report["evidence"]["summary"])
        self.assertIn("Evidence", report["next_step"])

    def test_report_excludes_internal_reasoning_fields(self):
        report = self.service.build({"id": "mission-3", "status": "CREATED", "evidence_refs": []}, [])
        serialized = str(report).lower()
        self.assertNotIn("input_prompt", serialized)
        self.assertNotIn("reasoning_trace", serialized)


if __name__ == "__main__":
    unittest.main()
