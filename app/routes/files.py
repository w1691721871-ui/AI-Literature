"""P29 enterprise input APIs. Uploads remain customer material, not RAG Evidence."""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from app.services.file_input_service import FileInputError, FileInputService

router=APIRouter(prefix="/api/files",tags=["enterprise-input"])
service=FileInputService()

class CreateMissionRequest(BaseModel):
    confirmed: bool=False
    user_id: str="local-user"

@router.post("/upload")
async def upload(file: UploadFile=File(...), user_id: str=Form("local-user")):
    try:return service.upload(file.filename or "upload",await file.read(),user_id)
    except FileInputError as error: raise HTTPException(status_code=400,detail=str(error)) from error

@router.get("")
def list_files(user_id: str="local-user"):
    return service.list(user_id)

@router.get("/analytics")
def analytics(): return service.analytics()

@router.get("/{file_id}/analysis")
def analysis(file_id: str):
    try:return service.analysis(file_id)
    except FileInputError as error: raise HTTPException(status_code=404,detail=str(error)) from error

@router.post("/{file_id}/create-mission")
def create_mission(file_id: str,payload: CreateMissionRequest):
    try:return service.create_mission(file_id,payload.confirmed,payload.user_id)
    except FileInputError as error: raise HTTPException(status_code=400,detail=str(error)) from error
