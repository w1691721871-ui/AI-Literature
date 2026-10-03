from fastapi import APIRouter,Depends,HTTPException
from app.services.enterprise_memory_service import DecisionMemoryService,MemoryError
from app.services.governance_service import GovernanceError
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
router=APIRouter(prefix="/api",tags=["enterprise-memory"]);service=DecisionMemoryService()
permissions=PermissionMiddleware()
@router.get("/knowledge/assets")
def assets(context:IdentityContext=Depends(permissions.current)):
 permissions.require(context,"KNOWLEDGE_VIEW");return service.assets(workspace_id=context.workspace_id)
@router.get("/knowledge/assets/{ident}")
def asset(ident:str,context:IdentityContext=Depends(permissions.current)):
 permissions.knowledge(context,ident,"KNOWLEDGE_VIEW");rows=service.assets(ident)
 if not rows:raise HTTPException(404,detail="Knowledge asset not found.")
 return rows[0]
@router.get("/knowledge/decisions")
def decisions(context:IdentityContext=Depends(permissions.current)):
 permissions.require(context,"KNOWLEDGE_VIEW");return service.decisions(context.workspace_id)
@router.post("/knowledge/decisions/{ident}/approve")
def approve(ident:str,context:IdentityContext=Depends(permissions.current)):
 permissions.require(context,"KNOWLEDGE_APPROVE")
 try:return service.approve(ident,context.workspace_id,context.user_id)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
 except MemoryError as e:raise HTTPException(404,detail=str(e))
@router.get("/knowledge/experience/search")
def search(query:str,context:IdentityContext=Depends(permissions.current)):
 permissions.require(context,"KNOWLEDGE_VIEW");return service.experiences.search(query,context.workspace_id)
@router.get("/knowledge/dashboard")
def dashboard(context:IdentityContext=Depends(permissions.current)):
 permissions.require(context,"KNOWLEDGE_VIEW");return service.dashboard(context.workspace_id)
