"""Fixture-only lifecycle tests for P3 product intelligence workspaces."""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import ResearchMemory, ResearchWorkspace  # noqa: F401 - register models
from app.services.database import Base
from app.services.research_deliverable_service import ResearchDeliverableService
from app.services.research_workspace_intelligence_service import ResearchWorkspaceIntelligenceService


def fixture_result(*, conflict: bool = False) -> dict[str, object]:
    sources = [
        {"paper_id": "paper-a", "chunk_id": "chunk-a", "paper_title": "真实资料 A", "section": "方法", "score": 0.82},
        {"paper_id": "paper-b", "chunk_id": "chunk-b", "paper_title": "真实资料 B", "section": "实验", "score": 0.71},
    ]
    return {
        "master_plan": {"user_goal": "比较研究方法的适用条件"},
        "executive_summary": "fixture only: evidence-backed summary.",
        "boundary_note": "fixture boundary",
        "report": {"背景分析": "fixture"},
        "sources": sources,
        "finite_loop": {
            "status": "stopped" if conflict else "completed",
            "stop_reason": "NEEDS_HUMAN_REVIEW" if conflict else "SUFFICIENT_EVIDENCE",
            "requires_human_review": conflict,
            "strategy": {"strategy_type": "comparison", "research_objective": "比较", "subtasks": [], "reasoning_basis": ["fixture"], "expected_evidence": ["fixture"], "stop_condition": "fixture"},
            "subtasks": [{"subtask_id": "subtask_1", "title": "性能与条件比较", "status": "completed", "evidence_refs": ["paper-a:chunk-a"], "decision": {"status": "sufficient"}, "conflict_report": {"status": "no_conflict"}}],
            "conflict_report": {"status": "context_difference" if conflict else "no_conflict", "requires_human_review": conflict, "count": 1 if conflict else 0},
            "research_gaps": ["需要人工复核条件"],
        },
    }


class ResearchWorkspaceIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.service = ResearchWorkspaceIntelligenceService(self.sessions, initialize=False)
        self.deliverables = ResearchDeliverableService()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_workspace_lifecycle_create_save_and_resume(self) -> None:
        workspace = self.service.resolve_or_create("比较研究方法的适用条件")
        snapshot = self.service.save_run(workspace["workspace_id"], fixture_result(conflict=True))
        resumed = self.service.resume(workspace["workspace_id"])
        self.assertEqual(snapshot["strategy_type"], "comparison")
        self.assertEqual(resumed["research_goal"], "比较研究方法的适用条件")
        self.assertEqual(len(resumed["used_evidence"]), 2)
        self.assertTrue(resumed["human_review"]["required"])

    def test_decision_candidate_keeps_evidence_refs_and_human_review(self) -> None:
        workspace = self.service.resolve_or_create("比较研究方法")
        self.service.save_run(workspace["workspace_id"], fixture_result(conflict=True))
        candidate = self.service.decision_candidate(workspace["workspace_id"])
        self.assertEqual(candidate["confidence_level"], "needs_human_review")
        self.assertTrue(candidate["human_review"])
        self.assertEqual(candidate["evidence_refs"][0]["evidence_id"], "chunk-a")
        self.assertNotIn("一定有效", candidate["statement"])

    def test_deliverable_is_evidence_grounded_and_not_a_fact_claim(self) -> None:
        workspace = self.service.resolve_or_create("比较研究方法")
        snapshot = self.service.save_run(workspace["workspace_id"], fixture_result())
        draft = self.deliverables.generate(snapshot, self.service.decision_candidate(workspace["workspace_id"]), "literature_review")
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(len(draft["evidence_refs"]), 2)
        self.assertIn("需由科研负责人审核", draft["boundary"])

    def test_trace_snapshot_contains_only_public_execution_fields(self) -> None:
        workspace = self.service.resolve_or_create("总结研究资料")
        snapshot = self.service.save_run(workspace["workspace_id"], fixture_result())
        forbidden = {"prompt", "token", "chain_of_thought", "internal_reasoning"}
        self.assertFalse(forbidden & set(snapshot))
        self.assertEqual(snapshot["tasks"][0]["evidence_count"], 1)
        metrics = self.service.quality_metrics(workspace["workspace_id"])
        self.assertIn("evidence_coverage", metrics["metrics"])
        self.assertNotIn("accuracy", metrics["metrics"])


if __name__ == "__main__":
    unittest.main()
