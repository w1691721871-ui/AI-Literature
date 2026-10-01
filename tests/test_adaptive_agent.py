"""P27 finite-loop tests using only disposable in-memory fixtures."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.agent_trace import AgentTrace
from app.models.agent_evaluation import AgentEvaluation
from app.models.computer_mission import ComputerMission
from app.models.execution_graph import ExecutionGraph
from app.models.adaptive_iteration import AdaptiveIteration
from app.services.adaptive_agent_service import AdaptiveAgentService

class Retrieval:
    def retrieve(self,*_args,**_kwargs): return [{"paper_id":"real-fixture-paper","chunk_id":"real-fixture-chunk","filename":"authorized.pdf","section":"Results"}]

class AdaptiveAgentTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:");self.Session=sessionmaker(bind=self.engine)
        for table in (AIMission.__table__,AIMissionEvent.__table__,AgentTrace.__table__,AgentEvaluation.__table__,ComputerMission.__table__,ExecutionGraph.__table__,AdaptiveIteration.__table__):table.create(self.engine)
        self.service=AdaptiveAgentService(self.Session,initialize=False,retrieval=Retrieval())
    def tearDown(self):self.engine.dispose()
    def _mission(self,mid="m1",status="PLANNING",refs="[]",iteration=0):
        s=self.Session();s.add(AIMission(id=mid,title="fixture",mission_type="RESEARCH",goal="compare research",status=status,evidence_refs_json=refs,adaptive_iteration=iteration,max_iterations=3));s.add(ExecutionGraph(mission_id=mid,node_name="Research",agent_name="Research Agent",status="PENDING",node_order=1));s.commit();s.close()
    def test_missing_evidence_uses_real_retrieval_and_continues(self):
        self._mission();result=self.service.run_once("m1")
        self.assertEqual(result["decision"],"CONTINUE");self.assertEqual(result["evidence_count"],1)
    def test_failed_mission_replans_and_preserves_graph_versions(self):
        self._mission(status="FAILED",refs='[{"paper_id":"p","chunk_id":"c"}]');result=self.service.run_once("m1")
        self.assertEqual(result["decision"],"REPLAN");self.assertEqual(len(self.service.graph_history("m1")),2)
    def test_computer_mission_never_auto_approves(self):
        self._mission(refs='[{"paper_id":"p","chunk_id":"c"}]');s=self.Session();s.add(ComputerMission(task_id="c1",mission_name="fixture",mission_id="m1",status="WAITING_APPROVAL"));s.commit();s.close()
        self.assertEqual(self.service.run_once("m1")["decision"],"REQUEST_REVIEW")
    def test_iteration_cap_forces_review_without_infinite_loop(self):
        self._mission(iteration=2,refs='[{"paper_id":"p","chunk_id":"c"}]');result=self.service.run_once("m1")
        self.assertEqual(result["decision"],"REQUEST_REVIEW");self.assertEqual(result["trigger"],"MAX_ITERATIONS_REACHED")
        self.assertEqual(self.service.run_once("m1")["iteration"],3)
        self.assertEqual(len(self.service.iterations("m1")),1)
    def test_iterations_are_traceable_and_review_is_explicit(self):
        self._mission(iteration=2,refs='[{"paper_id":"p","chunk_id":"c"}]');self.service.run_once("m1")
        self.assertEqual(self.service.iterations("m1")[0]["iteration"],3)
        self.assertEqual(self.service.review("m1","APPROVE")["status"],"PLANNING")

if __name__=="__main__":unittest.main()
