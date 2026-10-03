"""P0/P1 context and Research Memory boundaries."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.models.enterprise_memory import DecisionRecord, KnowledgeAsset
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.models.workspace_memory import WorkspaceMemory
from app.services.ai_team_orchestrator import AITeamOrchestrator
from app.services.database import Base
from app.services.skill_capability_registry import SkillCapabilityRegistry
from app.services.workspace_context_service import WorkspaceContextService
from app.services.workspace_memory_service import WorkspaceMemoryError, WorkspaceMemoryService


class _Registry:
    def plan(self, mission):
        return []


class _Adapter:
    def __init__(self, skill_id):
        self.name = f"{skill_id.title()} Skill"
        self.description = "Existing controlled skill."

    @staticmethod
    def required_permission():
        return "MISSION_VIEW"


class _PlannedRegistry:
    def plan(self, mission):
        return [(skill_id, _Adapter(skill_id)) for skill_id in ("review", "research", "computer")]


class WorkspaceContextTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        session = self.sessions()
        try:
            session.add_all([
                GovernanceWorkspace(id="workspace-a", organization_id="org-a", owner_id="user-a", name="Research A"),
                GovernanceWorkspace(id="workspace-b", organization_id="org-b", owner_id="user-b", name="Research B"),
                WorkspaceUserRole(workspace_id="workspace-a", user_id="user-a", role="OWNER"),
                WorkspaceUserRole(workspace_id="workspace-a", user_id="user-reviewer", role="REVIEWER"),
                WorkspaceUserRole(workspace_id="workspace-b", user_id="user-b", role="OWNER"),
                KnowledgeAsset(workspace_id="workspace-a", asset_type="PAPER", source_type="UPLOAD", title="Verified source", summary="Safe summary", status="VERIFIED"),
                DecisionRecord(mission_id="decision-a", workspace_id="workspace-a", title="Approved decision", review_status="APPROVED"),
                AIMission(id="historical-mission", workspace_id="workspace-a", title="Low-carbon materials delivery", goal="Low-carbon materials", status="COMPLETED"),
                Artifact(mission_id="historical-mission", artifact_type="DELIVERY_PACKAGE", title="Low-carbon materials review", status="APPROVED", content_summary="Approved evidence-backed material comparison.", evidence_count=3),
            ])
            session.commit()
        finally:
            session.close()
        self.memory = WorkspaceMemoryService(self.sessions, initialize=False)
        self.context = WorkspaceContextService(self.sessions, initialize=False, memories=self.memory)
        self.actor_a = SimpleNamespace(user_id="user-a", workspace_id="workspace-a", role="OWNER")
        self.actor_b = SimpleNamespace(user_id="user-b", workspace_id="workspace-b", role="OWNER")
        self.mission = {"id": "mission-a", "workspace_id": "workspace-a", "title": "Evidence review", "status": "PLANNING", "evidence_refs": [{"paper_id": "p-1"}]}

    def tearDown(self):
        self.engine.dispose()

    def test_context_joins_only_authorized_workspace_data(self):
        preference = self.memory.save_user_preference("workspace-a", "user-a", "Concise updates", "Prefer concise evidence-backed summaries.")
        payload = self.context.build(self.mission, actor=self.actor_a)
        self.assertEqual(payload["workspace"]["name"], "Research A")
        self.assertEqual(payload["knowledge"]["approved_assets"], 1)
        self.assertEqual(payload["knowledge"]["approved_decisions"], 1)
        self.assertEqual(payload["memory"]["selected"][0]["id"], preference["id"])
        self.assertIn("relevant", payload["memory"]["selected"][0]["selection_reason"].lower())
        self.assertNotIn("prompt", payload["memory"]["selected"][0])
        self.assertNotIn("cot", payload["memory"]["selected"][0])

    def test_context_selects_only_approved_workspace_artifact_summaries(self):
        payload = self.context.build(self.mission, actor=self.actor_a)
        self.assertEqual(len(payload["artifacts"]), 1)
        self.assertEqual(payload["artifacts"][0]["title"], "Low-carbon materials review")
        self.assertNotIn("file_path", payload["artifacts"][0])
        self.assertIn("approved", payload["artifacts"][0]["selection_reason"].lower())

    def test_context_retrieval_explains_ranking_without_internal_reasoning(self):
        record = self.memory.save_user_preference("workspace-a", "user-a", "Low-carbon focus", "Prefer low-carbon material comparisons.")
        payload = self.context.build(self.mission, actor=self.actor_a)
        explanation = payload["memory"]["explainability"]
        self.assertGreaterEqual(explanation["candidate_counts"]["authorized_memory"], 1)
        self.assertIn("Mission relevance", explanation["ranking_criteria"])
        selected = next(item for item in explanation["selected_context"] if item["title"] == record["title"])
        self.assertIsInstance(selected["score"], int)
        self.assertNotIn("prompt", selected)
        self.assertNotIn("chain_of_thought", selected)

    def test_context_rejects_cross_workspace_actor(self):
        with self.assertRaises(PermissionError):
            self.context.build(self.mission, actor=self.actor_b)

    def test_research_memory_is_user_visible_traceable_and_deletable(self):
        record = self.memory.save_user_preference("workspace-a", "user-a", "Output preference", "Prefer a concise delivery review.")
        self.assertEqual(self.memory.list("workspace-b", user_id="user-b"), [])
        explanation = self.memory.explain(record["id"], "workspace-a", user_id="user-a")
        self.assertIn("traceable", explanation["explanation"].lower())
        self.assertEqual(self.memory.delete(record["id"], "workspace-a", user_id="user-a"), {"id": record["id"], "deleted": True})
        self.assertEqual(self.memory.list("workspace-a", user_id="user-a"), [])

    def test_sensitive_memory_is_rejected(self):
        with self.assertRaises(WorkspaceMemoryError):
            self.memory.save_user_preference("workspace-a", "user-a", "API key", "Store my secret token")

    def test_memory_lifecycle_records_use_validation_and_archive(self):
        record = self.memory.save_user_preference("workspace-a", "user-a", "Research style", "Prefer concise evidence summaries.")
        self.assertEqual(record["importance_score"], 55)
        self.memory.mark_used([record["id"]], "workspace-a")
        used = self.memory.list("workspace-a", user_id="user-a")[0]
        self.assertEqual(used["lifecycle_state"], "IN_USE")
        self.assertEqual(used["use_count"], 1)
        verified = self.memory.validate(record["id"], "workspace-a")
        self.assertEqual(verified["lifecycle_state"], "VERIFIED")
        self.assertEqual(self.memory.archive(record["id"], "workspace-a", user_id="user-a"), {"id": record["id"], "archived": True})
        self.assertEqual(self.memory.list("workspace-a", user_id="user-a"), [])

    def test_ai_team_orchestrator_requires_matching_context(self):
        orchestrator = AITeamOrchestrator()
        self.assertEqual(orchestrator.plan(_Registry(), self.mission, {"workspace": {"id": "workspace-a"}}), [])
        with self.assertRaises(PermissionError):
            orchestrator.plan(_Registry(), self.mission, {"workspace": {"id": "workspace-b"}})

    def test_ai_team_orchestrator_orders_only_existing_runnable_skills(self):
        plan = AITeamOrchestrator().plan(
            _PlannedRegistry(), self.mission, {"workspace": {"id": "workspace-a"}},
            understanding={"required_capabilities": ["computer", "research"]},
        )
        self.assertEqual([skill_id for skill_id, _ in plan], ["computer", "research", "review"])

    def test_ai_team_plan_explains_deferred_capabilities_without_creating_skills(self):
        summary = AITeamOrchestrator().plan_summary(
            _PlannedRegistry(), self.mission, {"workspace": {"id": "workspace-a"}, "memory": {"selected": [], "evidence_refs": []}},
            understanding={"required_capabilities": ["delivery", "research"]},
        )
        self.assertEqual([step["skill_id"] for step in summary["steps"]], ["research", "computer", "review"])
        self.assertEqual(summary["deferred"], [{"skill_id": "delivery", "status": "DEFERRED", "reason": "Delivery begins only after a Mission has approved, traceable Evidence."}])
        self.assertNotIn("prompt", str(summary).lower())

    def test_capability_catalog_is_product_safe(self):
        catalog = SkillCapabilityRegistry().catalog()
        self.assertEqual({row["id"] for row in catalog}, {"research", "computer", "delivery", "review"})
        self.assertNotIn("prompt", str(catalog).lower())


if __name__ == "__main__":
    unittest.main()
