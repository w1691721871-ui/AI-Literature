"""P56 approval and audit checks use a private in-memory database only."""
from __future__ import annotations

import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.services.approval_service import ApprovalError, ApprovalService
from app.services.audit_service import AuditService
from app.services.database import Base
from app.services.governance_service import PermissionService
from app.services.identity_service import IdentityService
from app.services.permission_middleware import PermissionMiddleware


class GovernanceApprovalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.identity = IdentityService(self.sessions, initialize=False)
        self.permissions = PermissionService(self.sessions, initialize=False)
        self.audit = AuditService(self.sessions, initialize=False)
        self.approvals = ApprovalService(self.sessions, initialize=False, audit=self.audit)
        self.owner = self.identity.register("owner@governance.test", "Owner", "governance-owner-password")
        self.member = self.identity.register("member@governance.test", "Member", "governance-member-password")
        self.reviewer = self.identity.register("reviewer@governance.test", "Reviewer", "governance-review-password")
        self.viewer = self.identity.register("viewer@governance.test", "Viewer", "governance-viewer-password")
        session = self.sessions()
        try:
            workspace = GovernanceWorkspace(organization_id="org-governance", name="Governance", owner_id=self.owner["id"])
            other = GovernanceWorkspace(organization_id="org-other", name="Other", owner_id=self.owner["id"])
            session.add_all([workspace, other]); session.flush()
            self.workspace_id, self.other_workspace_id = workspace.id, other.id
            session.add_all([
                WorkspaceUserRole(workspace_id=workspace.id, user_id=self.owner["id"], role="OWNER"),
                WorkspaceUserRole(workspace_id=workspace.id, user_id=self.member["id"], role="MEMBER"),
                WorkspaceUserRole(workspace_id=workspace.id, user_id=self.reviewer["id"], role="REVIEWER"),
                WorkspaceUserRole(workspace_id=workspace.id, user_id=self.viewer["id"], role="VIEWER"),
                WorkspaceUserRole(workspace_id=other.id, user_id=self.owner["id"], role="OWNER"),
            ])
            mission = AIMission(title="Approval mission", goal="Evidence-backed delivery", workspace_id=workspace.id, status="PLANNING")
            foreign = AIMission(title="Foreign mission", goal="Isolated", workspace_id=other.id, status="PLANNING")
            session.add_all([mission, foreign]); session.flush()
            self.mission_id, self.foreign_mission_id = mission.id, foreign.id
            artifact = Artifact(mission_id=mission.id, artifact_type="DELIVERY_PACKAGE", title="Draft", status="NEEDS_REVIEW")
            session.add(artifact); session.flush(); self.artifact_id = artifact.id
            session.commit()
        finally:
            session.close()
        self.middleware = PermissionMiddleware(identities=self.identity, permissions=self.permissions, sessions=self.sessions)

    def tearDown(self):
        self.engine.dispose()

    def context(self, email, password):
        return self.identity.create_session(email, password, self.workspace_id)["profile"]

    def test_member_can_submit_workspace_scoped_approval(self):
        context = self.context("member@governance.test", "governance-member-password")
        self.middleware.require(context, "MISSION_CREATE")
        request = self.approvals.create_request(context, "MISSION", self.mission_id, "EVIDENCE_VERIFY", "NORMAL", "Verify evidence scope")
        self.assertEqual(request["workspace_id"], self.workspace_id)
        self.assertEqual(request["status"], "PENDING")

    def test_viewer_cannot_review_and_reviewer_can_approve(self):
        member = self.context("member@governance.test", "governance-member-password")
        request = self.approvals.create_request(member, "ARTIFACT", self.artifact_id, "ARTIFACT_RELEASE")
        viewer = self.context("viewer@governance.test", "governance-viewer-password")
        with self.assertRaises(HTTPException) as denied:
            self.middleware.require(viewer, "ARTIFACT_REVIEW")
        self.assertEqual(denied.exception.status_code, 403)
        reviewer = self.context("reviewer@governance.test", "governance-review-password")
        self.middleware.require(reviewer, "ARTIFACT_REVIEW")
        result = self.approvals.approve_request(reviewer, request["id"], "Reviewed by a human.")
        self.assertEqual(result["status"], "APPROVED")

    def test_cross_workspace_source_is_rejected(self):
        owner = self.context("owner@governance.test", "governance-owner-password")
        with self.assertRaises(ApprovalError):
            self.approvals.create_request(owner, "MISSION", self.foreign_mission_id, "DECISION_CONFIRMATION")

    def test_approval_and_runtime_and_artifact_events_are_auditable(self):
        member = self.context("member@governance.test", "governance-member-password")
        request = self.approvals.create_request(member, "MISSION", self.mission_id, "EVIDENCE_VERIFY")
        reviewer = self.context("reviewer@governance.test", "governance-review-password")
        self.approvals.approve_request(reviewer, request["id"])
        self.audit.record_event(self.workspace_id, member.user_id, "MISSION_EXECUTED", "Mission", self.mission_id, self.mission_id, "Runtime execution started.")
        self.audit.record_event(self.workspace_id, reviewer.user_id, "ARTIFACT_RELEASED", "Artifact", self.artifact_id, self.mission_id, "Artifact released after review.")
        events = self.audit.list_events(self.workspace_id)
        self.assertTrue({"APPROVAL_CREATED", "APPROVAL_APPROVED", "MISSION_EXECUTED", "ARTIFACT_RELEASED"}.issubset({row["action_type"] for row in events}))
        self.assertEqual(len(self.audit.get_resource_history(self.workspace_id, self.artifact_id)), 1)

    def test_missing_identity_is_unauthorized(self):
        with self.assertRaises(HTTPException) as denied:
            self.middleware.current(None)
        self.assertEqual(denied.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
