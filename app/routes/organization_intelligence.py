"""Current-Workspace organizational learning endpoint."""

from fastapi import APIRouter, Depends

from app.services.identity_service import IdentityContext
from app.services.organization_intelligence_service import OrganizationIntelligenceService
from app.services.permission_middleware import PermissionMiddleware


router = APIRouter(prefix="/api/workspace", tags=["organization-intelligence"])
service = OrganizationIntelligenceService()
permissions = PermissionMiddleware()


@router.get("/intelligence")
def organization_intelligence(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.require(context, "MISSION_VIEW")
    return service.overview(context.workspace_id)
