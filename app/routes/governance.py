from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from app.services.governance_service import GovernanceService,GovernanceError
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
router=APIRouter(prefix="/api",tags=["governance"]);service=GovernanceService()
permissions=PermissionMiddleware()
class Org(BaseModel):name:str
class Role(BaseModel):workspace_id:str;user_id:str;role:str
class Check(BaseModel):workspace_id:str;permission:str
class Policy(BaseModel):workspace_id:str;max_iterations:int|None=None;max_tool_calls:int|None=None;require_human_review:bool|None=None;allowed_connectors:list[str]=Field(default_factory=list)
@router.post("/organizations")
def org(p:Org,context:IdentityContext=Depends(permissions.current)):
 try:return service.create_org(p.name,context.user_id)
 except GovernanceError as e:raise HTTPException(400,detail=str(e))
@router.get("/organizations")
def orgs(context:IdentityContext=Depends(permissions.current)):return service.organizations()
@router.get("/workspaces")
def workspaces(organization_id:str|None=None,context:IdentityContext=Depends(permissions.current)):
 return [item for item in service.workspaces(organization_id) if item["id"]==context.workspace_id]
@router.post("/users/roles")
def role(p:Role,context:IdentityContext=Depends(permissions.current)):
 try:
  if p.workspace_id!=context.workspace_id:raise GovernanceError("Cross-workspace role update denied.")
  return service.set_role(p.workspace_id,p.user_id,p.role,context.user_id)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
@router.post("/permissions/check")
def check(p:Check,context:IdentityContext=Depends(permissions.current)):
 try:
  if p.workspace_id!=context.workspace_id:raise GovernanceError("Cross-workspace permission check denied.")
  return service.permissions.check(p.workspace_id,context.user_id,p.permission)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
@router.get("/audit/logs")
def logs(workspace_id:str|None=None,context:IdentityContext=Depends(permissions.current)):
 if workspace_id and workspace_id!=context.workspace_id:raise HTTPException(403,detail="Cross-workspace audit access denied.")
 permissions.require(context,"MISSION_APPROVE");return service.logs(context.workspace_id)
@router.get("/policies")
def policy(workspace_id:str,context:IdentityContext=Depends(permissions.current)):
 try:
  if workspace_id!=context.workspace_id:raise GovernanceError("Cross-workspace policy access denied.")
  permissions.require(context,"MISSION_APPROVE")
  return service.policy(workspace_id)
 except GovernanceError as e:raise HTTPException(404,detail=str(e))
@router.post("/policies")
def update_policy(p:Policy,context:IdentityContext=Depends(permissions.current)):
 try:
  if p.workspace_id!=context.workspace_id:raise GovernanceError("Cross-workspace policy update denied.")
  return service.policy(p.workspace_id,p.model_dump(exclude={"workspace_id"},exclude_none=True),context.user_id)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
