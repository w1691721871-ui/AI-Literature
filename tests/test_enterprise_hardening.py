"""P57 product hardening checks; all persistence is isolated in memory."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.services.database import Base
from app.services.demo_identity_service import DemoIdentitySeeder
from app.services.governance_service import PermissionService
from app.services.identity_service import IdentityService
from app.services.permission_middleware import PermissionMiddleware


class EnterpriseHardeningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.identity = IdentityService(self.sessions, initialize=False)
        self.permissions = PermissionService(self.sessions, initialize=False)
        self.owner = self.identity.register("owner@hardening.test", "Owner", "hardening-owner-password")
        self.viewer = self.identity.register("viewer@hardening.test", "Viewer", "hardening-viewer-password")
        session = self.sessions()
        try:
            self.workspace = GovernanceWorkspace(organization_id="hardening-org", name="Hardening", owner_id=self.owner["id"])
            self.other_workspace = GovernanceWorkspace(organization_id="other-org", name="Other", owner_id=self.owner["id"])
            session.add_all([self.workspace, self.other_workspace]); session.flush()
            self.workspace_id = self.workspace.id
            self.other_workspace_id = self.other_workspace.id
            session.add_all([
                WorkspaceUserRole(workspace_id=self.workspace.id, user_id=self.owner["id"], role="OWNER"),
                WorkspaceUserRole(workspace_id=self.workspace.id, user_id=self.viewer["id"], role="VIEWER"),
                WorkspaceUserRole(workspace_id=self.other_workspace.id, user_id=self.owner["id"], role="OWNER"),
            ])
            session.commit()
        finally:
            session.close()
        self.middleware = PermissionMiddleware(identities=self.identity, permissions=self.permissions, sessions=self.sessions)

    def tearDown(self):
        self.engine.dispose()

    def test_workspace_context_reports_real_member_count(self):
        result = self.identity.create_session("owner@hardening.test", "hardening-owner-password", self.workspace_id)
        profile = self.identity.profile(self.identity.context_for_token(result["session_token"]))
        self.assertEqual(profile["workspace"]["name"], "Hardening")
        self.assertEqual(profile["workspace"]["member_count"], 2)

    def test_workspace_isolation_and_rbac_remain_enforced(self):
        viewer_session = self.identity.create_session("viewer@hardening.test", "hardening-viewer-password", self.workspace_id)
        viewer = self.identity.context_for_token(viewer_session["session_token"])
        with self.assertRaises(HTTPException) as denied:
            self.middleware.require(viewer, "MISSION_CREATE")
        self.assertEqual(denied.exception.status_code, 403)
        owner_session = self.identity.create_session("owner@hardening.test", "hardening-owner-password", self.workspace_id)
        owner = self.identity.context_for_token(owner_session["session_token"])
        with self.assertRaises(HTTPException) as denied:
            self.middleware._assert_workspace(owner, self.other_workspace_id, "MISSION_VIEW")
        self.assertEqual(denied.exception.status_code, 403)

    def test_missing_session_is_rejected(self):
        with self.assertRaises(HTTPException) as denied:
            self.middleware.current(None)
        self.assertEqual(denied.exception.status_code, 401)

    def test_demo_seed_stays_opt_in(self):
        seeder = DemoIdentitySeeder(self.sessions, initialize=False)
        with patch.dict("os.environ", {"DEMO_MODE": "false"}, clear=False):
            self.assertEqual(seeder.seed_if_enabled()["reason"], "DEMO_MODE_DISABLED")
        with patch.dict("os.environ", {"DEMO_MODE": "true"}, clear=False):
            self.assertEqual(seeder.seed_if_enabled()["reason"], "DEMO_CREDENTIALS_NOT_CONFIGURED")

    def test_frontend_hides_advanced_navigation_and_sanitizes_errors(self):
        source = (Path(__file__).resolve().parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
        navigation = source.split('<div class="top-navigation-links product-navigation">', 1)[1].split('</div>\n         <div class="nav-utilities">', 1)[0]
        for hidden in ("Benchmark Center", "Connector Center", "Operator Studio", "Research Engine", "Planner"):
            self.assertNotIn(hidden, navigation)
        for visible in ("Home", "Workspace", "Missions", "Knowledge", "Deliveries", "Computer"):
            self.assertIn(f">{visible}<", navigation)
        self.assertIn("Permission denied. You do not have access to this Workspace resource.", source)
        self.assertNotIn("throw new Error(data.detail)", source)


if __name__ == "__main__":
    unittest.main()
