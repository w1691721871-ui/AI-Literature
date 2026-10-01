"""P28 Copilot tests use in-memory databases and never call RAG/FAISS."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.agent_memory import AgentMemory
from app.models.agent_trace import AgentTrace
from app.models.copilot_message import CopilotMessage
from app.models.copilot_session import CopilotSession
from app.models.computer_mission import ComputerMission
from app.models.execution_graph import ExecutionGraph
from app.models.notification import Notification
from app.models.planner_trace import PlannerTrace
from app.services.copilot_mission_service import CopilotMissionService

class CopilotTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:");self.Session=sessionmaker(bind=self.engine)
        for table in (AIMission.__table__,AIMissionEvent.__table__,AgentMemory.__table__,AgentTrace.__table__,CopilotMessage.__table__,CopilotSession.__table__,ComputerMission.__table__,ExecutionGraph.__table__,Notification.__table__,PlannerTrace.__table__):table.create(self.engine)
        self.service=CopilotMissionService(self.Session,initialize=False)
    def tearDown(self):self.engine.dispose()
    def test_session_intent_and_mission_use_existing_planner(self):
        session=self.service.create_session(); chat=self.service.chat(session["id"],"设计企业 AI 解决方案")
        self.assertEqual(chat["intent"],"SOLUTION")
        started=self.service.start(session["id"])
        self.assertTrue(started["mission"]["id"])
        s=self.Session(); self.assertGreater(s.query(ExecutionGraph).count(),0);s.close()
    def test_computer_route_and_activity_are_safe(self):
        session=self.service.create_session();self.assertEqual(self.service.chat(session["id"],"修复 Python API bug")["intent"],"COMPUTER")
        started=self.service.start(session["id"]);activity=self.service.activity(session["id"])
        self.assertEqual(activity["session_id"],session["id"]);self.assertEqual(started["intent"],"COMPUTER")
    def test_secret_is_redacted_and_cot_is_not_saved(self):
        session=self.service.create_session();self.service.chat(session["id"],"研究方向 api_key=abc123secretvalue")
        record=self.service.get(session["id"])
        text=" ".join(item["content_summary"] for item in record["messages"])
        self.assertNotIn("abc123secretvalue",text);self.assertNotIn("chain_of_thought",text)
    def test_intent_variants_and_session_analytics(self):
        session=self.service.create_session();self.assertEqual(self.service.chat(session["id"],"生成研究报告")["intent"],"REPORT")
        self.assertEqual(self.service.analytics()["sessions"],1)

if __name__=="__main__":unittest.main()
