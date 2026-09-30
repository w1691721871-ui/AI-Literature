"""P26 fixture-only tests. No production RAG, SQLite or FAISS state is used."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.agent.planner_agent import PlannerAgent
from app.models.ai_mission import AIMission
from app.models.agent_evaluation import AgentEvaluation
from app.models.agent_memory import AgentMemory
from app.models.computer_mission import ComputerMission
from app.models.execution_graph import ExecutionGraph
from app.models.planner_trace import PlannerTrace
from app.services.agent_evaluation_service import AgentEvaluationService
from app.services.agent_memory_service import AgentMemoryService
from app.services.dynamic_planner_service import DynamicPlannerService

class DynamicPlannerTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:"); self.Session=sessionmaker(bind=self.engine)
        for table in (AIMission.__table__,ExecutionGraph.__table__,PlannerTrace.__table__,AgentMemory.__table__,AgentEvaluation.__table__,ComputerMission.__table__): table.create(self.engine)
        self.memories=AgentMemoryService(self.Session,initialize=False)
        self.service=DynamicPlannerService(self.Session,initialize=False,memories=self.memories)
    def tearDown(self): self.engine.dispose()
    def _mission(self, mid="plan-1", goal="比较 RAG 技术路线并生成方案"):
        s=self.Session();s.add(AIMission(id=mid,title="fixture",mission_type="SOLUTION",goal=goal,status="COMPLETED"));s.commit();s.close()
    def test_planner_builds_distinct_safe_agent_selection(self):
        research=PlannerAgent().analyze("比较 RAG 方法并生成交付方案","SOLUTION")
        coding=PlannerAgent().analyze("修复 Python API bug","RESEARCH")
        self.assertIn("Literature Agent",research["required_agents"])
        self.assertNotIn("Computer Agent",research["required_agents"])
        self.assertIn("Computer Agent",coding["required_agents"])
        self.assertNotIn("chain",str(research).lower())
    def test_execution_graph_and_plan_are_persisted(self):
        self._mission(); plan=self.service.analyze("比较 RAG 技术路线并生成方案","SOLUTION","plan-1")
        saved=self.service.plan("plan-1")
        self.assertEqual(saved["selected_agents"],plan["required_agents"])
        self.assertGreaterEqual(len(saved["execution_graph"]),4)
        self.assertEqual(saved["execution_graph"][0]["status"],"PENDING")
    def test_memory_is_review_gated_retrievable_and_deletable(self):
        memory=self.memories.candidate("m1","RAG delivery requires evidence review before output.")
        self.assertEqual(self.memories.retrieve("RAG delivery"),[])
        s=self.Session(); s.get(AgentMemory,memory["id"]).status="CONFIRMED"; s.commit(); s.close()
        self.assertEqual(len(self.memories.retrieve("RAG delivery")),1)
        self.assertTrue(self.memories.delete(memory["id"])["deleted"])
    def test_planner_evaluation_is_explainable_and_uses_graph(self):
        self._mission(); self.service.analyze("比较 RAG 技术路线并生成方案","SOLUTION","plan-1")
        report=AgentEvaluationService(self.Session,initialize=False).evaluate("plan-1")
        self.assertEqual(report["planner_score"],100)
        self.assertNotIn("prompt",report)

if __name__=="__main__": unittest.main()
