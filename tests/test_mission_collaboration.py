from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.models.identity import User
from app.services.database import Base
from app.services.governance_service import GovernanceError, PermissionService
from app.services.identity_service import IdentityContext
from app.services.mission_collaboration_service import MissionCollaborationError, MissionCollaborationService
from app.services.workspace_context_service import WorkspaceContextService


class MissionCollaborationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        session = self.sessions()
        session.add_all([
            GovernanceWorkspace(id="workspace-a", organization_id="org-a", name="Research team", owner_id="owner"),
            GovernanceWorkspace(id="workspace-b", organization_id="org-b", name="Other team", owner_id="other"),
            User(id="owner", email="owner@example.com", display_name="Professor", password_hash="x"),
            User(id="researcher", email="researcher@example.com", display_name="Researcher", password_hash="x"),
            User(id="reviewer", email="reviewer@example.com", display_name="Expert Reviewer", password_hash="x"),
            User(id="viewer", email="viewer@example.com", display_name="Viewer", password_hash="x"),
            User(id="other", email="other@example.com", display_name="Other", password_hash="x"),
            WorkspaceUserRole(workspace_id="workspace-a", user_id="owner", role="OWNER"),
            WorkspaceUserRole(workspace_id="workspace-a", user_id="researcher", role="MEMBER"),
            WorkspaceUserRole(workspace_id="workspace-a", user_id="reviewer", role="REVIEWER"),
            WorkspaceUserRole(workspace_id="workspace-a", user_id="viewer", role="VIEWER"),
            WorkspaceUserRole(workspace_id="workspace-b", user_id="other", role="OWNER"),
            AIMission(id="mission-a", title="Low carbon materials", goal="Research trends", workspace_id="workspace-a", status="PLANNING"),
            AIMission(id="mission-b", title="Other", goal="Other", workspace_id="workspace-b", status="PLANNING"),
            AIMissionEvent(mission_id="mission-a", stage="Evidence", action="Evidence collected", status="WAITING_REVIEW", evidence_count=2, result_summary="Two traceable sources are ready for review."),
        ])
        session.commit(); session.close()
        self.service = MissionCollaborationService(self.sessions, initialize=False)
        self.permissions = PermissionService(self.sessions, initialize=False)

    def tearDown(self):
        self.engine.dispose()

    def test_member_roles_are_presented_as_team_collaboration_capabilities(self):
        members = self.service.members("workspace-a")
        researcher = next(item for item in members if item["user_id"] == "researcher")
        reviewer = next(item for item in members if item["user_id"] == "reviewer")
        self.assertEqual(researcher["role_label"], "Researcher")
        self.assertTrue(researcher["can_edit"])
        self.assertTrue(reviewer["can_review"])
        self.assertFalse(reviewer["can_manage"])

    def test_owner_assigns_workspace_member_to_mission(self):
        participant = self.service.assign("workspace-a", "mission-a", "researcher", "Collect recent sources", actor_id="owner")
        self.assertEqual(participant["display_name"], "Researcher")
        self.assertEqual(participant["responsibility"], "Collect recent sources")

    def test_cross_workspace_member_assignment_is_rejected(self):
        with self.assertRaises(MissionCollaborationError):
            self.service.assign("workspace-a", "mission-a", "other", "Outside scope", actor_id="owner")

    def test_review_comment_is_combined_with_real_ai_activity(self):
        self.service.comment("workspace-a", "mission-a", "reviewer", "Please add recent evidence.", status="REVISION_REQUESTED")
        collaboration = self.service.mission("workspace-a", "mission-a")
        self.assertEqual(collaboration["comments"][0]["display_name"], "Expert Reviewer")
        self.assertEqual({item["kind"] for item in collaboration["activity"]}, {"AI_ACTIVITY", "TEAM_COMMENT"})

    def test_viewer_cannot_comment_or_assign(self):
        with self.assertRaises(GovernanceError):
            self.permissions.check("workspace-a", "viewer", "MISSION_COMMENT")
        with self.assertRaises(GovernanceError):
            self.permissions.check("workspace-a", "viewer", "MISSION_ASSIGN")

    def test_team_dashboard_is_workspace_scoped(self):
        dashboard = self.service.dashboard("workspace-a")
        self.assertEqual(dashboard["active_missions"], 1)
        self.assertEqual(len(dashboard["members"]), 4)

    def test_runtime_context_includes_only_current_mission_collaboration(self):
        self.service.assign("workspace-a", "mission-a", "researcher", "Collect recent sources", actor_id="owner")
        self.service.comment("workspace-a", "mission-a", "reviewer", "Please add recent evidence.", status="REVISION_REQUESTED")
        actor = IdentityContext("owner", "owner@example.com", "Professor", "workspace-a", "OWNER", "session-a")
        context = WorkspaceContextService(self.sessions, initialize=False).build(
            {"id": "mission-a", "workspace_id": "workspace-a", "goal": "Research trends", "status": "PLANNING", "evidence_refs": []},
            actor=actor,
        )
        collaboration = context["collaboration"]
        self.assertEqual(collaboration["participants"][0]["responsibility"], "Collect recent sources")
        self.assertEqual(collaboration["recent_review_comments"][0]["status"], "REVISION_REQUESTED")


if __name__ == "__main__":
    unittest.main()
