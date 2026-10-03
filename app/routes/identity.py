"""Explicit identity endpoints. No local/default identity is created."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.identity_service import IdentityContext, IdentityError, IdentityService
from app.services.permission_middleware import PermissionMiddleware


router = APIRouter(prefix="/api/identity", tags=["identity"])
service = IdentityService()
permissions = PermissionMiddleware(identities=service)


class UserRegistration(BaseModel):
    email: str
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=512)


class WorkspaceRegistration(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: str
    password: str = Field(min_length=12, max_length=512)
    workspace_name: str = Field(min_length=1, max_length=160)


class SessionLogin(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=512)
    # Workspace selection is optional during login. The server selects only
    # among persisted memberships, then later permits explicit switching.
    workspace_id: str | None = Field(default=None, min_length=1, max_length=36)


class WorkspaceSwitch(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=36)


@router.post("/users", status_code=status.HTTP_201_CREATED)
def register(payload: UserRegistration) -> dict[str, object]:
    try:
        return service.register(payload.email, payload.display_name, payload.password)
    except IdentityError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_workspace(payload: WorkspaceRegistration) -> dict[str, object]:
    try:
        return service.register_workspace(payload.email, payload.name, payload.password, payload.workspace_name)
    except IdentityError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/demo-session")
def demo_session() -> dict[str, object]:
    try:
        return service.create_demo_session()
    except IdentityError as error:
        raise HTTPException(status_code=400, detail="Demo Workspace could not be started.") from error


@router.post("/sessions")
def login(payload: SessionLogin) -> dict[str, object]:
    try:
        return service.create_session(payload.email, payload.password, payload.workspace_id)
    except IdentityError as error:
        raise HTTPException(status_code=401, detail="Invalid login or Workspace access.") from error


@router.get("/me")
def me(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    return service.profile(context)


@router.post("/sessions/switch")
def switch_workspace(payload: WorkspaceSwitch, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    try:
        return service.switch_workspace(context, payload.workspace_id)
    except IdentityError as error:
        raise HTTPException(status_code=403, detail="Workspace switch denied.") from error
