"""Fixture-only P35 tests: model output is always bounded by deterministic guards."""
from __future__ import annotations
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission
from app.models.agent_observation import AgentObservation
from app.models.agent_trace import AgentTrace
from app.services.agent_runtime_loop import AgentRuntimeLoop
from app.services.database import Base
from app.services.llm_gateway import LLMGateway
from app.services.plan_validation_service import PlanValidator, PlanValidationError
from app.services.tool_selector_service import ToolSelector

class _Gateway:
    def generate_plan(self,*_): return ({"goal":"fixture","agents":["Research Agent","Literature Agent"],"tools":["KNOWLEDGE_CONNECTOR"],"steps":["Collect evidence","Request review"],"risk_points":["Evidence may be insufficient"]},{"status":"SUCCESS","model":"fixture-model","latency":0.01,"token_usage_summary":"total:2"})
class _Mission:
    def run(self,_): return {"status":"WAITING_REVIEW"}

class LLMRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:"); Base.metadata.create_all(self.engine); self.sessions=sessionmaker(bind=self.engine,autoflush=False,autocommit=False)
        s=self.sessions();s.add(AIMission(id="mission-llm",title="Fixture mission",goal="Compare research evidence"));s.commit();s.close()
    def tearDown(self): self.engine.dispose()
    def test_gateway_is_safe_without_configuration(self):
        with patch.dict("os.environ", {"DASHSCOPE_API_KEY":""}, clear=False):
            plan,meta=LLMGateway().generate_plan("goal","RESEARCH",["Research Agent"],["KNOWLEDGE_CONNECTOR"])
        self.assertIsNone(plan);self.assertIn(meta["status"],{"NOT_CONFIGURED","FAILED"})
    def test_plan_validation_rejects_unknown_agent_and_tool(self):
        validator=PlanValidator()
        with self.assertRaises(PlanValidationError): validator.validate({"agents":["Unknown"],"tools":["SHELL"],"steps":["x"],"risk_points":[]})
    def test_tool_selection_is_bounded_and_policy_aware(self):
        selected=ToolSelector().select(["Research Agent","Computer Agent"],requested_tools=["KNOWLEDGE_CONNECTOR","COMPUTER_AGENT"],policy={"allowed_connectors":["KNOWLEDGE_CONNECTOR"]})
        self.assertEqual(selected,["KNOWLEDGE_CONNECTOR","COMPUTER_AGENT"])
    def test_runtime_records_observation_not_prompt_or_cot(self):
        result=AgentRuntimeLoop(self.sessions,initialize=False,gateway=_Gateway(),mission_service=_Mission()).execute("mission-llm")
        self.assertEqual(result["status"],"WAITING_REVIEW")
        s=self.sessions(); observation=s.query(AgentObservation).one();trace=s.query(AgentTrace).one();s.close()
        self.assertTrue(observation.success);self.assertEqual(trace.model_name,"fixture-model")
        self.assertFalse(hasattr(observation,"prompt"));self.assertFalse(hasattr(trace,"response"))
    def test_policy_and_permission_can_block_plan(self):
        with self.assertRaises(PlanValidationError): PlanValidator().validate({"agents":["Research Agent"],"tools":["KNOWLEDGE_CONNECTOR"],"steps":["one","two"],"risk_points":[]},policy={"max_iterations":1,"max_tool_calls":2})

if __name__ == "__main__": unittest.main()
