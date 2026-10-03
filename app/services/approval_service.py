"""Approval Center service. It records decisions but never bypasses existing flows."""
from datetime import datetime, timezone
from sqlalchemy import select
from app.models.ai_mission import AIMission
from app.models.approval import ApprovalRequest
from app.models.artifact import Artifact
from app.models.computer_mission import ComputerMission
from app.models.enterprise_memory import KnowledgeAsset
from app.services.audit_service import AuditService
from app.services.database import SessionLocal, initialize_database
from app.services.identity_service import IdentityContext

class ApprovalError(ValueError):pass

class ApprovalService:
    TYPES={"EVIDENCE_VERIFY","ARTIFACT_RELEASE","COMPUTER_EXECUTION","DECISION_CONFIRMATION","KNOWLEDGE_UPDATE"}
    PRIORITIES={"LOW","NORMAL","HIGH"}
    def __init__(self,sessions=SessionLocal,*,initialize=True,audit=None):
        if initialize:initialize_database()
        self.s=sessions;self.audit=audit or AuditService(sessions,initialize=False)
    def create_request(self,context:IdentityContext,source_type,source_id,request_type,priority="NORMAL",comment=""):
        if request_type not in self.TYPES or priority not in self.PRIORITIES:raise ApprovalError("Invalid approval request.")
        source_type = source_type.strip().upper()
        mission_id=self._source_mission(context.workspace_id,source_type,source_id)
        session=self.s()
        try:
            row=ApprovalRequest(workspace_id=context.workspace_id,mission_id=mission_id,source_type=source_type,source_id=source_id,request_type=request_type,creator_id=context.user_id,priority=priority,comment=(comment or "")[:2000])
            session.add(row);session.commit();session.refresh(row);session.expunge(row)
        finally:session.close()
        self.audit.record_event(context.workspace_id,context.user_id,"APPROVAL_CREATED","ApprovalRequest",row.id,mission_id,"A review request was created.")
        return self._data(row)
    def list_pending(self,context:IdentityContext):
        session=self.s()
        try:return [self._data(row) for row in session.scalars(select(ApprovalRequest).where(ApprovalRequest.workspace_id==context.workspace_id).order_by(ApprovalRequest.created_at.desc())).all()]
        finally:session.close()
    def get_request(self,context:IdentityContext,request_id):
        row=self._row(request_id)
        self._scope(context,row);return self._data(row)
    def approve_request(self,context,request_id,comment=""):return self._resolve(context,request_id,"APPROVED",comment,"APPROVAL_APPROVED")
    def reject_request(self,context,request_id,comment=""):return self._resolve(context,request_id,"REJECTED",comment,"APPROVAL_REJECTED")
    def request_changes(self,context,request_id,comment=""):return self._resolve(context,request_id,"CHANGES_REQUESTED",comment,"APPROVAL_CHANGES_REQUESTED")
    def _resolve(self,context,request_id,status,comment,action):
        session=self.s()
        try:
            row=session.get(ApprovalRequest,request_id)
            if not row:raise ApprovalError("Approval request not found.")
            self._scope(context,row)
            if row.status!="PENDING":raise ApprovalError("Approval request is already resolved.")
            row.status=status;row.reviewer_id=context.user_id;row.comment=(comment or row.comment)[:2000];row.resolved_at=datetime.now(timezone.utc);session.commit();session.refresh(row);session.expunge(row)
        finally:session.close()
        self.audit.record_event(context.workspace_id,context.user_id,action,"ApprovalRequest",request_id,row.mission_id,"Human review decision recorded.")
        return self._data(row)
    def _source_mission(self,workspace_id,source_type,source_id):
        session=self.s()
        try:
            mission=None
            if source_type=="MISSION":mission=session.get(AIMission,source_id)
            elif source_type=="ARTIFACT":
                item=session.get(Artifact,source_id);mission=session.get(AIMission,item.mission_id) if item else None
            elif source_type=="COMPUTER":
                item=session.get(ComputerMission,source_id);mission=session.get(AIMission,item.mission_id) if item and item.mission_id else None
            elif source_type=="KNOWLEDGE":
                item=session.get(KnowledgeAsset,source_id)
                if item and item.workspace_id==workspace_id:return None
            if not mission or mission.workspace_id!=workspace_id:raise ApprovalError("Approval source is outside the current Workspace.")
            return mission.id
        finally:session.close()
    @staticmethod
    def _scope(context,row):
        if row.workspace_id!=context.workspace_id:raise ApprovalError("Cross-workspace approval access denied.")
    def _row(self,request_id):
        session=self.s()
        try:
            row=session.get(ApprovalRequest,request_id)
            if not row:raise ApprovalError("Approval request not found.")
            session.expunge(row);return row
        finally:session.close()
    @staticmethod
    def _data(row):return {"id":row.id,"workspace_id":row.workspace_id,"mission_id":row.mission_id,"source_type":row.source_type,"source_id":row.source_id,"request_type":row.request_type,"creator_id":row.creator_id,"reviewer_id":row.reviewer_id,"status":row.status,"priority":row.priority,"comment":row.comment,"created_at":row.created_at,"updated_at":row.updated_at,"resolved_at":row.resolved_at}
