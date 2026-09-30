"""Compatibility API surface for the FDE Solution Studio.

This router intentionally delegates to the review-first service.  It does not
create a second solution system or bypass Human Review.
"""

from fastapi import APIRouter, HTTPException, status

from app.agent.fde_solution_agent import FDESolutionAgent
from app.schemas.fde_solution import FDEProjectCreate, SolutionReviewRequest
from app.services.fde_solution_service import FDESolutionService, SolutionNotFoundError


router = APIRouter(prefix="/api/fde", tags=["fde-solution"])
service = FDESolutionService()
agent = FDESolutionAgent(service)


def _project_alias(project: dict[str, object]) -> dict[str, object]:
    return {**project, "name": project["title"]}


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: FDEProjectCreate) -> dict[str, object]:
    return _project_alias(service.create({"title": payload.name, "customer_need": payload.customer_need,
                                          "industry": payload.industry, "objective": payload.objective}))


@router.get("/projects")
def list_projects() -> list[dict[str, object]]:
    return [_project_alias(project) for project in service.list()]


@router.get("/projects/{project_id}/requirements")
def project_requirements(project_id: str) -> dict[str, object]:
    try:
        project = service.detail(project_id)
        return {"project": _project_alias(project), "requirements": project["requirements"]}
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/projects/{project_id}/blueprint")
def project_blueprint(project_id: str) -> dict[str, object]:
    try:
        return agent.prepare_solution(project_id)
    except (SolutionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/projects/{project_id}/risk")
def project_risk(project_id: str) -> dict[str, object]:
    try:
        return service.risks(project_id)
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/projects/{project_id}/review")
def project_review(project_id: str, payload: SolutionReviewRequest) -> dict[str, object]:
    try:
        return _project_alias(service.review(project_id, payload.status, payload.reviewer_note))
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/projects/{project_id}/delivery")
def project_delivery(project_id: str) -> dict[str, object]:
    try:
        return service.delivery_package(project_id)
    except (SolutionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/projects/{project_id}/computer-action")
def project_computer_action(project_id: str) -> dict[str, object]:
    try:
        return service.computer_actions(project_id)
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/projects/{project_id}/versions")
def project_versions(project_id: str) -> dict[str, object]:
    try:
        return service.versions(project_id)
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
