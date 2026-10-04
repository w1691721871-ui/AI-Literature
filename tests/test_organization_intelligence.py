"""Workspace-only organizational learning projections."""

from __future__ import annotations

import json
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.approval import ApprovalRequest
from app.models.artifact import Artifact
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.models.workspace_memory import WorkspaceMemory
from app.services.database import Base
from app.services.governance_service import PermissionService
from app.services.identity_service import IdentityService
from app.services.organization_intelligence_service import OrganizationIntelligenceService
from app.services.permission_middleware import PermissionMiddleware


class OrganizationIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.identity = IdentityService(self.sessions, initialize=False)
        self.permissions = PermissionService(self.sessions, initialize=False)
        self.middleware = PermissionMiddleware(identities=self.identity, permissions=self.permissions, sessions=self.sessions)
        self.service = OrganizationIntelligenceService(self.sessions, initialize=False)

    def tearDown(self):
        self.engine.dispose()

    def _workspace(self, email: str, name: str, role: str = "MEMBER"):
        user = self.identity.register(email, name, "correct-horse-battery-staple")
        session = self.sessions()
        try:
            workspace = GovernanceWorkspace(organization_id=f"org-{name}", name=f"{name} Workspace", owner_id=user["id"])
            session.add(workspace)
            session.flush()
            session.add(WorkspaceUserRole(workspace_id=workspace.id, user_id=user["id"], role=role))
            session.commit()
            token = self.identity.create_session(email, "correct-horse-battery-staple", workspace.id)["session_token"]
            return user, workspace.id, self.identity.context_for_token(token)
        finally:
            session.close()

    def test_empty_workspace_reports_no_data_without_synthetic_metrics(self):
        _, workspace_id, _ = self._workspace("empty.intelligence@test", "Empty")
        overview = self.service.overview(workspace_id)
        self.assertEqual(overview["data_state"], "NO_DATA")
        self.assertEqual(overview["metrics"], {
            "missions": 0, "completed_missions": 0, "evidence": 0, "approved_evidence": 0,
            "artifacts": 0, "reviews": 0, "research_memory": 0,
        })
        self.assertIn("No organizational learning data", overview["long_term_value"]["title"])

    def test_workspace_counts_are_persisted_unique_and_exclude_other_workspaces(self):
        user, workspace_id, _ = self._workspace("member.intelligence@test", "Member")
        _, other_workspace_id, _ = self._workspace("other.intelligence@test", "Other")
        session = self.sessions()
        try:
            refs = [{"paper_id": "p-1", "chunk_id": "c-1"}, {"paper_id": "p-2", "chunk_id": "c-2"}]
            mission = AIMission(title="Completed", goal="Evidence-bound", workspace_id=workspace_id, status="COMPLETED", evidence_refs_json=json.dumps(refs))
            duplicate = AIMission(title="Active", goal="Evidence-bound", workspace_id=workspace_id, status="PLANNING", evidence_refs_json=json.dumps([refs[0]]))
            other = AIMission(title="Other", goal="Isolated", workspace_id=other_workspace_id, status="COMPLETED", evidence_refs_json=json.dumps([{"paper_id": "other", "chunk_id": "other"}]))
            session.add_all([mission, duplicate, other])
            session.flush()
            session.add_all([
                Artifact(mission_id=mission.id, artifact_type="RESEARCH_BRIEF", title="Brief", status="NEEDS_REVIEW"),
                Artifact(mission_id=other.id, artifact_type="RESEARCH_BRIEF", title="Other brief", status="APPROVED"),
                ApprovalRequest(workspace_id=workspace_id, mission_id=mission.id, source_type="Evidence", source_id="c-1", request_type="EVIDENCE_VERIFY", creator_id=user["id"], status="APPROVED"),
                ApprovalRequest(workspace_id=workspace_id, mission_id=mission.id, source_type="Artifact", source_id="release-1", request_type="ARTIFACT_RELEASE", creator_id=user["id"], status="PENDING"),
                ApprovalRequest(workspace_id=other_workspace_id, mission_id=other.id, source_type="Evidence", source_id="other", request_type="EVIDENCE_VERIFY", creator_id=user["id"], status="APPROVED"),
                WorkspaceMemory(workspace_id=workspace_id, owner_id=user["id"], memory_type="MISSION", title="Completed research", summary="A safe persisted summary."),
                WorkspaceMemory(workspace_id=other_workspace_id, memory_type="WORKSPACE", title="Other memory", summary="Not visible here."),
            ])
            session.commit()
        finally:
            session.close()
        overview = self.service.overview(workspace_id)
        self.assertEqual(overview["data_state"], "READY")
        self.assertEqual(overview["metrics"], {
            "missions": 2, "completed_missions": 1, "evidence": 2, "approved_evidence": 1,
            "artifacts": 1, "reviews": 2, "research_memory": 1,
        })
        self.assertIn("completed 1 Mission", overview["long_term_value"]["summary"])

    def test_member_context_cannot_request_another_workspaces_intelligence(self):
        _, first_workspace_id, first_context = self._workspace("first.intelligence@test", "First")
        _, second_workspace_id, _ = self._workspace("second.intelligence@test", "Second")
        self.middleware.require(first_context, "MISSION_VIEW")
        with self.assertRaises(HTTPException) as denied:
            self.middleware._assert_workspace(first_context, second_workspace_id, "MISSION_VIEW")
        self.assertEqual(denied.exception.status_code, 403)
        self.assertNotEqual(first_workspace_id, second_workspace_id)


if __name__ == "__main__":
    unittest.main()
