"""Workspace-scoped audit access for the Admin Console."""
from fastapi import APIRouter, Depends, HTTPException

from app.services.audit_service import AuditService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware


router = APIRouter(prefix="/api/audit", tags=["audit"])
audit = AuditService()
permissions = PermissionMiddleware()


def _admin(context: IdentityContext) -> None:
    if context.role not in {"OWNER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Admin Console access is required for Audit Log.")


@router.get("/events")
def list_events(context: IdentityContext = Depends(permissions.current)) -> list[dict[str, object]]:
    _admin(context)
    return audit.list_events(context.workspace_id)


@router.get("/resources/{resource_id}")
def resource_history(resource_id: str, context: IdentityContext = Depends(permissions.current)) -> list[dict[str, object]]:
    _admin(context)
    return audit.get_resource_history(context.workspace_id, resource_id)
