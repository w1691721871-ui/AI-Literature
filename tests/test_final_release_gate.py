"""Final release guardrails for the single enterprise execution path."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FinalReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.routes = ROOT / "app" / "routes"
        self.services = ROOT / "app" / "services"

    def test_legacy_researchos_routes_are_not_a_normal_user_entry(self):
        source = (self.routes / "researchos.py").read_text(encoding="utf-8")
        self.assertIn('prefix="/researchos"', source)
        self.assertIn("dependencies=[Depends(require_legacy_compatibility_admin)]", source)
        self.assertIn("_legacy_permissions.admin_console(context)", source)

    def test_public_mission_execution_uses_only_ai_worker_runtime(self):
        source = (self.routes / "missions.py").read_text(encoding="utf-8")
        handler = source[source.index("def run_mission"):source.index('@router.get("/missions/{mission_id}/control")')]
        self.assertIn("ai_worker_runtime.execute(mission_id, actor=context)", handler)
        self.assertNotIn("service.run(mission_id)", handler)

    def test_computer_skill_remains_permission_bound(self):
        source = (self.routes / "computer_missions.py").read_text(encoding="utf-8")
        self.assertIn('permissions.mission(context, payload.mission_id, "COMPUTER_EXECUTE")', source)
        self.assertIn('permissions.computer(context, computer_mission_id, "COMPUTER_EXECUTE")', source)
        self.assertIn('permissions.computer(context, computer_mission_id, "MISSION_APPROVE")', source)

    def test_evidence_and_artifact_boundaries_remain_reviewable(self):
        runtime = (self.services / "ai_worker_runtime.py").read_text(encoding="utf-8")
        artifacts = (self.services / "artifact_service.py").read_text(encoding="utf-8")
        self.assertIn('result.status in {"NEEDS_EVIDENCE", "FAILED"}', runtime)
        self.assertIn('"WAITING_REVIEW"', runtime)
        self.assertIn('if row.status!="NEEDS_REVIEW"', artifacts)
        self.assertIn('"APPROVED","REVISION_REQUESTED","REJECTED"', artifacts)

    def test_workspace_and_persistent_storage_boundaries_are_declared(self):
        permissions = (self.services / "permission_middleware.py").read_text(encoding="utf-8")
        database = (self.services / "database.py").read_text(encoding="utf-8")
        documents = (self.services / "document_store.py").read_text(encoding="utf-8")
        vectors = (self.services / "vector_store.py").read_text(encoding="utf-8")
        artifacts = (self.services / "artifact_service.py").read_text(encoding="utf-8")
        self.assertIn("Cross-workspace access denied", permissions)
        self.assertIn("WORK_DIRECTORY", database)
        self.assertIn("PAPER_DIRECTORY = WORK_DIRECTORY / \"papers\"", documents)
        self.assertIn("VECTOR_INDEX_DIRECTORY = WORK_DIRECTORY / \"vector_index\"", vectors)
        self.assertIn('WORK_DIRECTORY/"artifacts"', artifacts)


if __name__ == "__main__":
    unittest.main()
