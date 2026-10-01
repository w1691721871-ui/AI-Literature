"""P23 finite, evidence-bounded Mission orchestration."""
from __future__ import annotations
import json
from collections.abc import Callable
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.agent_trace import AgentTrace
from app.models.computer_mission import ComputerMission
from app.models.execution_graph import ExecutionGraph
from app.models.notification import Notification
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.solution_deliverable import SolutionDeliverable
from app.models.solution_project import SolutionProject
from app.models.solution_requirement import SolutionRequirement
from app.models.solution_version import SolutionVersion
from app.models.file_asset import FileAsset
from app.models.mission_file_source import MissionFileSource
from app.services.database import SessionLocal, initialize_database
from app.services.fde_solution_service import FDESolutionService
from app.services.retrieval_service import RetrievalService
from app.services.dynamic_planner_service import DynamicPlannerService
from app.services.agent_memory_service import AgentMemoryService


class AIMissionNotFoundError(ValueError): pass


class AIMissionService:
    """Coordinates existing FDE + RAG services without fabricating Evidence."""
    max_retries = 3
    allowed_statuses = {"CREATED","PLANNING","REQUIREMENT_ANALYSIS","EVIDENCE_RETRIEVAL","SOLUTION_GENERATION","RISK_ANALYSIS","WAITING_REVIEW","NEEDS_REVISION","ADAPTIVE_REPLANNING","WAITING_ADAPTIVE_REVIEW","APPROVED","DELIVERY_READY","COMPLETED","FAILED"}

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal, *, initialize: bool = True, fde_service=None, retrieval_service=None, planner_service=None, memory_service=None):
        if initialize: initialize_database()
        self._sessions = session_factory
        self._fde = fde_service or FDESolutionService(session_factory, initialize=False)
        self._retrieval = retrieval_service or RetrievalService(session_factory=session_factory)
        self._memory = memory_service or AgentMemoryService(session_factory, initialize=False)
        self._planner = planner_service or DynamicPlannerService(session_factory, initialize=False, memories=self._memory)

    def create(self, payload: dict[str, str]) -> dict[str, object]:
        session = self._sessions()
        try:
            row=AIMission(title=payload["title"].strip(), mission_type=payload.get("mission_type","RESEARCH").strip(), goal=payload.get("goal","").strip())
            session.add(row); session.flush()
            self._event(session,row,"Mission","Mission Created","CREATED",0,"任务已创建，尚未执行检索或生成科研结论。")
            row.status,row.progress,row.current_step="PLANNING",5,"Requirement Analysis"
            self._event(session,row,"Planning","Mission Planning Ready","PLANNING",0,"尚未发起检索；等待用户启动受控执行。")
            session.add(Notification(notification_type="MISSION_CREATED",message=f"AI Mission 已创建：{row.title}")); session.commit(); session.refresh(row)
            self._planner.analyze(row.goal or row.title, row.mission_type, row.id)
            return self._mission(row)
        finally: session.close()

    def run(self, mission_id: str) -> dict[str, object]:
        mission=self._mission_row(mission_id)
        if mission["status"] not in {"CREATED","PLANNING","NEEDS_REVISION"}: raise ValueError("当前 Mission 不处于可执行或可修订状态。")
        try:
            self._graph_status(mission_id,"Research Agent","RUNNING")
            project_id=self._ensure_project(mission)
            self._transition(mission_id,"REQUIREMENT_ANALYSIS",20,"Requirement Analysis","Requirement Analysis Started","RUNNING",0,"开始生成六类待确认需求。")
            analyzed=self._fde.analyze(project_id)
            self._transition(mission_id,"EVIDENCE_RETRIEVAL",38,"Evidence Retrieval","Requirements Generated","COMPLETED",0,f"已生成 {len(analyzed['requirements'])} 类待确认需求。")
            self._transition(mission_id,"EVIDENCE_RETRIEVAL",45,"Evidence Retrieval","Evidence Retrieval Started","RUNNING",0,"调用现有 RAG 检索服务。")
            self._graph_status(mission_id,"Literature Agent","RUNNING")
            evidence=self._retrieve(mission["goal"] or mission["title"],mission_id); self._save_evidence(mission_id,evidence); self._graph_status(mission_id,"Literature Agent","COMPLETED")
            self._transition(mission_id,"SOLUTION_GENERATION",62,"Solution Generation","Evidence Retrieved" if evidence else "No Evidence Found","COMPLETED" if evidence else "WAITING",len(evidence),"只保存 RAG 返回的 paper_id / chunk_id / source。" if evidence else "当前未找到可用 Evidence；方案将明确标记 NEEDS_CONFIRMATION。")
            if self._selected(mission_id,"Innovation Agent"):
                self._graph_status(mission_id,"Innovation Agent","RUNNING")
                self._fde.blueprint(project_id,evidence_refs=evidence,version_summary="Generated Solution Blueprint from Mission Evidence"); self._graph_status(mission_id,"Innovation Agent","COMPLETED")
                self._transition(mission_id,"RISK_ANALYSIS",76,"Risk Analysis","Blueprint Generated","COMPLETED",len(evidence),"Solution Blueprint 已生成，未支持内容保持 NEEDS_CONFIRMATION。")
            else:
                self._transition(mission_id,"RISK_ANALYSIS",70,"Risk Analysis","Solution Draft Skipped","SKIPPED",len(evidence),"Planner 未选择方案草稿阶段；保留 Evidence 与人工审核边界。")
            if self._selected(mission_id,"Risk Agent"):
                self._graph_status(mission_id,"Risk Agent","RUNNING"); risks=self._fde.risks(project_id); self._graph_status(mission_id,"Risk Agent","COMPLETED")
            else:
                risks={"risks":[]}
                self._transition(mission_id,"WAITING_REVIEW",80,"Human Review","Risk Review Skipped","SKIPPED",len(evidence),"Planner 未选择风险专项检查；负责人仍需审核 Evidence 与任务范围。")
            self._transition(mission_id,"WAITING_REVIEW",85,"Human Review","Risk Analysis Completed","COMPLETED",len(evidence),f"已生成 {len(risks['risks'])} 项风险草稿，等待人工审核。")
            self._transition(mission_id,"WAITING_REVIEW",85,"Human Review","Waiting Human Review","WAITING_REVIEW",len(evidence),"AI 不会自动批准方案或交付包。")
            self._notify("REVIEW_REQUIRED",f"Mission 等待人工审核：{mission['title']}"); return self.detail(mission_id)
        except Exception as error:
            self._fail(mission_id); raise error

    def review(self, mission_id: str, status: str, comment: str) -> dict[str, object]:
        mission=self._mission_row(mission_id)
        if mission["status"] not in {"WAITING_REVIEW","NEEDS_REVISION"}: raise ValueError("当前 Mission 尚未进入人工审核阶段。")
        review=self._fde.review(str(mission["solution_project_id"]),status,comment)
        if status=="NEEDS_REVISION": self._transition(mission_id,"NEEDS_REVISION",72,"Human Review","Reviewer Requested Revision","NEEDS_REVISION",len(mission["evidence_refs"]),comment or "需要调整方案后再次审核。",comment)
        elif status=="APPROVED":
            self._transition(mission_id,"APPROVED",92,"Human Review","Mission Approved","APPROVED",len(mission["evidence_refs"]),comment or "Reviewer 已批准方案。",comment)
            self._memory.confirmed(mission_id, f"已人工确认 Mission “{mission['title']}” 的规划与审核状态；后续相似任务仍需重新检索 Evidence 并再次人工审核。")
            self._notify("MISSION_APPROVED",f"Mission 已获人工审核批准：{mission['title']}")
        else: self._transition(mission_id,"FAILED",100,"Human Review","Mission Rejected","REJECTED",len(mission["evidence_refs"]),comment or "Reviewer 已拒绝当前方案。",comment)
        return {"mission":self.detail(mission_id),"review":review}

    def revise(self, mission_id: str, change_summary: str) -> dict[str, object]:
        mission=self._mission_row(mission_id)
        if mission["status"]!="NEEDS_REVISION": raise ValueError("只有 NEEDS_REVISION 状态的 Mission 可以创建新版本。")
        self._transition(mission_id,"SOLUTION_GENERATION",76,"Solution Generation","Blueprint Revised","RUNNING",len(mission["evidence_refs"]),change_summary)
        self._fde.blueprint(str(mission["solution_project_id"]),evidence_refs=mission["evidence_refs"],version_summary=f"Reviewer Revision: {change_summary}")
        self._transition(mission_id,"WAITING_REVIEW",85,"Human Review","Waiting Human Review","WAITING_REVIEW",len(mission["evidence_refs"]),"已创建新版本，等待新的人工审核。"); return self.detail(mission_id)

    def delivery(self, mission_id: str) -> dict[str, object]:
        mission=self._mission_row(mission_id)
        if mission["status"]!="APPROVED": raise ValueError("Mission 尚未通过人工审核，不能生成 Delivery Package。")
        package=self._fde.delivery_package(str(mission["solution_project_id"])); package["evidence_references"]=mission["evidence_refs"]
        self._graph_status(mission_id,"Delivery Agent","COMPLETED")
        self._transition(mission_id,"DELIVERY_READY",97,"Delivery","Delivery Package Generated","COMPLETED",len(mission["evidence_refs"]),"交付包保留 AI Generated Draft 与 Evidence References 标记。")
        self._transition(mission_id,"COMPLETED",100,"Delivery","Mission Completed","COMPLETED",len(mission["evidence_refs"]),"Mission 交付流程完成。"); self._notify("MISSION_COMPLETED",f"Mission 已完成：{mission['title']}")
        return {"mission":self.detail(mission_id),"delivery_package":package}

    def list(self):
        s=self._sessions()
        try:return [self._mission(x) for x in s.scalars(select(AIMission).order_by(AIMission.updated_at.desc())).all()]
        finally:s.close()
    def detail(self,mission_id):
        s=self._sessions()
        try:
            m=self._require(s,mission_id); reqs,dels=self._solution_records(s,m.solution_project_id)
            versions = [] if not m.solution_project_id else [{"id": x.id, "version": x.version, "status": x.status, "change_summary": x.change_summary, "created_by": x.created_by, "created_at": x.created_at} for x in s.scalars(select(SolutionVersion).where(SolutionVersion.solution_project_id == m.solution_project_id).order_by(SolutionVersion.version.asc())).all()]
            computer_missions = [{"id": x.id, "task": x.task or x.mission_name, "status": x.status,
                                  "approval_status": x.approval_status, "execution_allowed": x.execution_allowed,
                                  "progress": x.progress, "risk_level": x.risk_level,
                                  "action_plan": self._object(x.action_plan_json, {}),
                                  "workspace": self._object(x.workspace_profile_json, {}),
                                  "diff_content": x.diff_content,
                                  "execution_log": self._object(x.execution_log_json, []),
                                  "verification": self._object(x.verification_json, {}),
                                  "retry_count": x.retry_count} for x in s.scalars(select(ComputerMission).where(ComputerMission.mission_id == m.id).order_by(ComputerMission.created_at.asc())).all()]
            plan_nodes=[{"id":x.id,"node_name":x.node_name,"agent_name":x.agent_name,"status":x.status,"order":x.node_order,"depends_on":self._decode(x.depends_on),"created_at":x.created_at} for x in s.scalars(select(ExecutionGraph).where(ExecutionGraph.mission_id==m.id).order_by(ExecutionGraph.node_order)).all()]
            sources=self._source_materials(s,m.id)
            return {**self._mission(m),"timeline":self._timeline(s,m.id),"team":self._team(m, computer_missions),"requirements":reqs,"deliverables":dels,"versions":versions,"computer_missions":computer_missions,"execution_graph":plan_nodes,"evidence_graph":self._graph(m,reqs,dels),"source_materials":sources}
        finally:s.close()
    def timeline(self,mission_id):
        s=self._sessions()
        try:self._require(s,mission_id);return self._timeline(s,mission_id)
        finally:s.close()
    def notifications(self):
        s=self._sessions()
        try:return [{"id":x.id,"type":x.notification_type,"message":x.message,"read":x.read,"created_at":x.created_at} for x in s.scalars(select(Notification).order_by(Notification.created_at.desc()).limit(30)).all()]
        finally:s.close()
    def mark_notification_read(self,notification_id):
        s=self._sessions()
        try:
            x=s.get(Notification,notification_id)
            if not x:raise AIMissionNotFoundError("Notification 不存在。")
            x.read=True;s.commit();return {"id":x.id,"read":True}
        finally:s.close()
    def dashboard(self):
        s=self._sessions()
        try:
            missions=[self._mission(x) for x in s.scalars(select(AIMission).order_by(AIMission.updated_at.desc())).all()]
            active={"PLANNING","REQUIREMENT_ANALYSIS","EVIDENCE_RETRIEVAL","SOLUTION_GENERATION","RISK_ANALYSIS","WAITING_REVIEW","NEEDS_REVISION"}
            metrics={"projects":int(s.scalar(select(func.count(SolutionProject.id)))or 0),"active_missions":sum(x["status"] in active for x in missions),"pending_reviews":int(s.scalar(select(func.count(SolutionProject.id)).where(SolutionProject.review_status.in_(("PENDING","NEEDS_REVISION"))))or 0),"completed_missions":sum(x["status"]=="COMPLETED" for x in missions),"knowledge_size":int(s.scalar(select(func.count(Paper.paper_id)))or 0),"evidence_count":int(s.scalar(select(func.count(PaperChunk.id)))or 0),"deliverables":int(s.scalar(select(func.count(SolutionDeliverable.id)))or 0)}
            return {"metrics":metrics,"recent_missions":missions[:6],"team_status":self._team(None),"latest_deliverables":metrics["deliverables"],"boundary":"Dashboard 只聚合数据库中的真实任务、资料、Evidence 引用与交付记录。"}
        finally:s.close()

    def _ensure_project(self,m):
        if m["solution_project_id"]:return str(m["solution_project_id"])
        p=self._fde.create({"title":str(m["title"]),"customer_need":str(m["goal"]or m["title"]),"industry":"Enterprise AI Workspace","objective":"待人工确认的解决方案目标"})
        s=self._sessions()
        try:self._require(s,str(m["id"])).solution_project_id=str(p["id"]);s.commit()
        finally:s.close()
        return str(p["id"])
    def _retrieve(self,question,mission_id):
        for attempt in range(1,self.max_retries+1):
            try:
                rows=self._retrieval.retrieve(question,top_k=5)
                return [{"paper_id":str(x["paper_id"]),"chunk_id":str(x["chunk_id"]),"source":str(x.get("filename")or x.get("paper_title")or"未命名资料"),"section":str(x.get("section")or"正文")} for x in rows]
            except Exception:
                self._retry(mission_id,attempt)
        raise RuntimeError("Evidence Retrieval 未能在有限重试内完成，请检查模型或索引配置。")
    def _retry(self,mission_id,attempt):
        s=self._sessions()
        try:
            m=self._require(s,mission_id);m.retry_count=attempt;self._event(s,m,"Evidence Retrieval","Evidence Retrieval Retry","RETRYING",0,f"第 {attempt}/{self.max_retries} 次受控重试。");s.commit()
        finally:s.close()
    def _save_evidence(self,mission_id,refs):
        s=self._sessions()
        try:self._require(s,mission_id).evidence_refs_json=json.dumps(refs,ensure_ascii=False);s.commit()
        finally:s.close()
    def _graph_status(self,mission_id,agent_name,status):
        s=self._sessions()
        try:
            row=s.scalar(select(ExecutionGraph).where(ExecutionGraph.mission_id==mission_id,ExecutionGraph.agent_name==agent_name))
            if row: row.status=status
            s.commit()
        finally:s.close()
    def _selected(self,mission_id,agent_name):
        s=self._sessions()
        try:return s.scalar(select(ExecutionGraph).where(ExecutionGraph.mission_id==mission_id,ExecutionGraph.agent_name==agent_name)) is not None
        finally:s.close()
    def _transition(self,mid,status,progress,step,action,event_status,count,result,comment=None):
        s=self._sessions()
        try:
            m=self._require(s,mid);m.status,m.progress,m.current_step=status,progress,step
            if comment is not None:m.review_comment=comment
            self._event(s,m,step,action,event_status,count,result);s.commit()
        finally:s.close()
    def _fail(self,mid):
        try:self._transition(mid,"FAILED",100,"Execution","Step Failed","FAILED",0,"当前步骤执行失败，请检查配置或重试。");self._notify("MISSION_FAILED",f"Mission 执行失败：{mid}")
        except Exception:pass
    def _notify(self,kind,msg):
        s=self._sessions()
        try:s.add(Notification(notification_type=kind,message=msg));s.commit()
        finally:s.close()
    @staticmethod
    def _event(s,m,stage,action,status,count,result):
        s.add(AIMissionEvent(mission_id=m.id,stage=stage,action=action,status=status,evidence_count=count,result_summary=result))
        agent = "Computer Agent" if stage == "Computer Agent" else ("Literature Agent" if stage == "Evidence Retrieval" else ("Risk Agent" if stage == "Risk Analysis" else ("Delivery Agent" if stage == "Delivery" else "Research Agent")))
        tool = "FAISS Retrieval" if stage == "Evidence Retrieval" else ("Verification Sandbox" if stage == "Computer Agent" else "")
        s.add(AgentTrace(trace_id=m.id, mission_id=m.id, step=stage, message=result, agent_name=agent, action=action, status=status, output_summary=result, tool_used=tool, evidence_count=count))
    @staticmethod
    def _require(s,mid):
        x=s.get(AIMission,mid)
        if not x:raise AIMissionNotFoundError("AI Mission 不存在。")
        return x
    def _mission_row(self,mid):
        s=self._sessions()
        try:return self._mission(self._require(s,mid))
        finally:s.close()
    @staticmethod
    def _decode(value):
        try:return json.loads(value or "[]") if isinstance(json.loads(value or "[]"),list) else []
        except (json.JSONDecodeError,TypeError):return []
    @staticmethod
    def _object(value, default):
        try:
            decoded=json.loads(value or "")
            return decoded if isinstance(decoded, type(default)) else default
        except (json.JSONDecodeError,TypeError):return default
    def _mission(self,x):return {"id":x.id,"title":x.title,"type":x.mission_type,"goal":x.goal,"solution_project_id":x.solution_project_id,"status":x.status,"progress":x.progress,"current_step":x.current_step,"evidence_refs":self._decode(x.evidence_refs_json),"review_comment":x.review_comment,"retry_count":x.retry_count,"created_at":x.created_at,"updated_at":x.updated_at}
    @staticmethod
    def _timeline(s,mid):return [{"id":x.id,"stage":x.stage,"action":x.action,"status":x.status,"evidence_count":x.evidence_count,"result":x.result_summary,"created_at":x.created_at} for x in s.scalars(select(AIMissionEvent).where(AIMissionEvent.mission_id==mid).order_by(AIMissionEvent.created_at.asc())).all()]
    @staticmethod
    def _source_materials(s, mission_id):
        """P29 is optional for legacy isolated test databases created before its tables."""
        try:
            return [{"file_id":x.file_id,"filename":asset.filename,"file_type":asset.file_type,"status":asset.status,"classification":"CUSTOMER_PROVIDED_DOCUMENT"} for x in s.scalars(select(MissionFileSource).where(MissionFileSource.mission_id==mission_id)).all() if (asset:=s.get(FileAsset,x.file_id))]
        except OperationalError:
            return []
    @staticmethod
    def _solution_records(s,pid):
        if not pid:return [],[]
        reqs=[{"id":x.id,"type":x.requirement_type,"content":x.description,"status":x.status} for x in s.scalars(select(SolutionRequirement).where(SolutionRequirement.solution_project_id==pid)).all()]
        dels=[{"id":x.id,"type":x.deliverable_type,"title":x.title,"status":x.status} for x in s.scalars(select(SolutionDeliverable).where(SolutionDeliverable.solution_project_id==pid)).all()]
        return reqs,dels
    @staticmethod
    def _team(m, computer_missions=None):
        state=m.status if m else "READY";has_evidence=bool(m and m.evidence_refs_json!="[]")
        computer_status = str((computer_missions or [{}])[-1].get("status", "IDLE"))
        return [{"name":"Research Agent","role":"任务规划","status":"RUNNING" if state in {"PLANNING","REQUIREMENT_ANALYSIS"} else ("COMPLETED" if state not in {"READY","CREATED"} else "READY"),"last_action":m.current_step if m else "等待任务"},{"name":"Literature Agent","role":"真实知识检索","status":"RUNNING" if state=="EVIDENCE_RETRIEVAL" else ("COMPLETED" if has_evidence else "WAITING"),"last_action":"仅在真实 RAG 检索时运行"},{"name":"Innovation Agent","role":"方案草稿","status":"RUNNING" if state=="SOLUTION_GENERATION" else ("COMPLETED" if state in {"RISK_ANALYSIS","WAITING_REVIEW","NEEDS_REVISION","APPROVED","DELIVERY_READY","COMPLETED"} else "WAITING"),"last_action":"依赖真实 Evidence"},{"name":"Risk Agent","role":"风险检查","status":"RUNNING" if state=="RISK_ANALYSIS" else ("COMPLETED" if state in {"WAITING_REVIEW","NEEDS_REVISION","APPROVED","DELIVERY_READY","COMPLETED"} else "WAITING"),"last_action":"风险项需人工确认"},{"name":"Computer Agent","role":"受控 Workspace 执行","status":computer_status,"last_action":"仅在 Diff 审核后执行"},{"name":"Delivery Agent","role":"交付生成","status":"RUNNING" if state=="DELIVERY_READY" else ("COMPLETED" if state=="COMPLETED" else "WAITING"),"last_action":"仅批准后生成交付包"}]
    @staticmethod
    def _graph(m,reqs,dels):
        nodes=[{"id":"mission","type":"customer_need","label":m.goal or m.title}];edges=[]
        for x in reqs:nodes.append({"id":f"requirement:{x['id']}","type":"requirement","label":x["type"]});edges.append({"from":"mission","to":f"requirement:{x['id']}","relation":"defines"})
        refs=AIMissionService._decode(m.evidence_refs_json)
        if not refs:nodes.append({"id":"evidence:pending","type":"evidence","label":"尚未关联 Evidence"})
        for x in refs:
            evidence_id=f"evidence:{x.get('chunk_id','')}"
            nodes.append({"id":evidence_id,"type":"evidence","label":x.get("source","未命名资料"),"paper_id":x.get("paper_id"),"chunk_id":x.get("chunk_id")})
            edges.append({"from":"mission","to":evidence_id,"relation":"grounds"})
        # The decision node mirrors the persisted Mission review state; it is
        # deliberately provisional until a human has reviewed the solution.
        nodes.append({"id":"decision:mission-review","type":"decision","label":f"Mission Review · {m.status}"})
        for x in refs: edges.append({"from":f"evidence:{x.get('chunk_id','')}","to":"decision:mission-review","relation":"informs"})
        blueprint = next((x for x in dels if x["type"] == "SOLUTION_BLUEPRINT"), None)
        if blueprint:
            blueprint_id=f"blueprint:{blueprint['id']}"
            nodes.append({"id":blueprint_id,"type":"blueprint","label":blueprint["title"]})
            edges.append({"from":"decision:mission-review","to":blueprint_id,"relation":"shapes"})
        for x in dels:
            node_id=f"deliverable:{x['id']}"
            nodes.append({"id":node_id,"type":"deliverable","label":x["title"]})
            edges.append({"from": blueprint_id if blueprint else "decision:mission-review", "to":node_id,"relation":"delivers"})
        return {"nodes":nodes,"edges":edges,"boundary":"节点只来自 Mission、已保存 Requirement、真实 RAG Evidence 引用与持久化 Deliverable；没有 Evidence 时明确显示未关联。"}
