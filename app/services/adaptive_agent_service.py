"""P27 finite adaptive decision gate. It never approves Computer actions."""
from __future__ import annotations
import json
from sqlalchemy import select
from app.models.adaptive_iteration import AdaptiveIteration
from app.models.agent_trace import AgentTrace
from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.computer_mission import ComputerMission
from app.models.execution_graph import ExecutionGraph
from app.services.agent_evaluation_service import AgentEvaluationService
from app.services.database import SessionLocal, initialize_database
from app.services.retrieval_service import RetrievalService

class AdaptiveDecisionEngine:
    MAX_ITERATIONS=3
    def decide(self, *, iteration, max_iterations, evidence_count, mission_status, computer_rows, all_required_completed):
        if iteration >= min(max_iterations,self.MAX_ITERATIONS): return ("REQUEST_REVIEW","MAX_ITERATIONS_REACHED","达到有限自适应循环上限，需人工决定后续路径。")
        if any(row.status in {"WAITING_APPROVAL","APPROVED","SECURITY_BLOCK","NEEDS_REVISION"} for row in computer_rows): return ("REQUEST_REVIEW","COMPUTER_REVIEW_REQUIRED","Computer Diff 或验证需要人工审核；系统不会自动批准或重试写入。")
        if mission_status=="FAILED": return ("REPLAN","TOOL_FAILURE","任务失败且尚有有限重规划预算，将生成新的可审阅执行图。")
        if evidence_count==0: return ("REQUEST_EVIDENCE","EVIDENCE_INSUFFICIENT","尚无可追溯 Evidence，先通过现有 RAG 请求真实资料。")
        if all_required_completed: return ("COMPLETE","REQUIRED_NODES_COMPLETED","必需节点已完成且存在 Evidence，交由现有 Human Review / Delivery 流程。")
        return ("CONTINUE","NEXT_NODE_PENDING","当前图仍有待执行节点，继续现有受控流程。")

class AdaptiveAgentService:
    def __init__(self, session_factory=SessionLocal, *, initialize=True, retrieval=None, evaluator=None, engine=None):
        if initialize: initialize_database()
        self.sessions=session_factory; self.retrieval=retrieval or RetrievalService(session_factory=session_factory)
        self.evaluator=evaluator or AgentEvaluationService(session_factory,initialize=False); self.engine=engine or AdaptiveDecisionEngine()
    def run_once(self, mission_id):
        s=self.sessions()
        try:
            mission=s.get(AIMission,mission_id)
            if not mission: raise ValueError("Mission 不存在。")
            previous_state=mission.status
            max_iterations=min(mission.max_iterations,self.engine.MAX_ITERATIONS)
            if mission.adaptive_iteration >= max_iterations:
                mission.status="WAITING_ADAPTIVE_REVIEW"; mission.current_step="Adaptive Human Review"
                s.commit()
                return {"mission_id":mission_id,"decision":"REQUEST_REVIEW","trigger":"MAX_ITERATIONS_REACHED","summary":"已达到有限循环上限，不能继续自动执行。","iteration":mission.adaptive_iteration,"max_iterations":max_iterations,"evidence_count":len(self._array(mission.evidence_refs_json)),"graph_version":1,"evaluation":self.evaluator.evaluate(mission_id)}
            nodes=s.scalars(select(ExecutionGraph).where(ExecutionGraph.mission_id==mission_id).order_by(ExecutionGraph.version.desc(),ExecutionGraph.node_order)).all()
            active_version=max((node.version for node in nodes),default=1)
            active=[node for node in nodes if node.version==active_version]
            computers=s.scalars(select(ComputerMission).where(ComputerMission.mission_id==mission_id)).all()
            refs=self._array(mission.evidence_refs_json)
            all_done=bool(active) and all(node.status=="COMPLETED" for node in active)
            next_iteration=mission.adaptive_iteration+1
            decision,trigger,summary=self.engine.decide(iteration=next_iteration,max_iterations=mission.max_iterations,evidence_count=len(refs),mission_status=mission.status,computer_rows=computers,all_required_completed=all_done)
            mission.adaptive_iteration=next_iteration
            if decision=="REQUEST_EVIDENCE":
                new_refs=self._retrieve(mission.goal or mission.title)
                if new_refs:
                    refs=self._merge_refs(refs,new_refs); mission.evidence_refs_json=json.dumps(refs,ensure_ascii=False)
                    decision,trigger,summary="CONTINUE","EVIDENCE_RECOVERED","已通过现有 RAG 获取可追溯 Evidence；可继续既有受控图。"
                else:
                    decision,trigger,summary="REQUEST_REVIEW","EVIDENCE_STILL_INSUFFICIENT","检索未返回可验证资料，不能继续生成无依据结论。"
            if decision=="REPLAN":
                active_version=self._replan(s,mission,active_version,trigger,summary); mission.status="ADAPTIVE_REPLANNING"; mission.current_step="Adaptive Replanning"
            elif decision=="REQUEST_REVIEW": mission.status="WAITING_ADAPTIVE_REVIEW"; mission.current_step="Adaptive Human Review"
            elif decision=="COMPLETE": mission.status="WAITING_REVIEW"; mission.current_step="Human Review"
            else: mission.status="PLANNING"; mission.current_step="Adaptive Continue"
            s.add(AdaptiveIteration(mission_id=mission_id,iteration=next_iteration,trigger=trigger,previous_state=previous_state,decision=decision,graph_version=active_version,summary=summary))
            s.add(AIMissionEvent(mission_id=mission_id,stage="Adaptive Decision",action=decision,status=decision,evidence_count=len(refs),result_summary=summary))
            s.add(AgentTrace(trace_id=mission_id,mission_id=mission_id,step="Adaptive Decision",message=summary,agent_name="Research Agent",action=decision,status=decision,output_summary=summary,evidence_count=len(refs),iteration=next_iteration,decision=decision,trigger=trigger,graph_version=active_version))
            s.commit()
        finally:s.close()
        evaluation=self.evaluator.evaluate(mission_id)
        return {"mission_id":mission_id,"decision":decision,"trigger":trigger,"summary":summary,"iteration":next_iteration,"max_iterations":max_iterations,"evidence_count":len(refs),"graph_version":active_version,"evaluation":evaluation}
    def iterations(self,mission_id):
        s=self.sessions()
        try:return [{"iteration":x.iteration,"trigger":x.trigger,"previous_state":x.previous_state,"decision":x.decision,"graph_version":x.graph_version,"summary":x.summary,"created_at":x.created_at} for x in s.scalars(select(AdaptiveIteration).where(AdaptiveIteration.mission_id==mission_id).order_by(AdaptiveIteration.iteration)).all()]
        finally:s.close()
    def graph_history(self,mission_id):
        s=self.sessions()
        try:
            rows=s.scalars(select(ExecutionGraph).where(ExecutionGraph.mission_id==mission_id).order_by(ExecutionGraph.version,ExecutionGraph.node_order)).all(); groups={}
            for row in rows: groups.setdefault(row.version,{"version":row.version,"parent_version":row.parent_version,"change_summary":row.change_summary,"nodes":[]})["nodes"].append({"agent_name":row.agent_name,"node_name":row.node_name,"status":row.status,"order":row.node_order})
            return list(groups.values())
        finally:s.close()
    def review(self,mission_id,status):
        if status not in {"APPROVE","REJECT","NEEDS_REVISION"}: raise ValueError("无效的 Adaptive Review 状态。")
        s=self.sessions()
        try:
            mission=s.get(AIMission,mission_id)
            if not mission: raise ValueError("Mission 不存在。")
            if mission.status!="WAITING_ADAPTIVE_REVIEW": raise ValueError("Mission 当前未等待 Adaptive Review。")
            mission.status="PLANNING" if status in {"APPROVE","NEEDS_REVISION"} else "FAILED"; mission.current_step="Adaptive Review Resolved"
            s.add(AIMissionEvent(mission_id=mission_id,stage="Adaptive Review",action=status,status=status,evidence_count=len(self._array(mission.evidence_refs_json)),result_summary="人工已处理有限自适应循环，不会自动写入或批准 Computer Action。")); s.commit()
            return {"mission_id":mission_id,"status":mission.status,"review":status}
        finally:s.close()
    def _replan(self,s,mission,version,trigger,summary):
        current=s.scalars(select(ExecutionGraph).where(ExecutionGraph.mission_id==mission.id,ExecutionGraph.version==version).order_by(ExecutionGraph.node_order)).all(); new_version=version+1
        names=[node.agent_name for node in current]
        if "Literature Agent" not in names: names.insert(1,"Literature Agent")
        for order,name in enumerate(names,1): s.add(ExecutionGraph(mission_id=mission.id,node_name=name.replace(" Agent",""),agent_name=name,status="PENDING",node_order=order,depends_on=json.dumps([] if order==1 else [names[order-2]]),version=new_version,parent_version=version,change_summary=f"Added/retained evidence path after {trigger}: {summary}"))
        return new_version
    def _retrieve(self,goal):
        try:return [{"paper_id":str(x["paper_id"]),"chunk_id":str(x["chunk_id"]),"source":str(x.get("filename") or x.get("paper_title") or "未命名资料"),"section":str(x.get("section") or "正文")} for x in self.retrieval.retrieve(goal,top_k=5)]
        except Exception:return []
    @staticmethod
    def _array(value):
        try:
            parsed=json.loads(value or "[]"); return parsed if isinstance(parsed,list) else []
        except (ValueError,TypeError):return []
    @staticmethod
    def _merge_refs(old,new):
        seen={(row.get("paper_id"),row.get("chunk_id")) for row in old}; return old+[row for row in new if (row.get("paper_id"),row.get("chunk_id")) not in seen]
