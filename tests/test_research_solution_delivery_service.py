"""Fixture-only checks for P5 solution delivery views."""

from __future__ import annotations

import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.research_memory import ResearchMemory
from app.models.research_task import ResearchTask
from app.models.research_workspace import ResearchWorkspace
from app.services.database import Base
from app.services.research_solution_delivery_service import ResearchSolutionDeliveryService


class ResearchSolutionDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.service = ResearchSolutionDeliveryService(self.sessions, initialize=False)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_scenarios_and_blueprint_are_explicit_demo_proposals(self) -> None:
        scenarios = self.service.list_scenarios()
        self.assertEqual(len(scenarios), 3)
        blueprint = self.service.blueprint("enterprise_rd_research")
        self.assertEqual(blueprint["scenario"]["customer_type"], "企业研发部门")
        self.assertIn("不会自动配置客户系统", blueprint["boundary"])

    def test_roi_uses_real_fixture_counts_and_makes_no_roi_claim(self) -> None:
        session = self.sessions()
        try:
            session.add(Paper(paper_id="paper-fixture", title="Fixture", filename="fixture.pdf", file_path="fixture.pdf", text_content="", analysis_status="ready", quality_status="ready", document_type="paper"))
            session.add(PaperChunk(id="chunk-fixture", paper_id="paper-fixture", chunk_index=0, section_title="Method", content="Fixture source", embedding="[0.1]"))
            session.add(ResearchWorkspace(id="workspace-fixture", name="Fixture workspace", member_roles="[]"))
            session.add(ResearchTask(id="task-fixture", workspace_id="workspace-fixture", name="Fixture task", task_type="文献分析"))
            session.add(ResearchMemory(scope="research_workspace:workspace-fixture", memory_json=json.dumps({"review_items": [{"status": "pending"}]})))
            session.commit()
        finally:
            session.close()
        roi = self.service.roi_dashboard()
        self.assertEqual(roi["research_assets"]["papers"], 1)
        self.assertEqual(roi["research_assets"]["evidence"], 1)
        self.assertEqual(roi["research_topic_coverage"]["status"], "not_evaluated")
        self.assertIn("不代表", roi["boundary"])
        self.assertEqual(self.service.admin_overview()["review_status"]["pending"], 1)

    def test_delivery_report_reuses_counts_without_claiming_customer_validation(self) -> None:
        report = self.service.delivery_report("joint_research_proposal")
        self.assertIn("Customer Delivery Report", report["title"])
        self.assertIn("资料", report["validation_result"][0])
        self.assertIn("需客户确认", report["boundary"])

    def test_demo_flow_carries_real_counts_without_creating_demo_records(self) -> None:
        before = self.service.admin_overview()
        flow = self.service.demo_flow("university_lab_management")
        after = self.service.admin_overview()
        self.assertTrue(flow["is_demo"])
        self.assertEqual(len(flow["steps"]), 6)
        self.assertEqual(flow["steps"][0]["evidence_count"], before["evidence_count"])
        self.assertEqual(before, after)
        self.assertIn("不会创建 Workspace", flow["boundary"])


if __name__ == "__main__":
    unittest.main()
