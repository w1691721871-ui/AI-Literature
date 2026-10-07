"""Release-closure checks: no synthetic corpus or false ready state."""
from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.models.identity import User
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.database import Base
from app.services.demo_readiness_service import DemoReadinessService
from app.services.identity_service import IdentityService


class ReleaseClosureTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def tearDown(self):
        self.engine.dispose()

    def test_empty_deployment_is_blocked_not_reported_as_demo_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = DemoReadinessService(self.sessions, index_path=Path(directory) / "index.faiss", mapping_path=Path(directory) / "mapping.json").snapshot()
        self.assertEqual(snapshot["overall"], "BLOCKED")
        self.assertEqual(snapshot["counts"]["papers"], 0)
        self.assertEqual(snapshot["checks"][0]["status"], "BLOCKED")

    def test_real_counts_remain_blocked_without_persisted_faiss(self):
        session = self.sessions()
        try:
            user = User(email="demo.release@example.test", display_name="Demo", password_hash="hash")
            session.add(user); session.flush()
            workspace = GovernanceWorkspace(organization_id="demo-org", name=IdentityService.demo_workspace_name, owner_id=user.id)
            session.add(workspace); session.flush()
            session.add(WorkspaceUserRole(workspace_id=workspace.id, user_id=user.id, role="OWNER"))
            for index in range(5):
                paper = Paper(title=f"Public {index}", filename=f"public-{index}.pdf", file_path=f"/safe/{index}.pdf", text_content="Public research source", analysis_status="indexed", quality_status="indexed")
                session.add(paper); session.flush()
                session.add(PaperChunk(paper_id=paper.paper_id, chunk_index=0, content="Traceable public text", embedding="[0.1, 0.2]"))
            session.commit()
        finally:
            session.close()
        with tempfile.TemporaryDirectory() as directory:
            snapshot = DemoReadinessService(self.sessions, index_path=Path(directory) / "index.faiss", mapping_path=Path(directory) / "mapping.json").snapshot()
        self.assertEqual(snapshot["counts"]["papers"], 5)
        self.assertEqual(snapshot["checks"][2]["status"], "BLOCKED")
        self.assertEqual(snapshot["overall"], "BLOCKED")

    def test_version_endpoint_declares_no_secret_configuration(self):
        from app.main import version_identity
        identity = version_identity()
        self.assertEqual(set(identity), {"service", "release", "commit", "frontend_version", "backend_version", "environment", "status"})
        self.assertEqual(identity["service"], "researchos-api")
        self.assertEqual(identity["status"], "ok")
        self.assertEqual(identity["frontend_version"], "v169")
        rendered = str(identity).lower()
        self.assertNotIn("secret", rendered)
        self.assertNotIn("password", rendered)
        self.assertNotIn("token", rendered)


if __name__ == "__main__":
    unittest.main()
