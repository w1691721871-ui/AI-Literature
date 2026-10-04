"""P33 RBAC and audit boundary for governed APIs."""
import json
from sqlalchemy import select
from app.models.organization import Organization
from app.models.governance import GovernanceWorkspace,WorkspaceUserRole,AuditLog,AgentPolicy
from app.services.database import SessionLocal,initialize_database
class GovernanceError(ValueError):pass
class PermissionService:
    roles={"OWNER","ADMIN","MANAGER","MEMBER","REVIEWER","VIEWER"}
    grants={
        "MISSION_CREATE":{"OWNER","ADMIN","MANAGER","MEMBER"},
        "MISSION_VIEW":{"OWNER","ADMIN","MANAGER","MEMBER","REVIEWER","VIEWER"},
        "MISSION_EXECUTE":{"OWNER","ADMIN","MANAGER","MEMBER"},
        "MISSION_ASSIGN":{"OWNER","ADMIN","MANAGER"},
        "MISSION_COMMENT":{"OWNER","ADMIN","MANAGER","MEMBER","REVIEWER"},
        "MISSION_APPROVE":{"OWNER","ADMIN","MANAGER","REVIEWER"},
        "COMPUTER_EXECUTE":{"OWNER","ADMIN","MANAGER","MEMBER"},
        "ARTIFACT_VIEW":{"OWNER","ADMIN","MANAGER","MEMBER","REVIEWER","VIEWER"},
        "ARTIFACT_DOWNLOAD":{"OWNER","ADMIN","MANAGER","MEMBER","REVIEWER","VIEWER"},
        "ARTIFACT_REVIEW":{"OWNER","ADMIN","MANAGER","REVIEWER"},
        "CONNECTOR_ACCESS":{"OWNER","ADMIN","MANAGER","MEMBER"},
        "KNOWLEDGE_ACCESS":{"OWNER","ADMIN","MANAGER","MEMBER","REVIEWER","VIEWER"},
        "KNOWLEDGE_VIEW":{"OWNER","ADMIN","MANAGER","MEMBER","REVIEWER","VIEWER"},
        "KNOWLEDGE_APPROVE":{"OWNER","ADMIN","MANAGER","REVIEWER"},
    }
    def __init__(self,sessions=SessionLocal,*,initialize=True):
        if initialize:initialize_database()
        self.s=sessions
    def check(self,workspace_id,user_id,permission):
        s=self.s()
        try:
            role=s.scalar(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id==workspace_id,WorkspaceUserRole.user_id==user_id))
            allowed=bool(role and role.role in self.grants.get(permission,set()))
            self.audit(s,user_id,workspace_id,"PERMISSION_CHECK","Permission",permission,"Allowed" if allowed else "Blocked")
            s.commit()
            if not allowed:raise GovernanceError("RBAC 拒绝该操作。")
            return {"allowed":True,"role":role.role,"permission":permission}
        finally:s.close()
    def can_create_mission(self,workspace_id,user_id): return self._can(workspace_id,user_id,"MISSION_CREATE")
    def can_view_mission(self,workspace_id,user_id): return self._can(workspace_id,user_id,"MISSION_VIEW")
    def can_execute_computer(self,workspace_id,user_id): return self._can(workspace_id,user_id,"COMPUTER_EXECUTE")
    def can_download_artifact(self,workspace_id,user_id): return self._can(workspace_id,user_id,"ARTIFACT_DOWNLOAD")
    def can_manage_connector(self,workspace_id,user_id): return self._can(workspace_id,user_id,"CONNECTOR_ACCESS")
    def can_approve_review(self,workspace_id,user_id): return self._can(workspace_id,user_id,"ARTIFACT_REVIEW")
    def _can(self,workspace_id,user_id,permission):
        try:self.check(workspace_id,user_id,permission);return True
        except GovernanceError:return False
    @staticmethod
    def audit(s,user,workspace,action,kind,resource,summary):s.add(AuditLog(user_id=user,workspace_id=workspace,action=action,resource_type=kind,resource_id=resource,summary=summary[:500]))
class GovernanceService:
    def __init__(self,sessions=SessionLocal,*,initialize=True):
        if initialize:initialize_database()
        self.s=sessions;self.permissions=PermissionService(sessions,initialize=False)
    def create_org(self,name,user_id):
        s=self.s()
        try:
            org=Organization(name=name.strip());s.add(org);s.flush(); ws=GovernanceWorkspace(organization_id=org.id,name=f"{org.name} Workspace",owner_id=user_id);s.add(ws);s.flush();s.add(WorkspaceUserRole(workspace_id=ws.id,user_id=user_id,role="OWNER"));s.add(AgentPolicy(workspace_id=ws.id));self.permissions.audit(s,user_id,ws.id,"CREATE_ORGANIZATION","Organization",org.id,"Organization and default workspace created.");s.commit();return {"id":org.id,"name":org.name,"status":"ACTIVE","workspace_id":ws.id}
        finally:s.close()
    def workspaces(self,organization_id=None):
        s=self.s()
        try:
            q=select(GovernanceWorkspace);q=q.where(GovernanceWorkspace.organization_id==organization_id) if organization_id else q
            return [{"id":x.id,"organization_id":x.organization_id,"name":x.name,"created_at":x.created_at} for x in s.scalars(q).all()]
        finally:s.close()
    def organizations(self):
        s=self.s()
        try:return [{"id":x.id,"name":x.name,"status":"ACTIVE","created_at":x.created_at} for x in s.scalars(select(Organization).order_by(Organization.created_at.desc())).all()]
        finally:s.close()
    def set_role(self,workspace_id,user_id,role,actor):
        if role not in self.permissions.roles:raise GovernanceError("无效角色。")
        self.permissions.check(workspace_id,actor,"MISSION_APPROVE");s=self.s()
        try:
            row=s.scalar(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id==workspace_id,WorkspaceUserRole.user_id==user_id))
            if row:row.role=role
            else:s.add(WorkspaceUserRole(workspace_id=workspace_id,user_id=user_id,role=role))
            self.permissions.audit(s,actor,workspace_id,"SET_ROLE","UserRole",user_id,f"Role set to {role}.");s.commit();return {"workspace_id":workspace_id,"user_id":user_id,"role":role}
        finally:s.close()
    def logs(self,workspace_id=None):
        s=self.s()
        try:
            q=select(AuditLog).order_by(AuditLog.created_at.desc());q=q.where(AuditLog.workspace_id==workspace_id) if workspace_id else q
            return [{"user_id":x.user_id,"workspace_id":x.workspace_id,"action":x.action,"resource_type":x.resource_type,"resource_id":x.resource_id,"summary":x.summary,"created_at":x.created_at} for x in s.scalars(q.limit(100)).all()]
        finally:s.close()
    def policy(self,workspace_id,data=None,actor=None):
        s=self.s()
        try:
            row=s.scalar(select(AgentPolicy).where(AgentPolicy.workspace_id==workspace_id))
            if not row:raise GovernanceError("Workspace Policy 不存在。")
            if data is not None:
                self.permissions.check(workspace_id,actor,"MISSION_APPROVE")
                row.max_iterations=max(1,min(int(data.get("max_iterations",row.max_iterations)),10));row.max_tool_calls=max(1,min(int(data.get("max_tool_calls",row.max_tool_calls)),50));row.require_human_review=bool(data.get("require_human_review",row.require_human_review));row.allowed_connectors=json.dumps(data.get("allowed_connectors",[]));self.permissions.audit(s,actor,workspace_id,"UPDATE_POLICY","AgentPolicy",row.id,"Policy updated without changing Agent runtime.");s.commit()
            return {"workspace_id":workspace_id,"max_iterations":row.max_iterations,"max_tool_calls":row.max_tool_calls,"require_human_review":row.require_human_review,"allowed_connectors":json.loads(row.allowed_connectors or "[]")}
        finally:s.close()
