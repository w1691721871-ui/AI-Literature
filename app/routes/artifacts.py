from pathlib import Path
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.artifact_service import ArtifactError,ArtifactService
router=APIRouter(prefix="/api",tags=["artifacts"]);service=ArtifactService()
class Generate(BaseModel):artifact_type:str
class Review(BaseModel):status:str;comment:str=""
class Revise(BaseModel):reason:str=""
@router.post("/missions/{mission_id}/artifacts/generate")
def generate(mission_id:str,payload:Generate):
    try:return service.generate(mission_id,payload.artifact_type)
    except ArtifactError as e:raise HTTPException(400,detail=str(e)) from e
@router.get("/missions/{mission_id}/artifacts")
def list_mission(mission_id:str):return service.list(mission_id)
@router.get("/artifacts/analytics")
def analytics():return service.analytics()
@router.get("/artifacts/{artifact_id}")
def detail(artifact_id:str):
    try:return service.detail(artifact_id)
    except ArtifactError as e:raise HTTPException(404,detail=str(e)) from e
@router.get("/artifacts/{artifact_id}/versions")
def versions(artifact_id:str):
    try:return service.detail(artifact_id)["versions"]
    except ArtifactError as e:raise HTTPException(404,detail=str(e)) from e
@router.get("/artifacts/{artifact_id}/evidence")
def evidence(artifact_id:str):
    try:return service.detail(artifact_id)["evidence"]
    except ArtifactError as e:raise HTTPException(404,detail=str(e)) from e
@router.post("/artifacts/{artifact_id}/review")
def review(artifact_id:str,payload:Review):
    try:return service.review(artifact_id,payload.status,payload.comment)
    except ArtifactError as e:raise HTTPException(400,detail=str(e)) from e
@router.post("/artifacts/{artifact_id}/revise")
def revise(artifact_id:str,payload:Revise):
    try:return service.revise(artifact_id,payload.reason)
    except ArtifactError as e:raise HTTPException(400,detail=str(e)) from e
@router.get("/artifacts/{artifact_id}/download")
def download(artifact_id:str):
    try:
        file=service.download_path(artifact_id)
        return FileResponse(file,filename=file.name)
    except ArtifactError as e:raise HTTPException(404,detail=str(e)) from e
