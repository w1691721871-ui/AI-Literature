"""P37 runs declared DEMO_ONLY scenarios through the existing Mission runtime."""
from __future__ import annotations
import json
from sqlalchemy import select
from app.models.enterprise_scenario import DemoDataSource, EnterpriseScenario, ScenarioRun
from app.services.agent_runtime_loop import AgentRuntimeLoop
from app.services.ai_mission_service import AIMissionService
from app.services.artifact_service import ArtifactService
from app.services.benchmark_service import BenchmarkService
from app.services.database import SessionLocal, initialize_database

class ScenarioError(ValueError): pass

class ScenarioDemoService:
    def __init__(self, sessions=SessionLocal, *, initialize=True, missions=None, runtime=None, artifacts=None, benchmarks=None):
        if initialize: initialize_database()
        self.s = sessions; self.missions = missions or AIMissionService(sessions, initialize=False)
        self.runtime = runtime or AgentRuntimeLoop(sessions, initialize=False); self.artifacts = artifacts or ArtifactService(sessions, initialize=False)
        self.benchmarks = benchmarks or BenchmarkService(sessions, initialize=False, missions=self.missions, runtime=self.runtime)
    def list(self):
        self._seed_demo(); s = self.s()
        try: return [self._scenario(row, s) for row in s.scalars(select(EnterpriseScenario).order_by(EnterpriseScenario.created_at.desc())).all()]
        finally: s.close()
    def run(self, scenario_id, *, permission_check=None, policy=None):
        self._seed_demo(); s = self.s()
        try: scenario = s.get(EnterpriseScenario, scenario_id)
        finally: s.close()
        if not scenario: raise ScenarioError("Scenario not found.")
        if permission_check: permission_check("MISSION_CREATE")
        mission = self.missions.create({"title": f"DEMO_ONLY · {scenario.name}", "mission_type": "ENTERPRISE", "goal": scenario.customer_need})
        s = self.s()
        try: run = ScenarioRun(scenario_id=scenario.id, mission_id=mission["id"], status="RUNNING"); s.add(run); s.commit(); s.refresh(run)
        finally: s.close()
        try:
            runtime_result = self.runtime.execute(mission["id"], policy=policy, permission_check=permission_check)
            artifact = self.artifacts.generate(mission["id"], "SOLUTION_DOCUMENT")
            benchmark = self.benchmarks.track_existing_mission({"name": f"DEMO_ONLY · {scenario.name}", "category": "ENTERPRISE", "difficulty": "MEDIUM", "description": scenario.customer_need, "expected_agents": self._decode(scenario.expected_agents_json), "expected_tools": self._decode(scenario.expected_tools_json), "evaluation_rules": {"source": "DEMO_ONLY"}}, mission["id"], runtime_result)
            s = self.s()
            try:
                row = s.get(ScenarioRun, run.id); row.status = "COMPLETED"; row.artifact_id = artifact["id"]; row.benchmark_run_id = benchmark["id"]; s.commit()
            finally: s.close()
            return self.detail(run.id)
        except Exception:
            s = self.s()
            try: row = s.get(ScenarioRun, run.id); row.status = "READY"; s.commit()
            finally: s.close()
            raise
    def detail(self, run_id):
        s = self.s()
        try:
            row = s.get(ScenarioRun, run_id)
            if not row: raise ScenarioError("Scenario run not found.")
            scenario = s.get(EnterpriseScenario, row.scenario_id); mission = self.missions.detail(row.mission_id)
            artifact = self.artifacts.detail(row.artifact_id) if row.artifact_id else None; benchmark = self.benchmarks.detail(row.benchmark_run_id) if row.benchmark_run_id else None
            return {"id": row.id, "status": row.status, "scenario": self._scenario(scenario, s), "mission": mission, "timeline": mission.get("timeline", []), "artifact": artifact, "benchmark": benchmark, "boundary": "DEMO_ONLY scenario. It is not a customer case, does not claim enterprise outcomes, and every generated artifact remains subject to Human Review."}
        finally: s.close()
    def _seed_demo(self):
        s = self.s()
        try:
            existing = s.scalar(select(EnterpriseScenario).where(EnterpriseScenario.name == "智能制造 AI 优化方案"))
            if existing: return
            row = EnterpriseScenario(name="智能制造 AI 优化方案", industry="MANUFACTURING", description="DEMO_ONLY · 演示从客户需求、受控资料检索、风险提示到待审核方案草稿的同一条 Mission 链路。", customer_need="DEMO_ONLY：评估智能制造优化方案的资料准备与研究支持范围。仅基于已有可验证 Evidence 输出待确认的风险、方案与下一步；资料不足时明确标记 NEEDS_CONFIRMATION。", expected_agents_json=json.dumps(["Research Agent", "Literature Agent", "Delivery Agent"]), expected_tools_json=json.dumps(["KNOWLEDGE_CONNECTOR"]))
            s.add(row); s.flush(); s.add(DemoDataSource(scenario_id=row.id, label="智能制造场景说明", description="DEMO_ONLY 元数据，不包含企业数据、企业收益或可作为科研 Evidence 的内容。")); s.commit()
        finally: s.close()
    @staticmethod
    def _decode(value):
        try: return json.loads(value or "[]")
        except json.JSONDecodeError: return []
    def _scenario(self, row, s):
        return {"id": row.id, "name": row.name, "industry": row.industry, "description": row.description, "customer_need": row.customer_need, "expected_agents": self._decode(row.expected_agents_json), "expected_tools": self._decode(row.expected_tools_json), "data_sources": [{"label": x.label, "classification": x.classification, "description": x.description} for x in s.scalars(select(DemoDataSource).where(DemoDataSource.scenario_id == row.id)).all()], "created_at": row.created_at}
