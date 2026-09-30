"""P24 public Computer Mission API; isolated from legacy Computer Use routes."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.computer_mission import ComputerMissionApproval, ComputerMissionCreate
from app.services.controlled_computer_mission_service import (
    ControlledComputerMissionNotFoundError,
    ControlledComputerMissionService,
)


router = APIRouter(prefix="/api", tags=["computer-missions"])
service = ControlledComputerMissionService()


@router.post("/computer-missions", status_code=status.HTTP_201_CREATED)
def create_computer_mission(payload: ComputerMissionCreate) -> dict[str, object]:
    return service.create(payload.model_dump())


@router.get("/computer-missions/{computer_mission_id}")
def get_computer_mission(computer_mission_id: str) -> dict[str, object]:
    try:
        return service.get(computer_mission_id)
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/computer-missions/{computer_mission_id}/analyze")
def analyze_computer_mission(computer_mission_id: str) -> dict[str, object]:
    try:
        return service.analyze(computer_mission_id)
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/computer-missions/{computer_mission_id}/diff")
def computer_mission_diff(computer_mission_id: str) -> dict[str, object]:
    try:
        mission = service.get(computer_mission_id)
        return {"status": mission["status"], "diff_content": mission["diff_content"], "approval_status": mission["approval_status"]}
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/computer-missions/{computer_mission_id}/approve")
def approve_computer_mission(computer_mission_id: str, payload: ComputerMissionApproval) -> dict[str, object]:
    try:
        return service.approve(computer_mission_id, payload.decision, payload.note)
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/computer-missions/{computer_mission_id}/execute")
def execute_computer_mission(computer_mission_id: str) -> dict[str, object]:
    try:
        return service.execute(computer_mission_id)
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/computer-missions/{computer_mission_id}/verification")
def computer_mission_verification(computer_mission_id: str) -> dict[str, object]:
    try:
        return service.verification(computer_mission_id)
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
