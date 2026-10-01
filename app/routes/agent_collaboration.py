from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from app.services.agent_collaboration_service import AgentMessageBus,AgentMessageError

router=APIRouter(prefix="/api/agent",tags=["agent-collaboration"]);service=AgentMessageBus()
class MessagePayload(BaseModel):
    mission_id:str
    sender_agent:str
    receiver_agent:str
    message_type:str
    payload_summary:str

@router.get("/messages/{mission_id}")
def messages(mission_id:str):return service.messages(mission_id)
@router.get("/collaboration/analytics")
def analytics():return service.analytics()
@router.get("/collaboration/{mission_id}")
def collaboration(mission_id:str):return service.graph(mission_id)
@router.get("/conflicts/{mission_id}")
def conflicts(mission_id:str):return service.conflicts(mission_id)
@router.post("/messages/send")
def send(payload:MessagePayload):
    try:return service.send(payload.model_dump())
    except AgentMessageError as error:raise HTTPException(400,detail=str(error)) from error
