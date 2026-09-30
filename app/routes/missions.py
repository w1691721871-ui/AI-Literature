"""Public AI Mission Center endpoints, isolated from research execution APIs."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.mission import AIMissionCreate, AIMissionReview, AIMissionRevision
from app.services.ai_mission_service import AIMissionNotFoundError, AIMissionService


router = APIRouter(prefix="/api", tags=["ai-missions"])
service = AIMissionService()


@router.post("/missions", status_code=status.HTTP_201_CREATED)
def create_mission(payload: AIMissionCreate) -> dict[str, object]:
    return service.create(payload.model_dump())


@router.post("/missions/{mission_id}/run")
def run_mission(mission_id: str) -> dict[str, object]:
    try:
        return service.run(mission_id)
    except (AIMissionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/missions/{mission_id}/review")
def review_mission(mission_id: str, payload: AIMissionReview) -> dict[str, object]:
    try:
        return service.review(mission_id, payload.status, payload.review_comment)
    except (AIMissionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/missions/{mission_id}/revise")
def revise_mission(mission_id: str, payload: AIMissionRevision) -> dict[str, object]:
    try:
        return service.revise(mission_id, payload.change_summary)
    except (AIMissionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/missions/{mission_id}/delivery")
def mission_delivery(mission_id: str) -> dict[str, object]:
    try:
        return service.delivery(mission_id)
    except (AIMissionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/missions")
def list_missions() -> list[dict[str, object]]:
    return service.list()


@router.get("/missions/dashboard")
def mission_dashboard() -> dict[str, object]:
    return service.dashboard()


@router.get("/missions/{mission_id}")
def mission_detail(mission_id: str) -> dict[str, object]:
    try:
        return service.detail(mission_id)
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/missions/{mission_id}/timeline")
def mission_timeline(mission_id: str) -> list[dict[str, object]]:
    try:
        return service.timeline(mission_id)
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/notifications")
def list_notifications() -> list[dict[str, object]]:
    return service.notifications()


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str) -> dict[str, object]:
    try:
        return service.mark_notification_read(notification_id)
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
