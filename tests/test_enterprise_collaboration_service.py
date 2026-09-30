"""Fixture-only coverage for the P11.5 enterprise collaboration layer."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.organization import OrganizationMember
from app.models.paper import Paper
from app.services.database import Base
from app.services.enterprise_collaboration_service import EnterpriseCollaborationService, PermissionDeniedError


class EnterpriseCollaborationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.service = EnterpriseCollaborationService(self.Session, initialize=False)
        self.organization = self.service.create_org("Fixture Research Lab", "Leader")
        self.admin_id = self.organization["admin_member_id"]
        session = self.Session()
        try:
            paper = Paper(title="Fixture paper", filename="fixture.pdf", file_path="fixture.pdf", text_content="fixture")
            session.add(paper)
            session.commit()
            self.paper_id = paper.paper_id
        finally:
            session.close()
        self.researcher_id = self.service.add_member(self.organization["id"], self.admin_id, "Researcher", "Researcher")["id"]
        self.reviewer_id = self.service.add_member(self.organization["id"], self.admin_id, "Reviewer", "Reviewer")["id"]

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_project_lifecycle_and_activity_are_organization_scoped(self) -> None:
        created = self.service.create_project(self.organization["id"], {
            "name": "Evidence review", "description": "Fixture only", "research_goal": "Review sources",
            "owner_member_id": self.admin_id,
        })
        updated = self.service.update_project_status(self.organization["id"], created["id"], self.admin_id, "Reviewing")
        self.assertEqual(updated["status"], "Reviewing")
        self.assertEqual(len(self.service.list_projects(self.organization["id"])), 1)
        self.assertTrue(any(item["action"] == "project_status_updated" for item in self.service.activity(self.organization["id"])))

    def test_permissions_and_team_knowledge_scope(self) -> None:
        self.service.set_knowledge_scope(self.organization["id"], {
            "member_id": self.researcher_id, "paper_id": self.paper_id, "knowledge_scope": "Team",
        })
        visible = self.service.team_knowledge(self.organization["id"], self.reviewer_id)
        self.assertEqual(visible[0]["paper_id"], self.paper_id)
        with self.assertRaises(PermissionDeniedError):
            self.service.set_knowledge_scope(self.organization["id"], {
                "member_id": self.reviewer_id, "paper_id": self.paper_id, "knowledge_scope": "Organization",
            })

    def test_owner_and_member_labels_reuse_the_server_side_permission_model(self) -> None:
        owner = self.service.add_member(self.organization["id"], self.admin_id, "Owner", "Owner")
        member = self.service.add_member(self.organization["id"], self.admin_id, "Member", "Member")
        self.assertEqual(self.service.check(self.organization["id"], owner["id"], "approve_deliverable").role, "Owner")
        self.assertEqual(self.service.check(self.organization["id"], member["id"], "view_evidence").role, "Member")

    def test_meeting_proposals_require_human_confirmation_and_create_no_task(self) -> None:
        result = self.service.create_meeting(self.organization["id"], {
            "member_id": self.researcher_id,
            "notes": "决定先审核当前证据\n行动：负责人确认是否建立后续研究任务",
        })
        self.assertTrue(result["human_confirmation_required"])
        self.assertEqual(result["status"], "pending_human_confirmation")
        self.assertTrue(result["decisions"])
        self.assertTrue(result["action_items"])

    def test_dashboard_uses_actual_database_counts(self) -> None:
        dashboard = self.service.dashboard(self.organization["id"], self.admin_id)
        self.assertEqual(dashboard["projects"]["total"], 0)
        self.assertEqual(dashboard["knowledge_assets"], 0)
        self.assertEqual(dashboard["evidence_count"], 0)

    def test_delivery_package_is_review_required_and_preserves_empty_data_boundary(self) -> None:
        package = self.service.delivery_package(self.organization["id"], self.admin_id)
        self.assertTrue(package["human_confirmation_required"])
        self.assertEqual(package["status"], "draft_for_human_review")
        self.assertIn("尚无可验证知识资料", package["data_boundary"])


if __name__ == "__main__":
    unittest.main()
