"""P55 contract/state tests for the unified Mission Runtime."""

from __future__ import annotations

import unittest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.mission_contract import MissionContract, RuntimeExecutionState
from app.models.runtime_execution import RuntimeExecution
from app.services.ai_worker_runtime import AIWorkerRuntime
from app.services.ai_worker_service import AIWorkerService
from app.services.database import Base
from app.services.skill_registry import SkillAdapter, SkillRegistry, SkillResult


class _MissionService:
    def __init__(self, mission): self.mission = mission
    def detail(self, mission_id): return dict(self.mission) if mission_id == self.mission["id"] else None


class _Skill(SkillAdapter):
    def __init__(self, name, result): self.name=name; self.description=name; self.result=result; self.calls=0
    def execute(self, mission): self.calls += 1; return self.result


class _Adaptive:
    def run_once(self, mission_id): return {"decision":"REQUEST_REVIEW","summary":"Evidence remains insufficient."}


class _Context:
    """Keeps legacy runtime tests focused on lifecycle, not database seeding."""
    def build(self, mission, *, actor=None):
        return {"workspace": {"id": mission["workspace_id"], "name": "Test Workspace"}, "mission": {"id": mission["id"]}, "knowledge": {}, "memory": {"workspace": [], "user": [], "mission": [], "knowledge": []}, "boundary": "test"}

    def presentation(self, context): return {"workspace": context["workspace"], "mission": context["mission"], "knowledge": {}, "memory_counts": {}, "boundary": "test"}


class _Memory:
    def record_mission_summary(self, mission, *, owner_id=None): return None


class UnifiedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:",connect_args={"check_same_thread":False})
        Base.metadata.create_all(self.engine); self.sessions=sessionmaker(bind=self.engine,autoflush=False,autocommit=False)
        self.mission={"id":"p55-mission","title":"Scoped goal","goal":"Analyze verified evidence","workspace_id":"workspace-a","type":"RESEARCH","status":"PLANNING","current_step":"Planning","evidence_refs":[],"computer_missions":[]}

    def tearDown(self): self.engine.dispose()

    def runtime(self, adapters):
        return AIWorkerRuntime(self.sessions,initialize=False,mission_service=_MissionService(self.mission),worker_service=AIWorkerService(),registry=SkillRegistry(adapters=adapters),adaptive_service=_Adaptive(),context_service=_Context(),workspace_memory_service=_Memory())

    def test_creates_workspace_bound_mission_contract(self):
        runtime=self.runtime({"research":_Skill("Research Skill",SkillResult("WAITING_REVIEW","Evidence observed","Review needed")),"review":_Skill("Review Skill",SkillResult("WAITING_REVIEW","",""))})
        runtime.snapshot("p55-mission")
        session=self.sessions()
        try:
            row=session.scalar(select(MissionContract).where(MissionContract.mission_id=="p55-mission"))
            self.assertEqual(row.workspace_id,"workspace-a"); self.assertEqual(row.task_type,"RESEARCH")
            self.assertNotIn("prompt", row.input_context.lower())
        finally: session.close()

    def test_runtime_records_observation_and_waiting_approval(self):
        research=_Skill("Research Skill",SkillResult("WAITING_REVIEW","Two references collected.","Human review required."))
        runtime=self.runtime({"research":research,"review":_Skill("Review Skill",SkillResult("WAITING_REVIEW","",""))})
        runtime.execute("p55-mission")
        session=self.sessions()
        try:
            state=session.scalar(select(RuntimeExecutionState).where(RuntimeExecutionState.mission_id=="p55-mission"))
            self.assertEqual(state.current_step,"WAITING_APPROVAL"); self.assertEqual(state.current_skill,"Research Skill")
            self.assertEqual(session.scalar(select(RuntimeExecution).where(RuntimeExecution.mission_id=="p55-mission")).status,"WAITING_REVIEW")
        finally: session.close()

    def test_evidence_stop_condition_is_user_readable(self):
        runtime=self.runtime({"research":_Skill("Research Skill",SkillResult("NEEDS_EVIDENCE","No Evidence observed.","Evidence is required.")),"review":_Skill("Review Skill",SkillResult("WAITING_REVIEW","",""))})
        result=runtime.execute("p55-mission")
        self.assertEqual(result["status"],"WAITING_REVIEW")
        self.assertIn("Evidence",result["timeline"][-1]["result_summary"])

    def test_contract_does_not_cross_workspace(self):
        runtime=self.runtime({"research":_Skill("Research Skill",SkillResult("SUCCESS","","")),"review":_Skill("Review Skill",SkillResult("WAITING_REVIEW","",""))})
        runtime.snapshot("p55-mission")
        session=self.sessions()
        try:
            row=session.scalar(select(MissionContract).where(MissionContract.mission_id=="p55-mission"))
            self.assertEqual(row.workspace_id,"workspace-a")
        finally: session.close()


if __name__=="__main__": unittest.main()
