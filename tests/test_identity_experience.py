"""P64.5 identity experience tests use an isolated in-memory database only."""

from __future__ import annotations

import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.models.identity import User
from app.services.database import Base
from app.services.governance_service import GovernanceError, PermissionService
from app.services.identity_service import IdentityError, IdentityService
from app.services.permission_middleware import PermissionMiddleware
from app.services.workspace_experience_service import WorkspaceExperienceService


class IdentityExperienceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.identity = IdentityService(self.sessions, initialize=False)
        self.permissions = PermissionService(self.sessions, initialize=False)
        self.middleware = PermissionMiddleware(identities=self.identity, permissions=self.permissions, sessions=self.sessions)

    def tearDown(self):
        self.engine.dispose()

    def test_registration_creates_workspace_owner_membership_and_session(self):
        result = self.identity.register_workspace(
            "owner@identity-experience.test",
            "Workspace Owner",
            "a-safe-test-password",
            "Innovation Research",
        )
        self.assertTrue(result["session_token"])
        self.assertEqual(result["workspace"]["name"], "Innovation Research")
        self.assertEqual(result["workspace"]["role"], "OWNER")
        context = self.identity.context_for_token(result["session_token"])
        self.assertEqual(context.role, "OWNER")
        session = self.sessions()
        try:
            workspace = session.get(GovernanceWorkspace, context.workspace_id)
            membership = session.scalar(select(WorkspaceUserRole).where(
                WorkspaceUserRole.workspace_id == context.workspace_id,
                WorkspaceUserRole.user_id == context.user_id,
            ))
            self.assertEqual(workspace.owner_id, context.user_id)
            self.assertEqual(membership.role, "OWNER")
            self.assertNotIn("a-safe-test-password", session.get(User, context.user_id).password_hash)
        finally:
            session.close()

    def test_registration_rejects_duplicate_email(self):
        self.identity.register_workspace("same@identity-experience.test", "First", "a-safe-test-password", "First Workspace")
        with self.assertRaises(IdentityError):
            self.identity.register_workspace("same@identity-experience.test", "Second", "another-safe-password", "Second Workspace")

    def test_demo_session_is_member_scoped_and_marked_demo(self):
        result = self.identity.create_demo_session()
        context = self.identity.context_for_token(result["session_token"])
        profile = self.identity.profile(context)
        self.assertEqual(context.role, "MEMBER")
        self.assertTrue(profile["workspace"]["is_demo"])
        self.assertEqual(profile["workspace"]["name"], "ResearchOS Demo Workspace")
        with self.assertRaises(GovernanceError):
            self.permissions.check(context.workspace_id, context.user_id, "MISSION_APPROVE")

    def test_demo_session_is_denied_from_admin_console(self):
        demo = self.identity.create_demo_session()
        context = self.identity.context_for_token(demo["session_token"])
        with self.assertRaises(HTTPException) as denied:
            self.middleware.admin_console(context)
        self.assertEqual(denied.exception.status_code, 403)

    def test_demo_workspace_cannot_access_customer_workspace(self):
        customer = self.identity.register_workspace(
            "customer@identity-experience.test", "Customer", "a-safe-test-password", "Customer Workspace"
        )
        demo = self.identity.create_demo_session()
        demo_context = self.identity.context_for_token(demo["session_token"])
        with self.assertRaises(HTTPException) as denied:
            self.middleware._assert_workspace(demo_context, customer["workspace"]["id"], "MISSION_VIEW")
        self.assertEqual(denied.exception.status_code, 403)

    def test_missing_session_is_rejected(self):
        with self.assertRaises(HTTPException) as denied:
            self.middleware.current(None)
        self.assertEqual(denied.exception.status_code, 401)

    def test_unassigned_user_is_forbidden_from_workspace_permissions(self):
        unassigned = self.identity.register("unassigned@identity-experience.test", "Unassigned", "a-safe-test-password")
        demo = self.identity.create_demo_session()
        demo_context = self.identity.context_for_token(demo["session_token"])
        with self.assertRaises(GovernanceError):
            self.permissions.check(demo_context.workspace_id, unassigned["id"], "MISSION_VIEW")

    def test_workspace_dashboard_filters_to_current_workspace(self):
        first = self.identity.register_workspace("first@identity-experience.test", "First", "a-safe-test-password", "First Workspace")
        second = self.identity.register_workspace("second@identity-experience.test", "Second", "a-safe-test-password", "Second Workspace")
        session = self.sessions()
        try:
            session.add_all([
                AIMission(title="First mission", goal="Scoped", workspace_id=first["workspace"]["id"]),
                AIMission(title="Second mission", goal="Scoped", workspace_id=second["workspace"]["id"]),
            ])
            session.commit()
        finally:
            session.close()
        dashboard = WorkspaceExperienceService(self.sessions, initialize=False).dashboard(first["workspace"]["id"])
        self.assertEqual([item["title"] for item in dashboard["missions"]], ["First mission"])

    def test_frontend_requires_identity_then_isolates_workspace_loaders(self):
        source = (Path(__file__).resolve().parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
        initialize = source[source.index("async function initializeAuthorizedWorkspace"):source.index("async function loginToWorkspace")]
        self.assertIn("const results = await Promise.allSettled", initialize)
        self.assertIn("[\"workspace overview\", loadWorkspaceExperience]", initialize)
        self.assertIn("[\"missions\", loadAIMissions]", initialize)
        self.assertIn("const identityRestored = await loadIdentityProfile();", source)
        establish = source[source.index("async function establishIdentitySession"):source.index("async function registerWorkspace")]
        self.assertLess(establish.index("activeWorkspaceView.value = destination"), establish.index("void initializeAuthorizedWorkspace()"))
        self.assertIn("void initializeApplication();", source)


if __name__ == "__main__":
    unittest.main()
