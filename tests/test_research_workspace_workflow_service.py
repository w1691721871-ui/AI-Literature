"""Fixture-only P4 enterprise workflow tests; never touch production stores."""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import ResearchMemory, ResearchWorkspace  # noqa: F401
from app.services.database import Base
from app.services.research_deliverable_service import ResearchDeliverableService
from app.services.research_workspace_intelligence_service import ResearchWorkspaceIntelligenceService
from app.services.research_workspace_workflow_service import (
    ResearchWorkspaceWorkflowService, WorkflowPermissionError,
)
from tests.test_research_workspace_intelligence_service import fixture_result


class ResearchWorkspaceWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.workspace_service = ResearchWorkspaceIntelligenceService(sessions, initialize=False)
        self.workflow = ResearchWorkspaceWorkflowService(self.workspace_service)
        self.deliverables = ResearchDeliverableService()
        self.workspace = self.workspace_service.resolve_or_create("整理 RAG 优化方向的现有资料")
        self.workspace_service.save_run(self.workspace["workspace_id"], fixture_result())

    def tearDown(self) -> None:
        self.engine.dispose()

    @property
    def workspace_id(self) -> str:
        return str(self.workspace["workspace_id"])

    def test_workflow_state_progresses_from_review_to_deliverable_to_completed(self) -> None:
        self.assertEqual(self.workflow.workflow(self.workspace_id)["current_state"], "evidence_review")
        after_review = self.workflow.submit_review(
            self.workspace_id, "review_evidence_support", "reviewer", "approved", "fixture review"
        )
        self.assertEqual(after_review["workflow"]["current_state"], "decision_pending")
        snapshot = self.workspace_service.get_workspace(self.workspace_id)
        brief = self.deliverables.generate(snapshot, self.workspace_service.decision_candidate(self.workspace_id), "research_brief")
        after_draft = self.workflow.mark_deliverable_draft(self.workspace_id, brief)
        self.assertEqual(after_draft["workflow"]["current_state"], "deliverable_draft")
        completed = self.workflow.complete(self.workspace_id, "leader")
        self.assertEqual(completed["workflow"]["current_state"], "completed")

    def test_reviewer_permission_is_enforced_without_auth_system(self) -> None:
        with self.assertRaises(WorkflowPermissionError):
            self.workflow.submit_review(self.workspace_id, "review_evidence_support", "researcher", "approved")
        self.assertEqual(self.workflow.review_items(self.workspace_id)[0]["status"], "pending")
        roles = {member["role_type"] for member in self.workflow.members(self.workspace_id)}
        self.assertEqual(roles, {"researcher", "reviewer", "leader"})

    def test_evidence_graph_keeps_traceable_ids_and_no_invented_claim(self) -> None:
        graph = self.workflow.evidence_graph(self.workspace_id)
        node_ids = {item["id"] for item in graph["nodes"]}
        self.assertIn("paper:paper-a", node_ids)
        self.assertIn("evidence:chunk-a", node_ids)
        self.assertIn("decision:pending", node_ids)
        self.assertIn("deliverable:research_brief", node_ids)
        self.assertIn("Evidence", graph["boundary"])

    def test_research_brief_is_grounded_and_demo_scenario_is_only_fixture(self) -> None:
        snapshot = self.workspace_service.get_workspace(self.workspace_id)
        brief = self.deliverables.generate(snapshot, self.workspace_service.decision_candidate(self.workspace_id), "research_brief")
        self.assertEqual(brief["status"], "draft")
        self.assertEqual(len(brief["evidence_refs"]), 2)
        self.assertIn("需由科研负责人审核", brief["boundary"])
        self.assertNotIn("确定有效", " ".join(str(value) for value in brief["sections"].values()))


if __name__ == "__main__":
    unittest.main()
