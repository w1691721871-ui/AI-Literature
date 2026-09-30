"""P26 persistence adapter for deterministic planning and review-gated memory."""
from __future__ import annotations
import json
from sqlalchemy import select
from app.agent.planner_agent import PlannerAgent
from app.models.ai_mission import AIMission
from app.models.execution_graph import ExecutionGraph
from app.models.planner_trace import PlannerTrace
from app.services.agent_memory_service import AgentMemoryService
from app.services.database import SessionLocal, initialize_database

class DynamicPlannerService:
    def __init__(self, session_factory=SessionLocal, *, initialize=True, planner=None, memories=None):
        if initialize: initialize_database()
        self.sessions=session_factory; self.planner=planner or PlannerAgent()
        self.memories=memories or AgentMemoryService(session_factory, initialize=False)
    def analyze(self, goal, mission_type="RESEARCH", mission_id=None):
        context=self.memories.retrieve(goal)
        plan=self.planner.analyze(goal,mission_type,context)
        if mission_id: self._persist(mission_id,plan)
        return {**plan,"memory_context_count":len(context),"memory_boundary":"仅使用经人工确认的摘要化历史经验；不读取论文全文、Prompt、密钥或隐私文件。"}
    def plan(self,mission_id):
        s=self.sessions()
        try:
            trace=s.scalar(select(PlannerTrace).where(PlannerTrace.mission_id==mission_id).order_by(PlannerTrace.created_at.desc()))
            nodes=s.scalars(select(ExecutionGraph).where(ExecutionGraph.mission_id==mission_id).order_by(ExecutionGraph.node_order)).all()
            if not trace: raise ValueError("该 Mission 尚未生成 Planner Plan。")
            return {"mission_id":mission_id,"selected_agents":self._array(trace.selected_agents_json),"skipped_agents":self._array(trace.skipped_agents_json),"reason_summary":trace.reason_summary,"execution_graph":[{"id":x.id,"node_name":x.node_name,"agent_name":x.agent_name,"status":x.status,"order":x.node_order,"depends_on":self._array(x.depends_on),"created_at":x.created_at} for x in nodes]}
        finally:s.close()
    def _persist(self,mission_id,plan):
        s=self.sessions()
        try:
            if not s.get(AIMission,mission_id): raise ValueError("Mission 不存在。")
            previous=s.scalars(select(ExecutionGraph).where(ExecutionGraph.mission_id==mission_id)).all()
            for row in previous:s.delete(row)
            s.add(PlannerTrace(mission_id=mission_id,selected_agents_json=json.dumps(plan["required_agents"],ensure_ascii=False),skipped_agents_json=json.dumps(plan["skip_agents"],ensure_ascii=False),reason_summary=plan["reason_summary"]))
            for node in plan["execution_graph"]:
                s.add(ExecutionGraph(mission_id=mission_id,node_name=node["node_name"],agent_name=node["agent_name"],status=node["status"],node_order=node["order"],depends_on=json.dumps(node["depends_on"],ensure_ascii=False)))
            s.commit()
        finally:s.close()
    @staticmethod
    def _array(value):
        try:
            result=json.loads(value or "[]")
            return result if isinstance(result,list) else []
        except (ValueError,TypeError): return []
