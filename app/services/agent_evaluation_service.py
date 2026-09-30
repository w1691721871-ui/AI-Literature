"""P25 observability over persisted Mission metadata, without inspecting prompts or CoT."""
from __future__ import annotations
import json
from collections import defaultdict
from sqlalchemy import select
from app.models.agent_evaluation import AgentEvaluation
from app.models.agent_metric import AgentMetric
from app.models.agent_trace import AgentTrace
from app.models.ai_mission import AIMission
from app.models.computer_mission import ComputerMission
from app.models.execution_graph import ExecutionGraph
from app.services.database import SessionLocal, initialize_database

class AgentEvaluationService:
    def __init__(self, session_factory=SessionLocal, *, initialize=True):
        if initialize: initialize_database()
        self.sessions=session_factory

    def evaluate(self, mission_id: str) -> dict[str, object]:
        s=self.sessions()
        try:
            mission=s.get(AIMission, mission_id)
            if not mission: raise ValueError("Mission 不存在。")
            refs=self._json(mission.evidence_refs_json, [])
            computers=s.scalars(select(ComputerMission).where(ComputerMission.mission_id==mission_id)).all()
            revisions=int(mission.retry_count or 0)+sum(int(row.retry_count or 0) for row in computers)
            verification="NOT_APPLICABLE" if not computers else ("PASS" if all(self._json(row.verification_json, {}).get("status")=="PASS" for row in computers if row.status=="COMPLETED") and any(row.status=="COMPLETED" for row in computers) else "PENDING")
            failure_type,failure_reason=self._failure(mission, computers)
            completed=mission.status in {"COMPLETED","DELIVERY_READY","APPROVED"}
            safety="PASS" if not any(row.status in {"SECURITY_BLOCK","UNSAFE"} for row in computers) else "BLOCKED"
            score=(30 if completed else 0)+(20 if refs else 0)+(20 if completed and revisions<=1 else 0)+(20 if verification in {"PASS","NOT_APPLICABLE"} else 0)+(10 if safety=="PASS" else 0)
            nodes=s.scalars(select(ExecutionGraph).where(ExecutionGraph.mission_id==mission_id)).all()
            is_implementation=any(word in (mission.goal or "").lower() for word in ("code","api","ui","bug","python","前端","代码","接口","修复","实现"))
            selected={node.agent_name for node in nodes}
            planner_score=(40 if completed else 0)+(30 if nodes else 0)+(20 if ("Computer Agent" in selected)==is_implementation else 0)+(10 if safety=="PASS" else 0)
            report={"mission_id":mission_id,"evaluation_score":score,"planner_score":planner_score,"task_completion":"COMPLETED" if completed else mission.status,"evidence_coverage":len(refs),"human_revision_count":revisions,"verification_result":verification,"execution_safety":safety,"failure_type":failure_type,"failure_reason":failure_reason,"boundary":"评分只根据已保存的任务状态、Execution Graph、Evidence 引用、人工修订和受控验证元数据计算；不读取 Prompt、CoT、密钥或隐私文件。"}
            row=s.scalar(select(AgentEvaluation).where(AgentEvaluation.mission_id==mission_id))
            if row is None: row=AgentEvaluation(mission_id=mission_id); s.add(row)
            for key in ("evaluation_score","planner_score","task_completion","evidence_coverage","human_revision_count","verification_result","execution_safety","failure_type","failure_reason"):
                setattr(row,key,report[key])
            row.report_json=json.dumps(report,ensure_ascii=False); s.commit(); return report
        finally:s.close()

    def get(self, mission_id):
        s=self.sessions()
        try:
            row=s.scalar(select(AgentEvaluation).where(AgentEvaluation.mission_id==mission_id))
            return self._json(row.report_json,{}) if row else self.evaluate(mission_id)
        finally:s.close()

    def evaluations(self):
        """Return persisted evaluation reports without creating new mission results."""
        s=self.sessions()
        try:
            rows=s.scalars(select(AgentEvaluation).order_by(AgentEvaluation.created_at.desc())).all()
            return [self._json(row.report_json,{}) for row in rows]
        finally:s.close()

    def traces(self, mission_id):
        s=self.sessions()
        try:return [{"agent_name":x.agent_name,"action":x.action or x.step,"status":x.status,"duration":x.duration,"input_summary":x.input_summary,"output_summary":x.output_summary or x.message,"tool_used":x.tool_used,"evidence_count":x.evidence_count,"created_at":x.created_at} for x in s.scalars(select(AgentTrace).where(AgentTrace.mission_id==mission_id).order_by(AgentTrace.created_at)).all()]
        finally:s.close()

    def metrics(self):
        s=self.sessions()
        try:
            groups=defaultdict(list)
            for trace in s.scalars(select(AgentTrace)).all(): groups[trace.agent_name].append(trace)
            result=[]
            for name,rows in groups.items():
                successful=sum(row.status in {"COMPLETED","PASS","APPROVED","WAITING_REVIEW"} for row in rows)
                failed=sum(row.status in {"FAILED","FAIL","BLOCKED","REJECTED"} for row in rows)
                total=len(rows); duration=sum(row.duration or 0 for row in rows)/total; evidence=sum(row.evidence_count for row in rows)/total
                item={"agent_name":name,"total_tasks":total,"success_count":successful,"failed_count":failed,"success_rate":round(successful/total*100,1) if total else 0,"avg_duration":round(duration,2),"avg_evidence_count":round(evidence,2)}
                snapshot=s.scalar(select(AgentMetric).where(AgentMetric.agent_name==name).order_by(AgentMetric.created_at.desc()))
                if snapshot is None: snapshot=AgentMetric(agent_name=name); s.add(snapshot)
                snapshot.total_tasks,snapshot.success_count,snapshot.failed_count=item["total_tasks"],item["success_count"],item["failed_count"]
                snapshot.avg_duration,snapshot.avg_evidence_count=item["avg_duration"],item["avg_evidence_count"]
                result.append(item)
            s.commit()
            return sorted(result,key=lambda item:item["agent_name"])
        finally:s.close()

    @staticmethod
    def _failure(mission, computers):
        if any(row.status in {"SECURITY_BLOCK","UNSAFE"} for row in computers): return ("SECURITY_BLOCK","受控安全策略阻止了该执行；未写入文件或调用危险工具。")
        if mission.status=="FAILED": return ("RETRIEVAL_FAILURE","Mission 在受控执行中失败；请查看用户可理解的 Mission Timeline。")
        if mission.status=="NEEDS_REVISION": return ("HUMAN_REJECT","人工审核要求修订后再继续。")
        if any(row.status=="NEEDS_REVISION" for row in computers): return ("VALIDATION_FAILURE","受控文件验证未通过，等待人工修订。")
        if any(row.status=="FAILED" and row.approval_status=="REJECTED" for row in computers): return ("HUMAN_REJECT","人工拒绝了 Computer Diff；未写入文件。")
        return ("","")

    @staticmethod
    def _json(value,default):
        try:
            parsed=json.loads(value or "")
            return parsed if isinstance(parsed,type(default)) else default
        except (TypeError,json.JSONDecodeError): return default
