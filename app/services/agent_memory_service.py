"""Small, review-gated memory store. It never stores source documents or prompts."""
from sqlalchemy import select
from app.models.agent_memory import AgentMemory
from app.services.database import SessionLocal, initialize_database

class AgentMemoryService:
    def __init__(self, session_factory=SessionLocal, *, initialize=True):
        if initialize: initialize_database()
        self.sessions=session_factory
    def list(self):
        s=self.sessions()
        try:return [self._item(row) for row in s.scalars(select(AgentMemory).order_by(AgentMemory.created_at.desc())).all()]
        finally:s.close()
    def retrieve(self, goal, limit=3):
        terms={word.lower() for word in (goal or "").split() if len(word)>2}
        return [item for item in self.list() if item["status"]=="CONFIRMED" and (not terms or any(term in item["content_summary"].lower() for term in terms))][:limit]
    def candidate(self, mission_id, summary, agent_name="Planner Agent"):
        safe=(summary or "").strip()[:500]
        if not safe: return None
        s=self.sessions()
        try:
            row=AgentMemory(memory_type="MISSION_MEMORY",agent_name=agent_name,content_summary=safe,source_mission_id=mission_id,importance=1,status="PENDING_REVIEW")
            s.add(row);s.commit();s.refresh(row);return self._item(row)
        finally:s.close()
    def confirmed(self, mission_id, summary, agent_name="Planner Agent"):
        """Persist only an approved, compact learning summary after Human Review."""
        item=self.candidate(mission_id,summary,agent_name)
        if not item: return None
        s=self.sessions()
        try:
            row=s.get(AgentMemory,item["id"]); row.status="CONFIRMED"; s.commit(); s.refresh(row); return self._item(row)
        finally:s.close()
    def delete(self,memory_id):
        s=self.sessions()
        try:
            row=s.get(AgentMemory,memory_id)
            if not row: raise ValueError("Memory 不存在。")
            s.delete(row);s.commit();return {"deleted":True,"id":memory_id}
        finally:s.close()
    @staticmethod
    def _item(row): return {"id":row.id,"memory_type":row.memory_type,"agent_name":row.agent_name,"content_summary":row.content_summary,"source_mission_id":row.source_mission_id,"importance":row.importance,"status":row.status,"created_at":row.created_at}
