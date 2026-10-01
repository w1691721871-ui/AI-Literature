"""P32 structured collaboration protocol without prompts or model reasoning."""
from __future__ import annotations
import json,re
from sqlalchemy import func,select
from app.models.agent_collaboration import AgentConflict,AgentMessage,CollaborationGraph
from app.models.ai_mission import AIMission,AIMissionEvent
from app.models.agent_trace import AgentTrace
from app.services.agent_registry import AgentRegistry
from app.services.database import SessionLocal,initialize_database

class AgentMessageError(ValueError):pass

class AgentContextService:
    def __init__(self,session_factory=SessionLocal):self.sessions=session_factory
    def exchange(self,mission_id:str)->dict:
        s=self.sessions()
        try:
            mission=s.get(AIMission,mission_id)
            if not mission:raise AgentMessageError("Mission 不存在。")
            try:refs=json.loads(mission.evidence_refs_json or "[]")
            except json.JSONDecodeError:refs=[]
            prior=[x.payload_summary for x in s.scalars(select(AgentMessage).where(AgentMessage.mission_id==mission_id,AgentMessage.message_type=="RESULT").order_by(AgentMessage.created_at.desc()).limit(5)).all()]
            return {"mission_summary":{"title":mission.title,"goal":mission.goal,"status":mission.status},"evidence_summary":{"count":len(refs),"sources":[{"paper_id":x.get("paper_id"),"chunk_id":x.get("chunk_id"),"source":x.get("source")} for x in refs]},"previous_results":prior,"boundary":"Only mission metadata and Evidence references are exchanged; prompts, CoT, secrets, and source bodies are excluded."}
        finally:s.close()

class AgentConflictResolver:
    def __init__(self,session_factory=SessionLocal):self.sessions=session_factory
    def create(self,session,mission_id,message_id,participants,summary):
        row=AgentConflict(mission_id=mission_id,source_message_id=message_id,participants=json.dumps(participants),conflict_summary=summary,status="WAITING_HUMAN_REVIEW")
        session.add(row);session.add(AIMissionEvent(mission_id=mission_id,stage="Agent Collaboration",action="Conflict requires human review",status="WAITING_HUMAN_REVIEW",evidence_count=0,result_summary="Agent warning was preserved for human review; the system did not select a result automatically."));return row

class AgentMessageBus:
    MAX_ROUNDS=10
    TYPES={"REQUEST","RESULT","FEEDBACK","WARNING","APPROVAL_REQUEST"}
    forbidden=re.compile(r"(?i)(chain[ -]?of[ -]?thought|system prompt|api[_-]?key\s*[=:]|password\s*[=:]|token\s*[=:]|bearer\s+|secret\s*[=:])")
    def __init__(self,session_factory=SessionLocal,*,initialize=True,registry=None):
        if initialize:initialize_database()
        self.sessions=session_factory;self.registry=registry or AgentRegistry();self.context=AgentContextService(session_factory);self.resolver=AgentConflictResolver(session_factory)
    def send(self,payload:dict)->dict:
        sender=str(payload.get("sender_agent","")).strip();receiver=str(payload.get("receiver_agent","")).strip();kind=str(payload.get("message_type","")).upper();summary=str(payload.get("payload_summary","")).strip();mission_id=str(payload.get("mission_id","")).strip()
        if not mission_id or not sender or not receiver or kind not in self.TYPES:raise AgentMessageError("Mission、发送者、接收者和合法 message_type 均为必填项。")
        if sender not in self.registry._agents or receiver not in self.registry._agents:raise AgentMessageError("发送者或接收者不在 Agent Registry 中。")
        if not summary or len(summary)>600 or self.forbidden.search(summary):raise AgentMessageError("消息只能保存简短、非敏感的用户可理解摘要。")
        if kind=="WARNING" and "CAN_SEND_WARNING" not in self.registry.communication_capabilities(sender):raise AgentMessageError("当前 Agent 无权发送 WARNING。")
        s=self.sessions()
        try:
            if not s.get(AIMission,mission_id):raise AgentMessageError("Mission 不存在。")
            count=int(s.scalar(select(func.count(AgentMessage.id)).where(AgentMessage.mission_id==mission_id)) or 0)
            if count>=self.MAX_ROUNDS:
                self.resolver.create(s,mission_id,None,[sender,receiver],"Collaboration reached the 10-message safety limit; human review is required.");s.commit();raise AgentMessageError("协作已达到 10 轮上限，已转入 WAITING_HUMAN_REVIEW。")
            message=AgentMessage(mission_id=mission_id,sender_agent=sender,receiver_agent=receiver,message_type=kind,payload_summary=summary,status="DELIVERED",collaboration_round=count+1);s.add(message);s.flush()
            edge=s.scalar(select(CollaborationGraph).where(CollaborationGraph.mission_id==mission_id,CollaborationGraph.sender_agent==sender,CollaborationGraph.receiver_agent==receiver))
            if not edge:edge=CollaborationGraph(mission_id=mission_id,sender_agent=sender,receiver_agent=receiver);s.add(edge)
            edge.message_count=(edge.message_count or 0)+1;edge.status="ACTIVE"
            if kind=="WARNING":
                edge.status="WAITING_HUMAN_REVIEW"
                self.resolver.create(s,mission_id,message.id,[sender,receiver],summary)
            s.add(AgentTrace(trace_id=mission_id,mission_id=mission_id,step="Agent Collaboration",message=f"{sender} → {receiver}: {kind}",agent_name=sender,action="SEND_MESSAGE",status="WAITING_HUMAN_REVIEW" if kind=="WARNING" else "COMPLETED",output_summary="Structured collaboration message delivered.",tool_used="Agent Message Bus",iteration=count+1,decision="HUMAN_REVIEW" if kind=="WARNING" else "",trigger=kind))
            s.commit();return self._message(message)
        finally:s.close()
    def messages(self,mission_id):
        s=self.sessions()
        try:return [self._message(x) for x in s.scalars(select(AgentMessage).where(AgentMessage.mission_id==mission_id).order_by(AgentMessage.created_at)).all()]
        finally:s.close()
    def graph(self,mission_id):
        s=self.sessions()
        try:
            edges=[{"from":x.sender_agent,"to":x.receiver_agent,"message_count":x.message_count,"status":x.status} for x in s.scalars(select(CollaborationGraph).where(CollaborationGraph.mission_id==mission_id)).all()]
            participants=sorted({part for edge in edges for part in (edge["from"],edge["to"])})
            return {"mission_id":mission_id,"participants":participants,"edges":edges,"message_count":sum(x["message_count"] for x in edges),"status":"WAITING_HUMAN_REVIEW" if any(x["status"]=="WAITING_HUMAN_REVIEW" for x in edges) else "ACTIVE"}
        finally:s.close()
    def conflicts(self,mission_id):
        s=self.sessions()
        try:return [{"id":x.id,"message_id":x.source_message_id,"participants":self._json(x.participants),"summary":x.conflict_summary,"status":x.status,"created_at":x.created_at} for x in s.scalars(select(AgentConflict).where(AgentConflict.mission_id==mission_id).order_by(AgentConflict.created_at.desc())).all()]
        finally:s.close()
    def analytics(self):
        s=self.sessions()
        try:
            rows=list(s.scalars(select(AgentMessage)).all());total=len(rows);processed=sum(x.status=="PROCESSED" for x in rows);participants=len({agent for x in rows for agent in (x.sender_agent,x.receiver_agent)});conflicts=int(s.scalar(select(func.count(AgentConflict.id))) or 0)
            return {"message_count":total,"average_collaboration_round":round(sum(x.collaboration_round for x in rows)/total,1) if total else 0,"agent_participation":participants,"conflict_count":conflicts,"message_completion_rate":round(processed/total*100,1) if total else 0,"boundary":"Analytics uses persisted summaries only; it never stores prompts, CoT, secrets, or full source text."}
        finally:s.close()
    @staticmethod
    def _message(x):return {"id":x.id,"mission_id":x.mission_id,"sender_agent":x.sender_agent,"receiver_agent":x.receiver_agent,"message_type":x.message_type,"payload_summary":x.payload_summary,"status":x.status,"collaboration_round":x.collaboration_round,"created_at":x.created_at}
    @staticmethod
    def _json(value):
        try:return json.loads(value or "[]")
        except json.JSONDecodeError:return []
