"""Fixture-only tests for Research Workflow Studio orchestration."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.research_workflow_agent import ResearchWorkflowAgent
from app.services.database import Base
from app.services.research_workspace_intelligence_service import ResearchWorkspaceIntelligenceService


class Diagnostics:
    def __init__(self, counts): self.counts = counts
    def run(self): return {"counts": self.counts}


class Master:
    def __init__(self): self.calls = 0
    def run_task(self, goal, selected_agents, paper_ids):
        self.calls += 1
        return {"master_plan": {"user_goal": goal}, "executive_summary": "fixture only", "boundary_note": "fixture boundary", "report": {},
                "sources": [{"paper_id": "paper-a", "chunk_id": "chunk-a", "paper_title": "Fixture A", "section": "Method", "score": .8}],
                "finite_loop": {"stop_reason": "SUFFICIENT_EVIDENCE", "requires_human_review": False, "strategy": {"strategy_type": "comparison"}, "subtasks": [], "conflict_report": {"status": "no_conflict"}}}


class Copilot:
    def intelligence(self, workspace_id): return {"workspace_id": workspace_id, "follow_up_suggestions": [], "boundary": "fixture"}


class Computer:
    def preview_task(self, goal): return {"task_type": "experiment_plan", "plan": [], "expected_output": "fixture"}


class ResearchWorkflowAgentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.workspace_service = ResearchWorkspaceIntelligenceService(self.Session, initialize=False)
        self.master = Master()

    def tearDown(self): self.engine.dispose()

    def test_preview_creates_dynamic_steps_without_claims_or_evidence(self):
        agent = ResearchWorkflowAgent(self.master, self.workspace_service, Diagnostics({"papers": 0, "chunks": 0, "embedded_chunks": 0}), Copilot(), Computer(), self.Session, initialize=False)
        workflow = agent.create("分析当前方向的研究空白")
        self.assertEqual(workflow["workflow_type"], "research_gap")
        self.assertEqual(workflow["status"], "CREATED")
        self.assertTrue(all(step["status"] == "PENDING" for step in workflow["steps"]))
        self.assertEqual(workflow["events"][0]["agent_name"], "Planner Agent")
        self.assertNotIn("prompt", workflow)

    def test_insufficient_evidence_blocks_before_master_execution(self):
        agent = ResearchWorkflowAgent(self.master, self.workspace_service, Diagnostics({"papers": 0, "chunks": 0, "embedded_chunks": 0}), Copilot(), Computer(), self.Session, initialize=False)
        workflow = agent.create("生成研究方案")
        result = agent.execute(workflow["id"])
        self.assertEqual(self.master.calls, 0)
        self.assertEqual(result["result_status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["status"], "WAITING_EVIDENCE")
        self.assertTrue(all(step["status"] == "BLOCKED" for step in result["steps"]))

    def test_real_agent_contract_is_orchestrated_with_source_refs(self):
        agent = ResearchWorkflowAgent(self.master, self.workspace_service, Diagnostics({"papers": 1, "chunks": 1, "embedded_chunks": 1}), Copilot(), Computer(), self.Session, initialize=False)
        workflow = agent.create("设计实验验证方案")
        result = agent.execute(workflow["id"])
        self.assertEqual(self.master.calls, 1)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["sources"][0]["chunk_id"], "chunk-a")
        self.assertTrue(any(step["agent_type"] == "Computer Agent" and step["status"] == "COMPLETED" for step in result["steps"]))
        self.assertTrue(any(event["agent_name"] == "Writer Agent" for event in result["events"]))
        self.assertNotIn("chain_of_thought", result)


if __name__ == "__main__":
    unittest.main()
