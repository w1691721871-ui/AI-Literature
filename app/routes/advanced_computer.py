from fastapi import APIRouter,Depends,HTTPException
from app.services.advanced_computer_service import AdvancedComputerService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
router=APIRouter(prefix="/api",tags=["advanced-computer"]);service=AdvancedComputerService();permissions=PermissionMiddleware()
@router.get("/computer/environments/{mid}")
def environment(mid:str,context:IdentityContext=Depends(permissions.current)):
 permissions.admin_console(context);return service.environment(mid)
@router.get("/computer/plans/{mid}")
def plan(mid:str,context:IdentityContext=Depends(permissions.current)):
 permissions.admin_console(context)
 r=service.plan(mid)
 if not r:raise HTTPException(404,detail="Computer mission not found.")
 return r
@router.get("/computer/observations/{mid}")
def observations(mid:str,context:IdentityContext=Depends(permissions.current)):
 permissions.admin_console(context);return service.observations(mid)
@router.post("/computer/plans/{pid}/approve")
def approve(pid:str,context:IdentityContext=Depends(permissions.current)):
 permissions.admin_console(context);return service.approve(pid)
@router.post("/computer/actions/{aid}/verify")
def verify(aid:str,context:IdentityContext=Depends(permissions.current)):
 permissions.admin_console(context);return {"action_id":aid,"success":False,"reason":"Use the existing controlled Computer Mission verification endpoint; this layer does not bypass approval."}
@router.get("/computer/experience")
def experience(context:IdentityContext=Depends(permissions.current)):
 permissions.admin_console(context);return service.experience()
