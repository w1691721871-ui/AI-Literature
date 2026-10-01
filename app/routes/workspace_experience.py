from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from app.services.governance_service import GovernanceError
from app.services.artifact_service import ArtifactError
from app.services.workspace_experience_service import WorkspaceExperienceError,WorkspaceExperienceService
router=APIRouter(prefix="/api",tags=["workspace-experience"]);service=WorkspaceExperienceService()
class Comment(BaseModel):reviewer_id:str=Field(min_length=1);workspace_id:str=Field(min_length=1);comment:str=Field(min_length=1,max_length=2000);request_revision:bool=False
@router.get("/workspace/dashboard")
def dashboard():return service.dashboard()
@router.get("/missions/{mission_id}/workspace")
def workspace(mission_id:str):
 try:return service.mission_workspace(mission_id)
 except (ValueError,WorkspaceExperienceError) as e:raise HTTPException(404,detail=str(e))
@router.get("/artifacts/{artifact_id}/preview")
def preview(artifact_id:str):
 try:return service.preview(artifact_id)
 except (WorkspaceExperienceError,ArtifactError) as e:raise HTTPException(404,detail=str(e))
@router.post("/artifacts/{artifact_id}/comments")
def comment(artifact_id:str,payload:Comment):
 try:return service.comment(artifact_id,payload.reviewer_id,payload.comment,payload.workspace_id,payload.request_revision)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
 except WorkspaceExperienceError as e:raise HTTPException(404,detail=str(e))
