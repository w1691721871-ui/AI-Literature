"""P28 Copilot session coordinator that delegates to the existing Mission service."""
from __future__ import annotations
import re
from sqlalchemy import func, select
from app.agent.copilot_agent import CopilotAgent
from app.models.copilot_message import CopilotMessage
from app.models.copilot_session import CopilotSession
from app.services.ai_mission_service import AIMissionService
from app.services.agent_memory_service import AgentMemoryService
from app.services.database import SessionLocal, initialize_database

class CopilotMissionService:
    def __init__(self,session_factory=SessionLocal,*,initialize=True,missions=None,memory=None,agent=None):
        if initialize: initialize_database()
        self.sessions=session_factory;self.missions=missions or AIMissionService(session_factory,initialize=False);self.memory=memory or AgentMemoryService(session_factory,initialize=False);self.agent=agent or CopilotAgent()
    def create_session(self,user_id="local-user"):
        s=self.sessions()
        try:
            row=CopilotSession(user_id=(user_id or "local-user")[:100]);s.add(row);s.commit();s.refresh(row);return self._session(s,row)
        finally:s.close()
    def chat(self,session_id,text):
        clean=self._summary(text)
        if not clean: raise ValueError("请输入需要完成的任务。")
        s=self.sessions()
        try:
            session=s.get(CopilotSession,session_id)
            if not session: raise ValueError("Copilot Session 不存在。")
            understanding=self.agent.understand(clean); memory=self.memory.retrieve(clean)
            s.add(CopilotMessage(session_id=session_id,role="USER",content_summary=clean,intent=understanding["intent"]))
            s.add(CopilotMessage(session_id=session_id,role="ASSISTANT",content_summary=understanding["summary"],intent=understanding["intent"]))
            session.conversation_summary=f"当前目标：{understanding['goal']}。意图：{understanding['intent']}。";s.commit()
            return {**understanding,"session_id":session_id,"memory_suggestions":[{"id":x["id"],"summary":x["content_summary"]} for x in memory],"boundary":"会话仅保存摘要化意图与结果，不保存完整 Prompt、CoT、密钥或敏感输入。"}
        finally:s.close()
    def start(self,session_id):
        s=self.sessions();
        try:
            session=s.get(CopilotSession,session_id)
            if not session: raise ValueError("Copilot Session 不存在。")
            latest=s.scalar(select(CopilotMessage).where(CopilotMessage.session_id==session_id, CopilotMessage.role=="USER").order_by(CopilotMessage.created_at.desc()))
            if not latest: raise ValueError("请先发送任务需求。")
            intent=latest.intent or "RESEARCH"; mission=self.missions.create({"title":f"Copilot · {latest.content_summary[:80]}","mission_type":self.agent.classifier.mission_type(intent),"goal":latest.content_summary})
            session.current_mission_id=mission["id"];s.add(CopilotMessage(session_id=session_id,role="SYSTEM",content_summary="Mission 已创建并已生成 Planner Execution Graph，等待用户启动受控执行。",intent=intent));s.commit()
            return {"session_id":session_id,"mission":mission,"intent":intent,"activity":["Intent understood","Mission created","Planner graph generated","Waiting for controlled start"]}
        finally:s.close()
    def get(self,session_id):
        s=self.sessions()
        try:
            row=s.get(CopilotSession,session_id)
            if not row: raise ValueError("Copilot Session 不存在。")
            return self._session(s,row)
        finally:s.close()
    def activity(self,session_id):
        session=self.get(session_id); activity=[]
        if session["current_mission_id"]:
            try:
                detail=self.missions.detail(session["current_mission_id"])
                activity=[{"agent":x["name"],"status":x["status"],"summary":x["last_action"]} for x in detail["team"]]
            except ValueError: pass
        return {"session_id":session_id,"activity":activity}
    def analytics(self):
        s=self.sessions()
        try:
            sessions=s.scalars(select(CopilotSession)).all();messages=s.scalars(select(CopilotMessage)).all(); intents={}
            for msg in messages:
                if msg.role=="USER":intents[msg.intent]=intents.get(msg.intent,0)+1
            return {"sessions":len(sessions),"created_missions":sum(row.current_mission_id is not None for row in sessions),"intent_distribution":intents,"completion_rate":round(sum(row.status=="COMPLETED" for row in sessions)/len(sessions)*100,1) if sessions else 0,"average_session_time":"not measured","boundary":"只统计摘要化 Copilot Session，不读取用户原始输入或私密内容。"}
        finally:s.close()
    def _session(self,s,row):
        messages=s.scalars(select(CopilotMessage).where(CopilotMessage.session_id==row.id).order_by(CopilotMessage.created_at)).all()
        return {"id":row.id,"user_id":row.user_id,"conversation_summary":row.conversation_summary,"current_mission_id":row.current_mission_id,"status":row.status,"created_at":row.created_at,"messages":[{"role":x.role,"content_summary":x.content_summary,"intent":x.intent,"created_at":x.created_at} for x in messages]}
    @staticmethod
    def _summary(text):
        value=" ".join((text or "").strip().split())[:500]
        value=re.sub(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+",r"\1=[REDACTED]",value)
        return value
