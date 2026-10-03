from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.artifact_service import ArtifactError,ArtifactService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
from app.services.audit_service import AuditService
router=APIRouter(prefix="/api",tags=["artifacts"]);service=ArtifactService()
permissions=PermissionMiddleware()
audit=AuditService()
class Generate(BaseModel):artifact_type:str
class Review(BaseModel):status:str;comment:str=""
class Revise(BaseModel):reason:str=""
@router.post("/missions/{mission_id}/artifacts/generate")
def generate(mission_id:str,payload:Generate,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_EXECUTE")
    try:return service.generate(mission_id,payload.artifact_type)
    except ArtifactError as e:raise HTTPException(400,detail=str(e)) from e
@router.get("/missions/{mission_id}/artifacts")
def list_mission(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"ARTIFACT_VIEW");return service.list(mission_id)
@router.get("/artifacts/analytics")
def analytics(context:IdentityContext=Depends(permissions.current)):
    permissions.require(context,"ARTIFACT_VIEW");return service.analytics(context.workspace_id)
@router.get("/artifacts/{artifact_id}")
def detail(artifact_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.artifact(context,artifact_id,"ARTIFACT_VIEW")
    try:return service.detail(artifact_id)
    except ArtifactError as e:raise HTTPException(404,detail=str(e)) from e
@router.get("/artifacts/{artifact_id}/versions")
def versions(artifact_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.artifact(context,artifact_id,"ARTIFACT_VIEW")
    try:return service.detail(artifact_id)["versions"]
    except ArtifactError as e:raise HTTPException(404,detail=str(e)) from e
@router.get("/artifacts/{artifact_id}/evidence")
def evidence(artifact_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.artifact(context,artifact_id,"ARTIFACT_VIEW")
    try:return service.detail(artifact_id)["evidence"]
    except ArtifactError as e:raise HTTPException(404,detail=str(e)) from e
@router.post("/artifacts/{artifact_id}/review")
def review(artifact_id:str,payload:Review,context:IdentityContext=Depends(permissions.current)):
    permissions.artifact(context,artifact_id,"ARTIFACT_REVIEW")
    try:
        result=service.review(artifact_id,payload.status,payload.comment)
        action="ARTIFACT_RELEASED" if payload.status=="APPROVED" else "ARTIFACT_REVIEWED"
        audit.record_event(context.workspace_id,context.user_id,action,"Artifact",artifact_id,result.get("mission_id"),"Artifact review decision recorded.",payload.status)
        return result
    except ArtifactError as e:raise HTTPException(400,detail=str(e)) from e
@router.post("/artifacts/{artifact_id}/revise")
def revise(artifact_id:str,payload:Revise,context:IdentityContext=Depends(permissions.current)):
    permissions.artifact(context,artifact_id,"ARTIFACT_REVIEW")
    try:return service.revise(artifact_id,payload.reason)
    except ArtifactError as e:raise HTTPException(400,detail=str(e)) from e
@router.get("/artifacts/{artifact_id}/download")
def download(artifact_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.artifact(context,artifact_id,"ARTIFACT_DOWNLOAD")
    try:
        file=service.download_path(artifact_id)
        return FileResponse(file,filename=file.name)
    except ArtifactError as e:raise HTTPException(404,detail=str(e)) from e
