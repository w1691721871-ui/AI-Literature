"""P21 FDE Solution Studio uses a disposable SQLite fixture and no FAISS writes."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.fde_solution_agent import FDESolutionAgent
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.solution_deliverable import SolutionDeliverable
from app.models.solution_project import SolutionProject
from app.models.solution_requirement import SolutionRequirement
from app.models.solution_computer_mission import SolutionComputerMission
from app.models.solution_version import SolutionVersion
from app.services.fde_solution_service import FDESolutionService


class FDESolutionAgentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        for table in (Paper.__table__, PaperChunk.__table__, SolutionProject.__table__, SolutionRequirement.__table__, SolutionDeliverable.__table__, SolutionComputerMission.__table__, SolutionVersion.__table__):
            table.create(self.engine)
        session = self.Session()
        session.add(Paper(paper_id="real-fixture-paper", title="Authorized Fixture Paper", filename="fixture.pdf", file_path="/fixture/authorized.pdf", text_content="Fixture text", analysis_status="ready", quality_status="ready"))
        session.add(PaperChunk(id="real-fixture-chunk", paper_id="real-fixture-paper", chunk_index=0, section_title="Method", content="A real fixture excerpt.", embedding="[0.1]"))
        session.commit(); session.close()
        self.service = FDESolutionService(self.Session, initialize=False)
        self.agent = FDESolutionAgent(self.service)
        self.project = self.service.create({"title": "University Knowledge Platform", "customer_need": "科研资料分散且研究方向难追踪", "industry": "Higher Education", "objective": "建立可审阅的知识与研究流程"})

    def tearDown(self):
        self.engine.dispose()

    def test_create_and_parse_requirements_as_draft(self):
        result = self.agent.understand_requirements(self.project["id"])
        self.assertEqual(len(result["requirements"]), 6)
        self.assertTrue(all(item["status"] == "NEEDS_CONFIRMATION" for item in result["requirements"]))

    def test_gap_analysis_uses_available_fixture_data(self):
        result = self.agent.understand_requirements(self.project["id"])
        self.assertEqual(result["gap_analysis"]["knowledge_base"]["status"], "AVAILABLE")
        self.assertEqual(result["gap_analysis"]["authentication"]["status"], "MISSING")

    def test_architecture_only_describes_installed_components(self):
        architecture = self.service.architecture(self.project["id"])
        self.assertIn("FastAPI", architecture["components"]["backend"])
        self.assertNotIn("Milvus", str(architecture))

    def test_blueprint_binds_real_fixture_evidence(self):
        self.agent.understand_requirements(self.project["id"])
        blueprint = self.agent.prepare_solution(self.project["id"])["blueprint"]
        self.assertEqual(blueprint["evidence_refs"][0]["chunk_id"], "real-fixture-chunk")
        self.assertEqual(blueprint["label"], "AI Generated Draft · NEEDS_CONFIRMATION")

    def test_risk_requires_human_review(self):
        risks = self.service.risks(self.project["id"])["risks"]
        self.assertTrue(all(item["requires_human_review"] == "true" for item in risks))

    def test_review_and_delivery_package_are_not_automatic_customer_delivery(self):
        with self.assertRaisesRegex(ValueError, "尚未批准"):
            self.service.delivery_package(self.project["id"])
        self.agent.understand_requirements(self.project["id"]); self.agent.prepare_solution(self.project["id"])
        reviewed = self.service.review(self.project["id"], "APPROVED", "fixture reviewer")
        self.assertEqual(reviewed["review_status"], "APPROVED")
        package = self.service.delivery_package(self.project["id"])
        self.assertEqual(package["label"], "Human Reviewed · AI Generated Draft · NEEDS_CONFIRMATION")
        self.assertIn("客户确认", " ".join(package["acceptance_criteria"]))

    def test_metrics_reflect_persisted_project_records(self):
        self.agent.understand_requirements(self.project["id"]); generated = self.agent.prepare_solution(self.project["id"])
        self.assertEqual(generated["metrics"]["requirements_parsed"], 6)
        self.assertGreaterEqual(generated["metrics"]["deliverables_generated"], 5)

    def test_computer_agent_integration_is_capability_only_and_approval_bounded(self):
        self.agent.understand_requirements(self.project["id"])
        blueprint = self.agent.prepare_solution(self.project["id"])["blueprint"]
        self.assertIn("Computer Lab（受控、审批前只分析）", blueprint["ai_capability"])
        self.assertIn("所有源码修改必须 Diff + Human Approval", blueprint["security_boundary"])

    def test_computer_mission_is_proposal_only(self):
        self.agent.understand_requirements(self.project["id"]); self.agent.prepare_solution(self.project["id"])
        actions = self.service.computer_actions(self.project["id"])["actions"]
        self.assertEqual(actions[0]["status"], "WAITING_APPROVAL")
        self.assertFalse(actions[0]["execution_allowed"])

    def test_solution_versions_preserve_draft_and_review_history(self):
        self.agent.understand_requirements(self.project["id"]); self.agent.prepare_solution(self.project["id"])
        self.service.review(self.project["id"], "NEEDS_REVISION", "reviewer requested a revision")
        versions = self.service.versions(self.project["id"])["versions"]
        self.assertEqual([item["status"] for item in versions], ["DRAFT", "REVISED"])


if __name__ == "__main__":
    unittest.main()
