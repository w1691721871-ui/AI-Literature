"""P58 deterministic Research Intelligence tests; no database or index is touched."""

from __future__ import annotations

import unittest

from app.services.ai_worker_runtime import ResearchOrchestrator
from app.services.research_strategy_service import ResearchStrategyService


class ResearchIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.service = ResearchStrategyService()
        self.refs = [
            {"paper_id": "paper-a", "chunk_id": "chunk-1", "source": "Paper A", "section": "Results", "workspace_id": "workspace-a"},
            {"paper_id": "paper-b", "chunk_id": "chunk-2", "source": "Paper B", "section": "Limitations", "workspace_id": "workspace-a"},
        ]

    def test_goal_analysis_creates_user_readable_strategy_without_reasoning_trace(self):
        strategy = self.service.research_goal_analysis("Compare RAG retrieval performance and limitations", self.refs)
        self.assertEqual(strategy["research_goal"], "Compare RAG retrieval performance and limitations")
        self.assertEqual(len(strategy["research_questions"]), 3)
        self.assertIn("Retrieval", strategy["knowledge_areas"])
        self.assertIn("Evaluation", strategy["knowledge_areas"])
        self.assertNotIn("prompt", str(strategy).lower())
        self.assertNotIn("chain", str(strategy).lower())

    def test_gap_analysis_keeps_findings_bound_to_existing_evidence(self):
        result = self.service.gap_analysis(self.refs, workspace_id="workspace-a")
        self.assertEqual(result["status"], "EVIDENCE_REVIEW_REQUIRED")
        self.assertTrue(result["established_findings"])
        for group in result["established_findings"] + result["uncertain_areas"] + result["potential_gaps"]:
            self.assertTrue(group["evidence_refs"])
            for ref in group["evidence_refs"]:
                self.assertIn(ref["chunk_id"], {"chunk-1", "chunk-2"})

    def test_no_evidence_cannot_create_trusted_innovation_conclusion(self):
        result = self.service.gap_analysis([])
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["established_findings"], [])
        self.assertEqual(result["research_opportunities"], [])
        self.assertIn("No innovation", result["boundary"])

    def test_workspace_filter_excludes_foreign_evidence(self):
        refs = self.refs + [{"paper_id": "paper-private", "chunk_id": "chunk-private", "source": "Other", "section": "Results", "workspace_id": "workspace-b"}]
        result = self.service.gap_analysis(refs, workspace_id="workspace-a")
        flattened = [ref for group in result["established_findings"] for ref in group["evidence_refs"]]
        self.assertEqual({ref["chunk_id"] for ref in flattened}, {"chunk-1", "chunk-2"})

    def test_research_orchestrator_exposes_strategy_as_a_projection_not_a_new_agent(self):
        mission = {"title": "RAG review", "goal": "Compare RAG methods", "workspace_id": "workspace-a", "evidence_refs": self.refs}
        insight = ResearchOrchestrator(self.service).research_insight(mission)
        self.assertIn("strategy", insight)
        self.assertIn("gap_analysis", insight)
        self.assertEqual(len(insight["innovation_proposals"]), 1)
        self.assertEqual(insight["innovation_proposals"][0]["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
