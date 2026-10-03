"""Workspace Context and Research Memory product endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.ai_mission_service import AIMissionNotFoundError, AIMissionService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
from app.services.workspace_context_service import WorkspaceContextService
from app.services.workspace_memory_service import WorkspaceMemoryError, WorkspaceMemoryService
from app.services.skill_capability_registry import SkillCapabilityRegistry


router = APIRouter(prefix="/api", tags=["workspace-context"])
permissions = PermissionMiddleware()
missions = AIMissionService()
context_service = WorkspaceContextService()
memory_service = WorkspaceMemoryService()
capabilities = SkillCapabilityRegistry()


class UserMemoryPreference(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    summary: str = Field(min_length=1, max_length=1200)


@router.get("/workspace/context")
def current_workspace_context(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.require(context, "MISSION_VIEW")
    return {
        "workspace": {"id": context.workspace_id, "role": context.role},
        "memory": memory_service.context_slice(context.workspace_id, user_id=context.user_id, mission_id=None),
        "boundary": "Workspace Context contains only authorized summaries. It excludes prompts, CoT, credentials and source-document bodies.",
    }


@router.get("/ai-worker/capabilities")
def ai_worker_capabilities(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    """Expose the controlled Skill catalog, never a legacy Agent registry."""
    permissions.require(context, "MISSION_VIEW")
    return {
        "worker": "AI Worker",
        "skills": capabilities.catalog(),
        "boundary": "Capabilities operate only within the current authorized Workspace. Important actions remain review-gated.",
    }


@router.get("/missions/{mission_id}/context")
def mission_context(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_VIEW")
    try:
        return context_service.build(missions.detail(mission_id), actor=context)
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Mission is unavailable.") from error


@router.get("/research-memory")
def list_research_memory(mission_id: str | None = None, context: IdentityContext = Depends(permissions.current)) -> list[dict[str, object]]:
    permissions.require(context, "KNOWLEDGE_VIEW")
    if mission_id:
        permissions.mission(context, mission_id, "MISSION_VIEW")
    return memory_service.list(context.workspace_id, user_id=context.user_id, mission_id=mission_id)


@router.post("/research-memory/preferences", status_code=status.HTTP_201_CREATED)
def save_user_memory(payload: UserMemoryPreference, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.require(context, "MISSION_VIEW")
    try:
        return memory_service.save_user_preference(context.workspace_id, context.user_id, payload.title, payload.summary)
    except WorkspaceMemoryError as error:
        raise HTTPException(status_code=400, detail="Memory must be a compact non-sensitive summary.") from error


@router.get("/research-memory/{memory_id}/explain")
def explain_research_memory(memory_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.require(context, "KNOWLEDGE_VIEW")
    try:
        return memory_service.explain(memory_id, context.workspace_id, user_id=context.user_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="Memory belongs to another Workspace member.") from error
    except WorkspaceMemoryError as error:
        raise HTTPException(status_code=404, detail="Memory is unavailable.") from error


@router.delete("/research-memory/{memory_id}")
def delete_research_memory(memory_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    try:
        allow_workspace_delete = context.role in {"OWNER", "ADMIN", "MANAGER", "REVIEWER"}
        return memory_service.delete(memory_id, context.workspace_id, user_id=context.user_id, allow_workspace_delete=allow_workspace_delete)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="You do not have permission to remove this Workspace memory.") from error
    except WorkspaceMemoryError as error:
        raise HTTPException(status_code=404, detail="Memory is unavailable.") from error
