from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from app.services.agent_collaboration_service import AgentMessageBus,AgentMessageError
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware

router=APIRouter(prefix="/api/agent",tags=["agent-collaboration"]);service=AgentMessageBus();permissions=PermissionMiddleware()
class MessagePayload(BaseModel):
    mission_id:str
    sender_agent:str
    receiver_agent:str
    message_type:str
    payload_summary:str

@router.get("/messages/{mission_id}")
def messages(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_VIEW");return service.messages(mission_id)
@router.get("/collaboration/analytics")
def analytics(context:IdentityContext=Depends(permissions.current)):
    permissions.admin_console(context);return service.analytics()
@router.get("/collaboration/{mission_id}")
def collaboration(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_VIEW");return service.graph(mission_id)
@router.get("/conflicts/{mission_id}")
def conflicts(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_VIEW");return service.conflicts(mission_id)
@router.post("/messages/send")
def send(payload:MessagePayload,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,payload.mission_id,"MISSION_EXECUTE")
    try:return service.send(payload.model_dump())
    except AgentMessageError as error:raise HTTPException(400,detail=str(error)) from error
