"""P25 fixture-only observability tests; no production SQLite or FAISS writes."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission
from app.models.agent_trace import AgentTrace
from app.models.agent_evaluation import AgentEvaluation
from app.models.agent_metric import AgentMetric
from app.models.computer_mission import ComputerMission
from app.models.execution_graph import ExecutionGraph
from app.services.agent_evaluation_service import AgentEvaluationService

class AgentEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:"); self.Session=sessionmaker(bind=self.engine)
        for table in (AIMission.__table__,AgentTrace.__table__,AgentEvaluation.__table__,AgentMetric.__table__,ComputerMission.__table__,ExecutionGraph.__table__): table.create(self.engine)
        self.service=AgentEvaluationService(self.Session,initialize=False)
    def tearDown(self): self.engine.dispose()
    def test_trace_metrics_and_evidence_grounded_score(self):
        s=self.Session(); s.add(AIMission(id="m1",title="fixture",mission_type="RESEARCH",goal="",status="COMPLETED",evidence_refs_json='[{"paper_id":"p","chunk_id":"c"}]'))
        s.add(AgentTrace(trace_id="m1",mission_id="m1",step="Evidence Retrieval",message="5 evidence found",agent_name="Literature Agent",action="retrieve evidence",status="COMPLETED",tool_used="FAISS",evidence_count=1))
        s.commit(); s.close()
        report=self.service.evaluate("m1")
        self.assertEqual(report["evaluation_score"],100); self.assertEqual(report["evidence_coverage"],1)
        self.assertEqual(self.service.evaluations()[0]["mission_id"],"m1")
        self.assertEqual(self.service.traces("m1")[0]["tool_used"],"FAISS")
        self.assertEqual(self.service.metrics()[0]["success_count"],1)
        s=self.Session(); self.assertEqual(s.query(AgentMetric).count(),1); s.close()
    def test_failure_is_safe_and_no_cot_fields_exist(self):
        s=self.Session(); s.add(AIMission(id="m2",title="fixture",mission_type="RESEARCH",goal="",status="NEEDS_REVISION")); s.commit();s.close()
        report=self.service.evaluate("m2")
        self.assertEqual(report["failure_type"],"HUMAN_REJECT")
        self.assertNotIn("input_prompt",report); self.assertNotIn("chain_of_thought",report)

    def test_completed_computer_verification_is_scored(self):
        s=self.Session()
        s.add(AIMission(id="m3",title="fixture",mission_type="COMPUTER",goal="",status="COMPLETED",evidence_refs_json='[{"paper_id":"p","chunk_id":"c"}]'))
        s.add(ComputerMission(task_id="task-3",mission_name="fixture",mission_id="m3",status="COMPLETED",verification_json='{"status":"PASS"}'))
        s.commit(); s.close()
        report=self.service.evaluate("m3")
        self.assertEqual(report["verification_result"],"PASS")
        self.assertEqual(report["evaluation_score"],100)

    def test_security_block_is_classified_without_stack_trace(self):
        s=self.Session()
        s.add(AIMission(id="m4",title="fixture",mission_type="COMPUTER",goal="",status="FAILED"))
        s.add(ComputerMission(task_id="task-4",mission_name="fixture",mission_id="m4",status="SECURITY_BLOCK"))
        s.commit(); s.close()
        report=self.service.evaluate("m4")
        self.assertEqual(report["execution_safety"],"BLOCKED")
        self.assertEqual(report["failure_type"],"SECURITY_BLOCK")
        self.assertNotIn("traceback",report["failure_reason"].lower())

if __name__=="__main__": unittest.main()
