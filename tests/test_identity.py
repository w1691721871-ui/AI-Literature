"""P54 identity, session, RBAC, and workspace-isolation tests using memory only."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.models.computer_mission import ComputerMission
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.models.identity import User, UserSession
from app.services.database import Base
from app.services.governance_service import GovernanceError, PermissionService
from app.services.identity_service import IdentityError, IdentityService
from app.services.demo_identity_service import DemoIdentitySeeder
from app.services.permission_middleware import PermissionMiddleware


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.identities = IdentityService(self.sessions, initialize=False)
        self.permissions = PermissionService(self.sessions, initialize=False)
        self.owner = self.identities.register("owner@example.test", "Owner", "correct-horse-battery-staple")
        self.viewer = self.identities.register("viewer@example.test", "Viewer", "correct-horse-battery-viewer")
        self.reviewer = self.identities.register("reviewer@example.test", "Reviewer", "correct-horse-battery-review")
        session = self.sessions()
        try:
            self.workspace_a = GovernanceWorkspace(organization_id="org-a", name="A", owner_id=self.owner["id"])
            self.workspace_b = GovernanceWorkspace(organization_id="org-b", name="B", owner_id=self.owner["id"])
            session.add_all([self.workspace_a, self.workspace_b]); session.flush()
            self.workspace_a_id, self.workspace_b_id = self.workspace_a.id, self.workspace_b.id
            session.add_all([
                WorkspaceUserRole(workspace_id=self.workspace_a_id, user_id=self.owner["id"], role="OWNER"),
                WorkspaceUserRole(workspace_id=self.workspace_a_id, user_id=self.viewer["id"], role="VIEWER"),
                WorkspaceUserRole(workspace_id=self.workspace_a_id, user_id=self.reviewer["id"], role="REVIEWER"),
                WorkspaceUserRole(workspace_id=self.workspace_b_id, user_id=self.owner["id"], role="OWNER"),
            ])
            mission = AIMission(title="Scoped mission", goal="Use real evidence", workspace_id=self.workspace_a_id, status="PLANNING")
            session.add(mission); session.flush(); self.mission_id = mission.id
            artifact = Artifact(mission_id=mission.id, artifact_type="DELIVERY_PACKAGE", title="Draft", status="NEEDS_REVIEW")
            session.add(artifact); session.flush(); self.artifact_id = artifact.id
            computer = ComputerMission(task_id="computer-identity", mission_name="Scoped computer", mission_id=mission.id)
            session.add(computer); session.flush(); self.computer_id = computer.id
            session.commit()
        finally:
            session.close()
        self.middleware = PermissionMiddleware(identities=self.identities, permissions=self.permissions, sessions=self.sessions)

    def tearDown(self):
        self.engine.dispose()

    def login(self, email, password, workspace):
        return self.identities.create_session(email, password, workspace)["profile"]

    def test_login_session_stores_only_hash_and_resolves_context(self):
        result = self.identities.create_session("owner@example.test", "correct-horse-battery-staple", self.workspace_a_id)
        self.assertTrue(result["session_token"])
        context = self.identities.context_for_token(result["session_token"])
        self.assertEqual(context.user_id, self.owner["id"])
        self.assertEqual(context.workspace_id, self.workspace_a_id)
        session = self.sessions()
        try:
            stored = session.query(UserSession).one()
            self.assertNotEqual(stored.session_token_hash, result["session_token"])
            self.assertNotIn("correct-horse", session.query(User).filter_by(id=self.owner["id"]).one().password_hash)
        finally:
            session.close()

    def test_login_without_workspace_uses_only_a_persisted_membership(self):
        result = self.identities.create_session("owner@example.test", "correct-horse-battery-staple")
        self.assertIn(result["profile"].workspace_id, {self.workspace_a_id, self.workspace_b_id})

    def test_workspace_isolation_rejects_cross_workspace_mission(self):
        context = self.login("owner@example.test", "correct-horse-battery-staple", self.workspace_b_id)
        with self.assertRaises(Exception):
            self.middleware.mission(context, self.mission_id, "MISSION_VIEW")

    def test_viewer_cannot_modify_or_execute(self):
        context = self.login("viewer@example.test", "correct-horse-battery-viewer", self.workspace_a_id)
        self.middleware.mission(context, self.mission_id, "MISSION_VIEW")
        with self.assertRaises(Exception):
            self.middleware.mission(context, self.mission_id, "MISSION_EXECUTE")

    def test_member_cannot_approve_artifact(self):
        session = self.sessions()
        try:
            member = self.identities.register("member@example.test", "Member", "correct-horse-battery-member")
            session.add(WorkspaceUserRole(workspace_id=self.workspace_a_id, user_id=member["id"], role="MEMBER")); session.commit()
        finally:
            session.close()
        context = self.login("member@example.test", "correct-horse-battery-member", self.workspace_a_id)
        with self.assertRaises(Exception):
            self.middleware.artifact(context, self.artifact_id, "ARTIFACT_REVIEW")

    def test_reviewer_can_approve_artifact(self):
        context = self.login("reviewer@example.test", "correct-horse-battery-review", self.workspace_a_id)
        self.middleware.artifact(context, self.artifact_id, "ARTIFACT_REVIEW")
        self.assertTrue(self.permissions.can_approve_review(self.workspace_a_id, self.reviewer["id"]))

    def test_computer_execution_requires_role(self):
        viewer = self.login("viewer@example.test", "correct-horse-battery-viewer", self.workspace_a_id)
        with self.assertRaises(Exception):
            self.middleware.computer(viewer, self.computer_id, "COMPUTER_EXECUTE")
        owner = self.login("owner@example.test", "correct-horse-battery-staple", self.workspace_a_id)
        self.middleware.computer(owner, self.computer_id, "COMPUTER_EXECUTE")

    def test_missing_or_invalid_login_is_rejected(self):
        with self.assertRaises(IdentityError):
            self.identities.context_for_token("")
        with self.assertRaises(IdentityError):
            self.identities.create_session("owner@example.test", "wrong-password", self.workspace_a_id)

    def test_demo_seed_is_opt_in_and_uses_environment_credentials(self):
        seeded = DemoIdentitySeeder(self.sessions, initialize=False)
        with patch.dict("os.environ", {"DEMO_MODE": "false"}, clear=False):
            self.assertEqual(seeded.seed_if_enabled()["reason"], "DEMO_MODE_DISABLED")
        with patch.dict("os.environ", {
            "DEMO_MODE": "true",
            "DEMO_OWNER_PASSWORD": "demo-owner-password",
            "DEMO_REVIEWER_PASSWORD": "demo-reviewer-password",
        }, clear=False):
            result = seeded.seed_if_enabled()
        self.assertTrue(result["seeded"])
        owner_context = self.identities.create_session("demo.owner@localhost", "demo-owner-password")
        self.assertEqual(owner_context["profile"].workspace_id, result["workspace_id"])


if __name__ == "__main__":
    unittest.main()
