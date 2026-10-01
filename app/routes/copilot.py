"""P28 natural-language Copilot endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.copilot_mission_service import CopilotMissionService
router=APIRouter(prefix="/api/copilot",tags=["copilot"]); service=CopilotMissionService()
class SessionRequest(BaseModel): user_id:str="local-user"
class ChatRequest(BaseModel): session_id:str; message:str=Field(min_length=1,max_length=4000)
@router.post("/session")
def create_session(payload:SessionRequest): return service.create_session(payload.user_id)
@router.post("/chat")
def chat(payload:ChatRequest):
    try:return service.chat(payload.session_id,payload.message)
    except ValueError as error:raise HTTPException(status_code=400,detail=str(error)) from error
@router.get("/session/{session_id}")
def session(session_id:str):
    try:return service.get(session_id)
    except ValueError as error:raise HTTPException(status_code=404,detail=str(error)) from error
@router.get("/session/{session_id}/activity")
def activity(session_id:str):
    try:return service.activity(session_id)
    except ValueError as error:raise HTTPException(status_code=404,detail=str(error)) from error
@router.post("/session/{session_id}/start")
def start(session_id:str):
    try:return service.start(session_id)
    except ValueError as error:raise HTTPException(status_code=400,detail=str(error)) from error
@router.get("/analytics")
def analytics():return service.analytics()
