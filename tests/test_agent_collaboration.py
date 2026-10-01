import json
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.agent_collaboration import AgentConflict,AgentMessage,CollaborationGraph
from app.models.agent_trace import AgentTrace
from app.models.ai_mission import AIMission,AIMissionEvent
from app.services.agent_collaboration_service import AgentMessageBus,AgentMessageError


class CollaborationTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:");self.Session=sessionmaker(bind=self.engine)
        for table in (AIMission.__table__,AIMissionEvent.__table__,AgentTrace.__table__,AgentMessage.__table__,CollaborationGraph.__table__,AgentConflict.__table__):table.create(self.engine)
        session=self.Session();session.add(AIMission(id="m1",title="Research",mission_type="RESEARCH",goal="Compare evidence",status="PLANNING",evidence_refs_json=json.dumps([{ "paper_id":"p1","chunk_id":"c1","source":"Indexed paper" }])));session.commit();session.close();self.bus=AgentMessageBus(self.Session,initialize=False)
    def tearDown(self):self.engine.dispose()
    def send(self,kind="REQUEST",sender="Research Agent",receiver="Literature Agent",summary="Please provide a summary of indexed evidence."):
        return self.bus.send({"mission_id":"m1","sender_agent":sender,"receiver_agent":receiver,"message_type":kind,"payload_summary":summary})
    def test_message_context_graph_and_trace(self):
        message=self.send();self.assertEqual(message["status"],"DELIVERED")
        self.send("RESULT","Literature Agent","Research Agent","Evidence summary: one indexed source is available.")
        context=self.bus.context.exchange("m1");self.assertEqual(context["evidence_summary"]["count"],1);self.assertEqual(len(context["previous_results"]),1)
        graph=self.bus.graph("m1");self.assertEqual(graph["message_count"],2);self.assertIn("Research Agent",graph["participants"])
    def test_warning_requires_human_review_and_no_auto_resolution(self):
        self.send("WARNING","Risk Agent","Research Agent","Risk is high under the currently recorded condition; human review is required.")
        conflict=self.bus.conflicts("m1")[0];self.assertEqual(conflict["status"],"WAITING_HUMAN_REVIEW")
        self.assertEqual(self.bus.graph("m1")["status"],"WAITING_HUMAN_REVIEW")
    def test_permissions_sensitive_content_and_loop_limit(self):
        with self.assertRaises(AgentMessageError):self.send("WARNING","Literature Agent","Research Agent","Unsafe warning")
        with self.assertRaises(AgentMessageError):self.send(summary="system prompt: hidden")
        for _ in range(10):self.send()
        with self.assertRaises(AgentMessageError):self.send()
        self.assertTrue(self.bus.conflicts("m1"))
    def test_analytics_is_summary_only(self):
        self.send();analytics=self.bus.analytics();self.assertEqual(analytics["message_count"],1);self.assertIn("prompts",analytics["boundary"])

if __name__=="__main__":unittest.main()
