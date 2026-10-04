"""Release-level checks for an empty enterprise Workspace and access boundaries."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.computer_mission import ComputerMission
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.services.ai_mission_service import AIMissionService
from app.services.ai_worker_runtime import AIWorkerRuntime
from app.services.database import Base
from app.services.governance_service import PermissionService
from app.services.identity_service import IdentityService
from app.services.permission_middleware import PermissionMiddleware


class FinalReleaseReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.identity = IdentityService(self.sessions, initialize=False)
        self.permissions = PermissionService(self.sessions, initialize=False)
        self.middleware = PermissionMiddleware(identities=self.identity, permissions=self.permissions, sessions=self.sessions)

    def tearDown(self):
        self.engine.dispose()

    def _workspace_user(self, email: str, role: str):
        user = self.identity.register(email, role.title(), "correct-horse-battery-staple")
        session = self.sessions()
        try:
            workspace = session.query(GovernanceWorkspace).filter_by(name="Release Workspace").one_or_none()
            if workspace is None:
                workspace = GovernanceWorkspace(organization_id="release-org", name="Release Workspace", owner_id=user["id"])
                session.add(workspace)
                session.flush()
            session.add(WorkspaceUserRole(workspace_id=workspace.id, user_id=user["id"], role=role))
            session.commit()
            return user, workspace.id
        finally:
            session.close()

    def _context(self, email: str, password: str, workspace_id: str):
        return self.identity.context_for_token(self.identity.create_session(email, password, workspace_id)["session_token"])

    def test_empty_workspace_initializes_identity_mission_runtime_and_demo_safely(self):
        registration = self.identity.register_workspace(
            "release.owner@example.test", "Release Owner", "correct-horse-battery-staple", "Fresh Workspace"
        )
        context = self.identity.context_for_token(registration["session_token"])
        mission = AIMissionService(self.sessions, initialize=False).create({
            "title": "Fresh evidence review",
            "goal": "Prepare a reviewable research brief from traceable evidence.",
            "workspace_id": context.workspace_id,
        })
        snapshot = AIWorkerRuntime(self.sessions, initialize=False).snapshot(mission["id"], actor=context)
        self.assertEqual(snapshot["mission"]["id"], mission["id"])
        self.assertEqual(snapshot["research_insight"]["gap_analysis"]["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(snapshot["execution"])

        demo = self.identity.create_demo_session()
        demo_context = self.identity.context_for_token(demo["session_token"])
        self.assertEqual(demo_context.role, "MEMBER")
        self.assertNotEqual(demo_context.workspace_id, context.workspace_id)

    def test_startup_initializes_persistence_before_optional_demo_provisioning(self):
        from app import main

        with patch.object(main, "initialize_database") as initialize, patch.object(main, "DemoIdentitySeeder") as seeder:
            main.provision_demo_identity_if_enabled()
        initialize.assert_called_once_with()
        seeder.return_value.seed_if_enabled.assert_called_once_with()

    def test_role_matrix_enforces_anonymous_demo_reviewer_owner_and_admin_boundaries(self):
        owner, workspace_id = self._workspace_user("owner.release@example.test", "OWNER")
        admin, _ = self._workspace_user("admin.release@example.test", "ADMIN")
        reviewer, _ = self._workspace_user("reviewer.release@example.test", "REVIEWER")
        viewer, _ = self._workspace_user("viewer.release@example.test", "VIEWER")
        session = self.sessions()
        try:
            mission = AIMission(title="Release mission", goal="Evidence first", workspace_id=workspace_id)
            session.add(mission)
            session.flush()
            computer = ComputerMission(task_id="release-computer", mission_name="Release computer", mission_id=mission.id)
            session.add(computer)
            session.commit()
            mission_id, computer_id = mission.id, computer.id
        finally:
            session.close()

        with self.assertRaises(HTTPException) as anonymous:
            self.middleware.current(None)
        self.assertEqual(anonymous.exception.status_code, 401)

        demo_context = self.identity.context_for_token(self.identity.create_demo_session()["session_token"])
        with self.assertRaises(HTTPException) as demo_admin:
            self.middleware.admin_console(demo_context)
        self.assertEqual(demo_admin.exception.status_code, 403)

        owner_context = self._context(owner["email"], "correct-horse-battery-staple", workspace_id)
        admin_context = self._context(admin["email"], "correct-horse-battery-staple", workspace_id)
        reviewer_context = self._context(reviewer["email"], "correct-horse-battery-staple", workspace_id)
        viewer_context = self._context(viewer["email"], "correct-horse-battery-staple", workspace_id)
        self.middleware.admin_console(owner_context)
        self.middleware.admin_console(admin_context)
        self.middleware.mission(reviewer_context, mission_id, "MISSION_VIEW")
        with self.assertRaises(HTTPException) as reviewer_execute:
            self.middleware.mission(reviewer_context, mission_id, "MISSION_EXECUTE")
        with self.assertRaises(HTTPException) as viewer_execute:
            self.middleware.computer(viewer_context, computer_id, "COMPUTER_EXECUTE")
        self.assertEqual(reviewer_execute.exception.status_code, 403)
        self.assertEqual(viewer_execute.exception.status_code, 403)

    def test_runtime_computer_and_compatibility_routes_declare_identity_boundaries(self):
        root = Path(__file__).resolve().parents[1] / "app" / "routes"
        runtime = (root / "runtime.py").read_text(encoding="utf-8")
        computer = (root / "computer_missions.py").read_text(encoding="utf-8")
        legacy = (root / "researchos.py").read_text(encoding="utf-8")
        self.assertIn('permissions.mission(context, mission_id, "MISSION_EXECUTE")', runtime)
        self.assertIn("Depends(permissions.current)", computer)
        self.assertIn('permissions.computer(context, computer_mission_id, "COMPUTER_EXECUTE")', computer)
        self.assertIn("dependencies=[Depends(require_legacy_compatibility_admin)]", legacy)


if __name__ == "__main__":
    unittest.main()
