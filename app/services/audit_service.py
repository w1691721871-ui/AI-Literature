"""Workspace-isolated audit events with deliberately bounded summaries."""
from sqlalchemy import select
from app.models.audit import AuditEvent
from app.services.database import SessionLocal, initialize_database

class AuditService:
    def __init__(self,sessions=SessionLocal,*,initialize=True):
        if initialize: initialize_database()
        self.s=sessions
    def record_event(self,workspace_id,user_id,action_type,resource_type,resource_id,mission_id=None,summary="",result="SUCCESS"):
        event=AuditEvent(workspace_id=workspace_id,user_id=user_id,action_type=action_type,resource_type=resource_type,resource_id=resource_id,mission_id=mission_id,summary=(summary or "")[:500],result=result)
        session=self.s()
        try:
            session.add(event);session.commit();session.refresh(event);session.expunge(event)
            return self._data(event)
        finally:session.close()
    def list_events(self,workspace_id):
        session=self.s()
        try:return [self._data(row) for row in session.scalars(select(AuditEvent).where(AuditEvent.workspace_id==workspace_id).order_by(AuditEvent.created_at.desc()).limit(200)).all()]
        finally:session.close()
    def get_resource_history(self,workspace_id,resource_id):
        session=self.s()
        try:return [self._data(row) for row in session.scalars(select(AuditEvent).where(AuditEvent.workspace_id==workspace_id,AuditEvent.resource_id==resource_id).order_by(AuditEvent.created_at.asc())).all()]
        finally:session.close()
    @staticmethod
    def _data(row):return {"id":row.id,"workspace_id":row.workspace_id,"user_id":row.user_id,"action_type":row.action_type,"resource_type":row.resource_type,"resource_id":row.resource_id,"mission_id":row.mission_id,"summary":row.summary,"result":row.result,"created_at":row.created_at}
