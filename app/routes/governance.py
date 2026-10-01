from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from app.services.governance_service import GovernanceService,GovernanceError
router=APIRouter(prefix="/api",tags=["governance"]);service=GovernanceService()
class Org(BaseModel):name:str;user_id:str="local-owner"
class Role(BaseModel):workspace_id:str;user_id:str;role:str;actor_id:str
class Check(BaseModel):workspace_id:str;user_id:str;permission:str
class Policy(BaseModel):workspace_id:str;actor_id:str|None=None;max_iterations:int|None=None;max_tool_calls:int|None=None;require_human_review:bool|None=None;allowed_connectors:list[str]=Field(default_factory=list)
@router.post("/organizations")
def org(p:Org):
 try:return service.create_org(p.name,p.user_id)
 except GovernanceError as e:raise HTTPException(400,detail=str(e))
@router.get("/organizations")
def orgs():return service.organizations()
@router.get("/workspaces")
def workspaces(organization_id:str|None=None):return service.workspaces(organization_id)
@router.post("/users/roles")
def role(p:Role):
 try:return service.set_role(p.workspace_id,p.user_id,p.role,p.actor_id)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
@router.post("/permissions/check")
def check(p:Check):
 try:return service.permissions.check(p.workspace_id,p.user_id,p.permission)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
@router.get("/audit/logs")
def logs(workspace_id:str|None=None):return service.logs(workspace_id)
@router.get("/policies")
def policy(workspace_id:str):
 try:return service.policy(workspace_id)
 except GovernanceError as e:raise HTTPException(404,detail=str(e))
@router.post("/policies")
def update_policy(p:Policy):
 try:return service.policy(p.workspace_id,p.model_dump(exclude={"workspace_id","actor_id"},exclude_none=True),p.actor_id)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
