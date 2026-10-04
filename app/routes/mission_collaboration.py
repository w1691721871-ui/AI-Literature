from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.identity_service import IdentityContext
from app.services.mission_collaboration_service import MissionCollaborationError, MissionCollaborationService
from app.services.permission_middleware import PermissionMiddleware


router = APIRouter(prefix="/api", tags=["mission-collaboration"])
service = MissionCollaborationService()
permissions = PermissionMiddleware()


class ParticipantInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    responsibility: str = Field(default="Mission collaborator", max_length=240)


class CommentInput(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)
    target_type: str = Field(default="MISSION", max_length=40)
    target_id: str = Field(default="", max_length=36)
    status: str = Field(default="COMMENTED", max_length=40)


@router.get("/workspace/team-dashboard")
def team_dashboard(context: IdentityContext = Depends(permissions.current)):
    permissions.require(context, "MISSION_VIEW")
    return service.dashboard(context.workspace_id)


@router.get("/workspace/members")
def workspace_members(context: IdentityContext = Depends(permissions.current)):
    permissions.require(context, "MISSION_VIEW")
    return service.members(context.workspace_id)


@router.get("/missions/{mission_id}/collaboration")
def mission_collaboration(mission_id: str, context: IdentityContext = Depends(permissions.current)):
    permissions.mission(context, mission_id, "MISSION_VIEW")
    try:
        return service.mission(context.workspace_id, mission_id)
    except MissionCollaborationError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/missions/{mission_id}/participants")
def assign_participant(mission_id: str, payload: ParticipantInput, context: IdentityContext = Depends(permissions.current)):
    permissions.mission(context, mission_id, "MISSION_ASSIGN")
    try:
        return service.assign(context.workspace_id, mission_id, payload.user_id, payload.responsibility, actor_id=context.user_id)
    except MissionCollaborationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/missions/{mission_id}/comments")
def add_comment(mission_id: str, payload: CommentInput, context: IdentityContext = Depends(permissions.current)):
    permissions.mission(context, mission_id, "MISSION_COMMENT")
    try:
        return service.comment(context.workspace_id, mission_id, context.user_id, payload.comment, target_type=payload.target_type, target_id=payload.target_id, status=payload.status)
    except MissionCollaborationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
