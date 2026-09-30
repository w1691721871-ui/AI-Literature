"""ResearchOS product routes, independent from existing paper and RAG APIs."""

import os

from fastapi import APIRouter, HTTPException, Response, status
from dotenv import load_dotenv
from sqlalchemy import func, select

from app.agent.research_master_agent import ResearchMasterAgent
from app.agent.research_brain import ResearchBrain
from app.agent.research_worker import ResearchWorker
from app.agent.research_operator_agent import ResearchOperatorAgent
from app.agent.research_computer_agent import ResearchComputerAgent
from app.agent.research_computer_operator_pro import ResearchComputerOperatorPro
from app.agent.research_computer_runtime_agent import ResearchComputerRuntimeAgent
from app.agent.research_autonomous_computer_agent import ResearchAutonomousComputerAgent
from app.agent.research_computer_use_agent import ResearchComputerUseAgent
from app.agent.research_workflow_agent import ResearchWorkflowAgent, WorkflowNotFoundError
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.research_project import ResearchProject
from app.schemas.researchos import (
    ResearchOSTaskRequest, ResearchValueRequest, WorkspaceCompleteRequest, WorkspaceReviewRequest, WorkflowCreateRequest,
)
from app.schemas.autonomous_research import AutonomousResearchRunRequest, AutonomousResearchRunResponse
from app.schemas.research_worker import ResearchWorkerRunRequest, ResearchWorkerRunResponse
from app.schemas.operator import OperatorApprovalRequest, OperatorTaskCreate
from app.schemas.computer import ComputerActionReview, ComputerTaskCreate
from app.schemas.computer_pro import AutonomousComputerTaskCreate, ComputerProTaskCreate, ComputerProjectMemoryCreate, ComputerRuntimeApproval, ComputerRuntimeTaskCreate, ComputerUseTaskCreate
from app.services.autonomous_computer_service import AutonomousComputerNotFoundError
from app.services.computer_intelligence_service import ComputerIntelligenceService
from app.services.product_experience_service import ProductExperienceService
from app.schemas.product_experience import OnboardingStepComplete
from app.schemas.fde_solution import SolutionProjectCreate, SolutionReviewRequest
from app.agent.fde_solution_agent import FDESolutionAgent
from app.services.fde_solution_service import FDESolutionService, SolutionNotFoundError
from app.schemas.research_project import (
    EnterpriseMatchRequest,
    ResearchProjectInput,
    ResearchProjectResponse,
)
from app.schemas.decision_loop import (
    KnowledgeStatusUpdate,
    ResearchActionCreate,
    ResearchActionResponse,
    ResearchActionUpdate,
    ResearchDecisionCreate,
    ResearchDecisionResponse,
    ResearchOutcomeCreate,
    ResearchOutcomeResponse,
    ResearchOutcomeUpdate,
)
from app.services.embedding_service import EmbeddingConfigurationError, EmbeddingRequestError
from app.services.llm_service import LLMConfigurationError, LLMRequestError
from app.services.database import SessionLocal, initialize_database
from app.services.evidence_center_service import EvidenceCenterService
from app.services.research_project_service import (
    ResearchProjectNotFoundError,
    ResearchProjectService,
)
from app.services.research_action_service import ResearchActionNotFoundError, ResearchActionService
from app.services.research_outcome_service import (
    ResearchOutcomeNotFoundError,
    ResearchOutcomeProjectNotFoundError,
    ResearchOutcomeSourceActionNotFoundError,
    ResearchOutcomeService,
)
from app.services.autonomous_research_run_service import AutonomousResearchRunNotFoundError
from app.services.research_worker_run_service import ResearchWorkerRunNotFoundError
from app.services.research_operator_service import OperatorTaskNotFoundError
from app.services.research_computer_service import ComputerActionNotFoundError, ComputerSessionNotFoundError
from app.services.workspace_service import WorkspaceNotFoundError, WorkspaceService
from app.services.research_workspace_intelligence_service import ResearchWorkspaceIntelligenceService
from app.services.research_deliverable_service import ResearchDeliverableService
from app.services.research_workspace_workflow_service import (
    ResearchWorkspaceWorkflowService, ReviewItemNotFoundError, WorkflowPermissionError,
)
from app.services.client_delivery_service import ClientDeliveryService
from app.services.researchos_diagnostic_service import ResearchOSDiagnosticService
from app.services.research_solution_delivery_service import ResearchSolutionDeliveryService
from app.services.research_copilot_service import ResearchCopilotService
from app.services.research_goal_memory_service import ResearchGoalMemoryService
from app.services.research_copilot_action_service import ResearchCopilotActionService, CopilotActionNotFoundError
from app.services.document_collaboration_service import DocumentCollaborationService, DocumentRevisionNotFoundError
from app.schemas.copilot import CopilotActionCreate, CopilotActionReview, DocumentCommentCreate
from app.schemas.enterprise import (KnowledgeScopeUpdate, MeetingCreate, OrganizationCreate, OrganizationMemberCreate,
                                    OrganizationProjectCreate, PermissionRequest, ProjectStatusUpdate)
from app.services.enterprise_collaboration_service import (EnterpriseCollaborationService,
                                                           EnterpriseNotFoundError, PermissionDeniedError)
from app.schemas.workspace import DeliveryExportRequest, TaskCreate, WorkspaceCreate
from app.memory.research_memory_service import ResearchMemoryService


router = APIRouter(prefix="/researchos", tags=["researchos"])
master_agent = ResearchMasterAgent()
research_brain = ResearchBrain(master_agent=master_agent)
research_worker = ResearchWorker()
research_operator = ResearchOperatorAgent()
research_computer = ResearchComputerAgent()
computer_operator_pro = ResearchComputerOperatorPro()
computer_runtime_agent = ResearchComputerRuntimeAgent(computer_operator_pro)
autonomous_computer_agent = ResearchAutonomousComputerAgent(computer_runtime_agent)
computer_use_agent = ResearchComputerUseAgent(autonomous_computer_agent)
computer_intelligence_service = ComputerIntelligenceService()
product_experience_service = ProductExperienceService()
fde_solution_service = FDESolutionService()
fde_solution_agent = FDESolutionAgent(fde_solution_service)
research_memory_service = ResearchMemoryService()
project_service = ResearchProjectService()
evidence_center_service = EvidenceCenterService()
research_action_service = ResearchActionService()
research_outcome_service = ResearchOutcomeService()
workspace_service = WorkspaceService()
workspace_intelligence_service = ResearchWorkspaceIntelligenceService()
research_workflow_agent = ResearchWorkflowAgent(master_agent=master_agent, workspace_service=workspace_intelligence_service)
research_deliverable_service = ResearchDeliverableService()
workspace_workflow_service = ResearchWorkspaceWorkflowService(workspace_intelligence_service)
client_delivery_service = ClientDeliveryService()
diagnostic_service = ResearchOSDiagnosticService()
solution_delivery_service = ResearchSolutionDeliveryService()
copilot_service = ResearchCopilotService(workspace_intelligence_service)
goal_memory_service = ResearchGoalMemoryService()
copilot_action_service = ResearchCopilotActionService()
document_collaboration_service = DocumentCollaborationService()
enterprise_collaboration_service = EnterpriseCollaborationService()


def _project_response(project: ResearchProject) -> ResearchProjectResponse:
    return ResearchProjectResponse(
        id=project.id,
        name=project.name,
        enterprise_requirement=project.enterprise_requirement,
        research_goal=project.research_goal,
        technology_route=project.technology_route,
        paper_plan=project.paper_plan,
        patent_plan=project.patent_plan,
        outcome_management=project.outcome_management,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/agents")
def list_researchos_agents() -> dict[str, object]:
    """Expose the orchestrator's available specialist roles to the UI."""
    return {"agents": master_agent.catalog()}


@router.post("/organizations")
def create_organization(payload: OrganizationCreate) -> dict[str, object]:
    return enterprise_collaboration_service.create_org(payload.name, payload.admin_name)


@router.get("/organizations/{organization_id}/members")
def list_organization_members(organization_id: str) -> list[dict[str, object]]:
    return enterprise_collaboration_service.members(organization_id)


@router.post("/organizations/{organization_id}/members", status_code=status.HTTP_201_CREATED)
def add_organization_member(organization_id: str, payload: OrganizationMemberCreate) -> dict[str, object]:
    try:
        return enterprise_collaboration_service.add_member(organization_id, payload.member_id, payload.display_name, payload.role)
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/organizations/{organization_id}/activity")
def list_organization_activity(organization_id: str) -> list[dict[str, object]]:
    return enterprise_collaboration_service.activity(organization_id)


@router.post("/organizations/{organization_id}/permissions/check")
def check_organization_permission(organization_id: str, payload: PermissionRequest) -> dict[str, object]:
    try:
        member = enterprise_collaboration_service.check(organization_id, payload.member_id, payload.permission)
        return {"allowed": True, "role": member.role, "permission": payload.permission}
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@router.get("/organizations/{organization_id}/projects")
def list_organization_projects(organization_id: str) -> list[dict[str, object]]:
    try:
        return enterprise_collaboration_service.list_projects(organization_id)
    except EnterpriseNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/organizations/{organization_id}/projects", status_code=status.HTTP_201_CREATED)
def create_organization_project(organization_id: str, payload: OrganizationProjectCreate) -> dict[str, object]:
    try:
        return enterprise_collaboration_service.create_project(organization_id, payload.model_dump())
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except EnterpriseNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/organizations/{organization_id}/projects/{project_id}/status")
def update_organization_project_status(organization_id: str, project_id: str, payload: ProjectStatusUpdate) -> dict[str, object]:
    try:
        return enterprise_collaboration_service.update_project_status(organization_id, project_id, payload.member_id, payload.status)
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except EnterpriseNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/organizations/{organization_id}/knowledge")
def list_team_knowledge(organization_id: str, member_id: str) -> list[dict[str, object]]:
    try:
        return enterprise_collaboration_service.team_knowledge(organization_id, member_id)
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@router.post("/organizations/{organization_id}/knowledge/scope")
def update_team_knowledge_scope(organization_id: str, payload: KnowledgeScopeUpdate) -> dict[str, object]:
    try:
        return enterprise_collaboration_service.set_knowledge_scope(organization_id, payload.model_dump())
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except EnterpriseNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/organizations/{organization_id}/meetings", status_code=status.HTTP_201_CREATED)
def create_enterprise_meeting(organization_id: str, payload: MeetingCreate) -> dict[str, object]:
    try:
        return enterprise_collaboration_service.create_meeting(organization_id, payload.model_dump())
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error


@router.get("/organizations/{organization_id}/dashboard")
def get_enterprise_dashboard(organization_id: str, member_id: str) -> dict[str, object]:
    try:
        return enterprise_collaboration_service.dashboard(organization_id, member_id)
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except EnterpriseNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/organizations/{organization_id}/delivery-package")
def get_enterprise_delivery_package(organization_id: str, member_id: str) -> dict[str, object]:
    try:
        return enterprise_collaboration_service.delivery_package(organization_id, member_id)
    except PermissionDeniedError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except EnterpriseNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/solution-scenarios")
def list_solution_scenarios() -> list[dict[str, object]]:
    """Return fixed, clearly-labelled customer scenario templates only."""
    return solution_delivery_service.list_scenarios()


@router.get("/solution-scenarios/{scenario_id}/blueprint")
def get_solution_blueprint(scenario_id: str) -> dict[str, object]:
    try:
        return solution_delivery_service.blueprint(scenario_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/solution-scenarios/{scenario_id}/demo-flow")
def get_solution_demo_flow(scenario_id: str) -> dict[str, object]:
    try:
        return solution_delivery_service.demo_flow(scenario_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/solution-roi")
def get_solution_roi() -> dict[str, object]:
    """Show observable assets plus non-numeric potential value indicators."""
    return solution_delivery_service.roi_dashboard()


@router.get("/solution-admin-overview")
def get_solution_admin_overview() -> dict[str, object]:
    return solution_delivery_service.admin_overview()


@router.get("/solution-scenarios/{scenario_id}/delivery-report")
def get_solution_delivery_report(scenario_id: str) -> dict[str, object]:
    try:
        return solution_delivery_service.delivery_report(scenario_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/diagnostics")
def get_researchos_diagnostics() -> dict[str, object]:
    """Return read-only workflow readiness; never fabricate research data."""
    return diagnostic_service.run()


@router.get("/autonomous-runs", response_model=list[AutonomousResearchRunResponse])
def list_autonomous_research_runs() -> list[dict[str, object]]:
    """List persisted user-visible autonomous execution summaries."""
    return research_brain.list_runs()


@router.get("/autonomous-runs/tools")
def list_autonomous_research_tools() -> dict[str, object]:
    """Expose the allow-listed research tools used by Research Brain."""
    return {"tools": research_brain.tool_catalog()}


@router.get("/research-worker/tools")
def list_research_worker_tools() -> dict[str, object]:
    """List Research Worker's explicit, safe execution tools."""
    return {"tools": research_worker.tool_catalog()}


@router.get("/operator/tools")
def list_research_operator_tools() -> dict[str, object]:
    """List the explicit allow-list used by the separate Operator layer."""
    return {"tools": research_operator.tool_catalog()}


@router.get("/computer/tools")
def list_computer_tools() -> dict[str, object]:
    return {"tools": research_computer.tool_catalog()}


@router.get("/computer/environment")
def get_computer_environment() -> dict[str, object]:
    """Return a read-only profile of approved local research/project roots."""
    return computer_operator_pro.environment()


@router.get("/computer/pro/catalog")
def get_computer_pro_catalog() -> dict[str, object]:
    return computer_operator_pro.catalog()


@router.post("/computer/runtime/tasks", status_code=status.HTTP_201_CREATED)
def create_computer_runtime_task(payload: ComputerRuntimeTaskCreate) -> dict[str, object]:
    try:
        return computer_runtime_agent.create(payload.goal, payload.execution_mode, payload.workspace_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/computer/runtime/{task_id}")
def get_computer_runtime_task(task_id: str) -> dict[str, object]:
    try:
        return computer_runtime_agent.get(task_id)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/computer/runtime/{task_id}/execute")
def execute_computer_runtime_task(task_id: str) -> dict[str, object]:
    try:
        return computer_runtime_agent.execute(task_id)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/runtime/{task_id}/timeline")
def get_computer_runtime_timeline(task_id: str) -> list[dict[str, object]]:
    try:
        return computer_runtime_agent.timeline(task_id)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/runtime/{task_id}/artifacts")
def get_computer_runtime_artifacts(task_id: str) -> list[dict[str, object]]:
    try:
        return computer_runtime_agent.artifacts(task_id)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/computer/runtime/{task_id}/approve")
def approve_computer_runtime_task(task_id: str, payload: ComputerRuntimeApproval) -> dict[str, object]:
    try:
        return computer_runtime_agent.approve(task_id, payload.reviewer_note)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/computer/runtime/{task_id}/retry")
def retry_computer_runtime_task(task_id: str) -> dict[str, object]:
    try:
        return computer_runtime_agent.retry(task_id)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/computer/autonomous/tasks", status_code=status.HTTP_201_CREATED)
def create_autonomous_computer_task(payload: AutonomousComputerTaskCreate) -> dict[str, object]:
    try:
        return autonomous_computer_agent.create(payload.goal, payload.execution_mode, payload.workspace_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/computer/autonomous/{runtime_id}")
def get_autonomous_computer_task(runtime_id: str) -> dict[str, object]:
    try: return autonomous_computer_agent.get(runtime_id)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/computer/autonomous/{runtime_id}/execute")
def execute_autonomous_computer_task(runtime_id: str) -> dict[str, object]:
    try: return autonomous_computer_agent.execute(runtime_id)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/autonomous/{runtime_id}/timeline")
def get_autonomous_computer_timeline(runtime_id: str) -> list[dict[str, object]]:
    try: return autonomous_computer_agent.timeline(runtime_id)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/autonomous/{runtime_id}/artifacts")
def get_autonomous_computer_artifacts(runtime_id: str) -> list[dict[str, object]]:
    try: return autonomous_computer_agent.artifacts(runtime_id)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/computer/autonomous/{runtime_id}/approve")
def approve_autonomous_computer_task(runtime_id: str, payload: ComputerRuntimeApproval) -> dict[str, object]:
    try: return autonomous_computer_agent.approve(runtime_id, payload.reviewer_note)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/computer/autonomous/{runtime_id}/retry")
def retry_autonomous_computer_task(runtime_id: str) -> dict[str, object]:
    try: return autonomous_computer_agent.retry(runtime_id)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/computer/use/tasks", status_code=status.HTTP_201_CREATED)
def create_computer_use_task(payload: ComputerUseTaskCreate) -> dict[str, object]:
    return computer_use_agent.create(payload.goal, payload.execution_mode, payload.workspace_id)


@router.post("/computer/use/{task_id}/start")
def start_computer_use_task(task_id: str) -> dict[str, object]:
    try: return computer_use_agent.start(task_id)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/use/{task_id}/timeline")
def computer_use_timeline(task_id: str) -> list[dict[str, object]]:
    try: return computer_use_agent.timeline(task_id)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/use/{task_id}/changes")
def computer_use_changes(task_id: str) -> list[dict[str, object]]:
    try: return computer_use_agent.changes.changes(task_id)
    except Exception as error: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/computer/use/{task_id}/artifacts")
def computer_use_artifacts(task_id: str) -> list[dict[str, object]]:
    try: return computer_use_agent.artifacts(task_id)
    except AutonomousComputerNotFoundError as error: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/computer/use/{task_id}/approve")
def approve_computer_use_task(task_id: str, payload: ComputerRuntimeApproval) -> dict[str, object]:
    try: return computer_use_agent.approve(task_id, payload.reviewer_note)
    except (AutonomousComputerNotFoundError, ValueError) as error: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/computer/use/{task_id}/rollback")
def rollback_computer_use_task(task_id: str) -> dict[str, object]:
    try: return computer_use_agent.rollback(task_id)
    except (AutonomousComputerNotFoundError, ValueError) as error: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/computer/use/{task_id}/activity")
def computer_use_activity(task_id: str) -> list[dict[str, object]]:
    return computer_intelligence_service.activities(task_id)


@router.get("/computer/skills")
def computer_skills() -> dict[str, object]:
    return {"skills": computer_intelligence_service.skills()}


@router.get("/computer/project-memory/{workspace_id}")
def computer_project_memory(workspace_id: str) -> list[dict[str, object]]:
    return computer_intelligence_service.memories(workspace_id)


@router.get("/computer/use/{task_id}/mission")
def computer_use_mission(task_id: str) -> dict[str, object]:
    mission = product_experience_service.mission(task_id)
    if mission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer Mission 不存在。")
    return mission


@router.post("/computer/project-memory/{workspace_id}", status_code=status.HTTP_201_CREATED)
def create_computer_project_memory(workspace_id: str, payload: ComputerProjectMemoryCreate) -> dict[str, object]:
    """Persist only bounded preferences and conventions; secret-like content is rejected."""
    try:
        return computer_intelligence_service.remember(workspace_id, payload.memory_type, payload.content)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/product/onboarding/{user_key}")
def product_onboarding(user_key: str) -> dict[str, object]:
    return product_experience_service.onboarding(user_key)


@router.post("/product/onboarding/{user_key}/complete")
def complete_product_onboarding(user_key: str, payload: OnboardingStepComplete) -> dict[str, object]:
    return product_experience_service.complete_onboarding_step(user_key, payload.step)


@router.get("/product/artifacts")
def product_artifacts() -> dict[str, object]:
    return {"artifacts": product_experience_service.artifacts()}


@router.get("/product/demos")
def product_demos() -> dict[str, object]:
    return {"demos": product_experience_service.demo_scenarios()}


@router.post("/solutions", status_code=status.HTTP_201_CREATED)
def create_solution_project(payload: SolutionProjectCreate) -> dict[str, object]:
    return fde_solution_service.create(payload.model_dump())


@router.get("/solutions")
def list_solution_projects() -> list[dict[str, object]]:
    return fde_solution_service.list()


@router.get("/solutions/{solution_id}")
def solution_project_detail(solution_id: str) -> dict[str, object]:
    try:
        return fde_solution_service.detail(solution_id)
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/solutions/{solution_id}/analyze")
def analyze_solution_requirements(solution_id: str) -> dict[str, object]:
    try:
        return fde_solution_agent.understand_requirements(solution_id)
    except (SolutionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/solutions/{solution_id}/blueprint")
def create_solution_blueprint(solution_id: str) -> dict[str, object]:
    try:
        return fde_solution_agent.prepare_solution(solution_id)
    except (SolutionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/solutions/{solution_id}/architecture")
def solution_architecture(solution_id: str) -> dict[str, object]:
    try:
        return fde_solution_service.architecture(solution_id)
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/solutions/{solution_id}/risks")
def solution_risks(solution_id: str) -> dict[str, object]:
    try:
        return fde_solution_service.risks(solution_id)
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/solutions/{solution_id}/review")
def review_solution(solution_id: str, payload: SolutionReviewRequest) -> dict[str, object]:
    try:
        return fde_solution_service.review(solution_id, payload.status, payload.reviewer_note)
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/solutions/{solution_id}/delivery-package")
def solution_delivery_package(solution_id: str) -> dict[str, object]:
    try:
        return fde_solution_service.delivery_package(solution_id)
    except (SolutionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/solutions/{solution_id}/computer-action")
def solution_computer_action(solution_id: str) -> dict[str, object]:
    try:
        return fde_solution_service.computer_actions(solution_id)
    except SolutionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/computer/pro/tasks", status_code=status.HTTP_201_CREATED)
def create_computer_pro_task(payload: ComputerProTaskCreate) -> dict[str, object]:
    try:
        return computer_operator_pro.create_task(payload.goal, payload.execution_mode, payload.workspace_id, payload.external_urls)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/computer/tasks/{task_id}/execute")
def execute_computer_pro_task(task_id: str) -> dict[str, object]:
    try:
        return computer_operator_pro.execute(task_id)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/tasks/{task_id}/events")
def get_computer_pro_events(task_id: str) -> list[dict[str, object]]:
    try:
        return computer_operator_pro.events(task_id)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/tasks/{task_id}/checkpoint")
def get_computer_task_checkpoint(task_id: str) -> dict[str, object]:
    try:
        checkpoint = computer_operator_pro.checkpoints.get(task_id)
        if checkpoint is None:
            raise ComputerSessionNotFoundError("该任务尚无执行检查点。")
        return checkpoint
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/computer/tasks/{task_id}/patches")
def list_computer_task_patches(task_id: str) -> list[dict[str, object]]:
    return computer_operator_pro.patches.list_for_task(task_id)


@router.get("/computer/memory")
def get_computer_memory() -> dict[str, object]:
    """Return metadata-only operator preferences; never source document text."""
    return research_computer.memory_snapshot()


@router.post("/computer/plan")
def preview_computer_task(request_body: ComputerTaskCreate) -> dict[str, object]:
    """Plan only.  This creates no session and invokes no research tool."""
    try:
        return research_computer.preview_task(request_body.user_goal)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/computer/tasks", status_code=status.HTTP_201_CREATED)
def create_computer_task(request_body: ComputerTaskCreate) -> dict[str, object]:
    try:
        return research_computer.create_task(request_body.user_goal, request_body.workspace_id, request_body.external_urls)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/computer/tasks")
def list_computer_tasks() -> list[dict[str, object]]:
    return research_computer.list()


@router.get("/computer/tasks/{task_id}")
def get_computer_task(task_id: str) -> dict[str, object]:
    try:
        return research_computer.get(task_id)
    except ComputerSessionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/computer/actions/{action_id}/approve")
def approve_computer_action(action_id: str, request_body: ComputerActionReview) -> dict[str, object]:
    try:
        # Existing endpoint remains compatible while adding P14's public event.
        return computer_operator_pro.approve(action_id, request_body.reviewer_note)
    except ComputerActionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/computer/actions/{action_id}/reject")
def reject_computer_action(action_id: str, request_body: ComputerActionReview) -> dict[str, object]:
    try:
        return computer_operator_pro.reject(action_id, request_body.reviewer_note)
    except ComputerActionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/operator/tasks", status_code=status.HTTP_201_CREATED)
def create_operator_task(request_body: OperatorTaskCreate) -> dict[str, object]:
    """Create and safely execute a bounded task until human approval is needed."""
    try:
        return research_operator.create_task(request_body.user_goal, request_body.workspace_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/operator/tasks")
def list_operator_tasks() -> list[dict[str, object]]:
    return research_operator.list_tasks()


@router.get("/operator/tasks/{task_id}")
def get_operator_task(task_id: str) -> dict[str, object]:
    try:
        return research_operator.get_task(task_id)
    except OperatorTaskNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/operator/tasks/{task_id}/approve")
def approve_operator_task(task_id: str, request_body: OperatorApprovalRequest) -> dict[str, object]:
    try:
        return research_operator.approve(task_id, request_body.reviewer_note)
    except OperatorTaskNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/operator/tasks/{task_id}/reject")
def reject_operator_task(task_id: str, request_body: OperatorApprovalRequest) -> dict[str, object]:
    try:
        return research_operator.reject(task_id, request_body.reviewer_note)
    except OperatorTaskNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/research-worker/run", response_model=ResearchWorkerRunResponse, status_code=status.HTTP_201_CREATED)
def run_research_worker(request_body: ResearchWorkerRunRequest) -> dict[str, object]:
    """Execute a bounded research-support task without altering decision-loop entities."""
    try:
        return research_worker.run(request_body.goal)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/research-worker/{run_id}", response_model=ResearchWorkerRunResponse)
def get_research_worker_run(run_id: str) -> dict[str, object]:
    try:
        return research_worker.get_run(run_id)
    except ResearchWorkerRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-worker/{run_id}/timeline")
def get_research_worker_timeline(run_id: str) -> list[dict[str, object]]:
    """Return the user-visible Agent Loop timeline, never hidden model reasoning."""
    try:
        return research_worker.timeline(run_id)
    except ResearchWorkerRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-worker/{run_id}/context")
def get_research_worker_context(run_id: str) -> dict[str, object]:
    """Return the task-scoped context summary; never raw files or model reasoning."""
    try:
        return research_worker.context(run_id)
    except ResearchWorkerRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/workspaces")
def list_research_workspaces() -> list[dict[str, object]]:
    """List lightweight organization spaces; roles are display-only without login."""
    return workspace_service.list()


@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
def create_research_workspace(request_body: WorkspaceCreate) -> dict[str, object]:
    return workspace_service.create(request_body.name, request_body.member_roles)


@router.get("/tasks")
def list_research_tasks(workspace_id: str | None = None) -> list[dict[str, object]]:
    try:
        return workspace_service.list_tasks(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/workspaces/{workspace_id}/tasks", status_code=status.HTTP_201_CREATED)
def create_research_task(workspace_id: str, request_body: TaskCreate) -> dict[str, object]:
    try:
        return workspace_service.create_task(workspace_id, request_body.model_dump())
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/agent-monitor")
def get_agent_monitor() -> dict[str, object]:
    return workspace_service.monitor()


@router.get("/client-delivery/{run_id}")
def get_client_delivery_preview(run_id: str) -> dict[str, object]:
    try:
        return client_delivery_service.preview(research_worker.get_run(run_id))
    except ResearchWorkerRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/client-delivery/export")
def export_client_delivery(request_body: DeliveryExportRequest) -> dict[str, str]:
    try:
        return client_delivery_service.export_pdf(research_worker.get_run(request_body.worker_run_id))
    except ResearchWorkerRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-memory")
def get_research_memory() -> dict[str, object]:
    """Return organization memory separately from document knowledge evidence."""
    return research_memory_service.get_lab_profile()


@router.post("/research-memory/refresh")
def refresh_research_memory() -> dict[str, object]:
    """Rebuild factual lab memory from current local metadata and task history."""
    return research_memory_service.refresh_lab_profile()


@router.get("/autonomous-runs/{run_id}", response_model=AutonomousResearchRunResponse)
def get_autonomous_research_run(run_id: str) -> dict[str, object]:
    try:
        return research_brain.get_run(run_id)
    except AutonomousResearchRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/autonomous-runs", response_model=AutonomousResearchRunResponse, status_code=status.HTTP_201_CREATED)
def run_autonomous_research(request_body: AutonomousResearchRunRequest) -> dict[str, object]:
    """Run the bounded Research Brain without changing existing task endpoints."""
    try:
        return research_brain.run(
            request_body.goal,
            request_body.paper_ids,
            request_body.generate_docx,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except EmbeddingRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.get("/overview")
def get_researchos_overview() -> dict[str, object]:
    """Return honest lab-knowledge counters without pretending other assets exist."""
    initialize_database()
    session = SessionLocal()
    try:
        paper_count = session.scalar(select(func.count(Paper.paper_id))) or 0
        chunk_count = session.scalar(select(func.count(PaperChunk.id))) or 0
        ready_count = session.scalar(
            select(func.count(Paper.paper_id)).where(Paper.quality_status.in_(("indexed", "ready")))
        ) or 0
    finally:
        session.close()
    return {
        "workspace_name": "ResearchOS 科研空间",
        "paper_count": paper_count,
        "knowledge_chunk_count": chunk_count,
        "ready_paper_count": ready_count,
        "asset_boundary": "当前版本已接入 PDF 论文资料；专利、实验报告与项目资料入口为后续扩展方向。",
    }


@router.get("/system-status")
def get_system_status() -> dict[str, object]:
    """Return safe local readiness signals without sending a model request.

    This is deliberately a configuration and data-index check. It must not
    consume model quota or expose API keys as part of a status page.
    """
    initialize_database()
    load_dotenv()
    session = SessionLocal()
    try:
        paper_count = session.scalar(select(func.count(Paper.paper_id))) or 0
        chunk_count = session.scalar(select(func.count(PaperChunk.id))) or 0
        ready_count = session.scalar(
            select(func.count(Paper.paper_id)).where(Paper.quality_status.in_(("indexed", "ready")))
        ) or 0
    finally:
        session.close()

    model_configured = bool(os.getenv("DASHSCOPE_API_KEY"))
    return {
        "version": "ResearchOS v3.0",
        "platform_name": "AI科研创新决策平台",
        "services": [
            {
                "id": "knowledge_base",
                "name": "知识库服务",
                "status": "ready" if paper_count else "empty",
                "detail": f"已入库 {paper_count} 份资料，包含 {chunk_count} 个知识片段。",
            },
            {
                "id": "agent_service",
                "name": "Agent 服务",
                "status": "ready",
                "detail": f"Research Master 与 {len(master_agent.catalog())} 个专项 Agent 已加载。",
            },
            {
                "id": "model_service",
                "name": "模型服务",
                "status": "configured" if model_configured else "not_configured",
                "detail": "模型配置已检测，不执行实时调用。" if model_configured else "未检测到模型配置，实际分析不可用。",
            },
            {
                "id": "data_index",
                "name": "数据索引",
                "status": "ready" if ready_count else "empty",
                "detail": f"{ready_count} 份资料已完成索引并可参与知识检索。",
            },
        ],
        "boundary_note": "状态中心不发起模型调用，显示的是本地配置和知识库索引状态，不代表外部模型服务的实时可用性。",
    }


@router.get("/evidence")
def list_research_evidence(limit: int = 24) -> dict[str, object]:
    """List short, factual knowledge-base excerpts for the Evidence Center."""
    items = evidence_center_service.list_evidence(limit)
    return {
        "items": items,
        "boundary_note": "证据卡仅展示已上传资料的章节级片段，不等同于精准页码引用，也不代表资料外的科研事实。",
    }


@router.get("/bi")
def get_research_bi() -> dict[str, object]:
    """Return factual, small-scale BI indicators from locally stored assets."""
    initialize_database()
    session = SessionLocal()
    try:
        type_rows = list(session.execute(
            select(Paper.document_type, func.count(Paper.paper_id)).group_by(Paper.document_type)
        ))
        latest_titles = list(session.scalars(
            select(Paper.title).order_by(Paper.updated_at.desc()).limit(5)
        ))
        paper_count = session.scalar(select(func.count(Paper.paper_id))) or 0
        chunk_count = session.scalar(select(func.count(PaperChunk.id))) or 0
    finally:
        session.close()
    projects = project_service.list_projects()
    planned_outcomes = sum(1 for project in projects if project.paper_plan or project.patent_plan or project.outcome_management)
    radar_value = min(100, paper_count * 15 + chunk_count // 8)
    return {
        "asset_distribution": [
            {"document_type": document_type, "count": count}
            for document_type, count in type_rows
        ],
        "research_assets": {"papers": paper_count, "knowledge_chunks": chunk_count, "projects": len(projects)},
        "latest_assets": latest_titles,
        "technology_roadmap": ["资料入库", "知识检索", "趋势与创新辅助", "项目成果规划"],
        "outcome_funnel": [
            {"stage": "科研资料", "count": paper_count},
            {"stage": "知识索引", "count": chunk_count},
            {"stage": "科研项目", "count": len(projects)},
            {"stage": "已规划成果", "count": planned_outcomes},
        ],
        "capability_radar": [
            {"name": "知识资产沉淀", "score": radar_value},
            {"name": "资料可检索性", "score": min(100, chunk_count * 5)},
            {"name": "项目规划覆盖", "score": min(100, len(projects) * 25)},
            {"name": "成果规划覆盖", "score": min(100, planned_outcomes * 30)},
        ],
        "trend_boundary": "研究热点与趋势需要基于已上传资料运行 Research Master 任务生成；本驾驶舱不虚构外部实时统计。",
    }


@router.post("/value-assessment")
def assess_research_value(request_body: ResearchValueRequest) -> dict[str, object]:
    try:
        return master_agent.assess_research_value(request_body.research_goal, request_body.paper_ids)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except EmbeddingRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.post("/lab-profile/generate")
def generate_lab_profile() -> dict[str, object]:
    try:
        return master_agent.generate_lab_profile()
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except EmbeddingRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.get("/projects", response_model=list[ResearchProjectResponse])
def list_research_projects() -> list[ResearchProjectResponse]:
    return [_project_response(project) for project in project_service.list_projects()]


@router.post("/projects", response_model=ResearchProjectResponse, status_code=status.HTTP_201_CREATED)
def create_research_project(request_body: ResearchProjectInput) -> ResearchProjectResponse:
    return _project_response(project_service.create_project(request_body.model_dump()))


@router.get("/projects/{project_id}", response_model=ResearchProjectResponse)
def get_research_project(project_id: str) -> ResearchProjectResponse:
    try:
        return _project_response(project_service.get_project(project_id))
    except ResearchProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.put("/projects/{project_id}", response_model=ResearchProjectResponse)
def update_research_project(project_id: str, request_body: ResearchProjectInput) -> ResearchProjectResponse:
    try:
        return _project_response(project_service.update_project(project_id, request_body.model_dump()))
    except ResearchProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_research_project(project_id: str) -> Response:
    try:
        project_service.delete_project(project_id)
    except ResearchProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/actions", response_model=ResearchActionResponse, status_code=status.HTTP_201_CREATED)
def create_research_action(request_body: ResearchActionCreate) -> dict[str, object]:
    """Save a user-approved next action with its explicit Agent/result context."""
    return research_action_service.create_action(request_body)


@router.get("/actions", response_model=list[ResearchActionResponse])
def list_research_actions(project_id: str | None = None) -> list[dict[str, object]]:
    return research_action_service.list_actions(project_id)


@router.put("/actions/{action_id}", response_model=ResearchActionResponse)
def update_research_action(action_id: str, request_body: ResearchActionUpdate) -> dict[str, object]:
    try:
        return research_action_service.update_action(action_id, request_body)
    except ResearchActionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该科研行动") from error


@router.post("/decisions", response_model=ResearchDecisionResponse)
def save_research_decision(request_body: ResearchDecisionCreate) -> dict[str, object]:
    """Record the user's adoption, modification, or rejection of an AI suggestion."""
    try:
        return research_action_service.save_decision(request_body)
    except ResearchActionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到需要确认的科研行动") from error


@router.get("/decisions", response_model=list[ResearchDecisionResponse])
def list_research_decisions(project_id: str | None = None) -> list[dict[str, object]]:
    return research_action_service.list_decisions(project_id)


@router.post("/projects/{project_id}/outcomes", response_model=ResearchOutcomeResponse, status_code=status.HTTP_201_CREATED)
def create_project_outcome(project_id: str, request_body: ResearchOutcomeCreate) -> dict[str, object]:
    try:
        return research_outcome_service.create_outcome(project_id, request_body)
    except ResearchOutcomeProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该科研项目") from error
    except ResearchOutcomeSourceActionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="来源行动不存在或不属于该项目") from error


@router.get("/projects/{project_id}/outcomes", response_model=list[ResearchOutcomeResponse])
def list_project_outcomes(project_id: str) -> list[dict[str, object]]:
    try:
        project_service.get_project(project_id)
        return research_outcome_service.list_outcomes(project_id)
    except ResearchProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该科研项目") from error


@router.put("/outcomes/{outcome_id}", response_model=ResearchOutcomeResponse)
def update_project_outcome(outcome_id: str, request_body: ResearchOutcomeUpdate) -> dict[str, object]:
    try:
        return research_outcome_service.update_outcome(outcome_id, request_body)
    except ResearchOutcomeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该科研成果") from error
    except ResearchOutcomeSourceActionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="来源行动不存在") from error


@router.delete("/outcomes/{outcome_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_outcome(outcome_id: str) -> Response:
    try:
        research_outcome_service.delete_outcome(outcome_id)
    except ResearchOutcomeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该科研成果") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/outcomes/{outcome_id}/knowledge-status", response_model=ResearchOutcomeResponse)
def update_outcome_knowledge_status(outcome_id: str, request_body: KnowledgeStatusUpdate) -> dict[str, object]:
    """Record asset organization readiness; this does not trigger RAG indexing."""
    try:
        return research_outcome_service.update_knowledge_status(outcome_id, request_body)
    except ResearchOutcomeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该科研成果") from error


@router.post("/projects/{project_id}/match")
def match_project_requirement(project_id: str, request_body: EnterpriseMatchRequest) -> dict[str, object]:
    """Run the Project Agent against existing lab knowledge for one project."""
    try:
        project_service.get_project(project_id)
        return master_agent.match_enterprise_requirement(
            request_body.enterprise_requirement,
            request_body.paper_ids,
        )
    except ResearchProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except EmbeddingRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.post("/tasks/plan")
def plan_researchos_task(request_body: ResearchOSTaskRequest) -> dict[str, object]:
    """Preview a deterministic Master-Agent plan before a model call."""
    try:
        return master_agent.plan_task(request_body.user_goal, request_body.selected_agents)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/workflows", status_code=status.HTTP_201_CREATED)
def create_research_workflow(request_body: WorkflowCreateRequest) -> dict[str, object]:
    """Generate a deterministic workflow preview; no research conclusion is generated."""
    try:
        return research_workflow_agent.create(request_body.goal, request_body.workspace_id, request_body.workflow_type)
    except (ValueError, WorkspaceNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/workflows")
def list_research_workflows(workspace_id: str | None = None) -> list[dict[str, object]]:
    return research_workflow_agent.list(workspace_id)


@router.get("/workflows/{workflow_id}")
def get_research_workflow(workflow_id: str) -> dict[str, object]:
    try:
        return research_workflow_agent.get(workflow_id)
    except WorkflowNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/workflows/{workflow_id}/events")
def get_research_workflow_events(workflow_id: str) -> list[dict[str, object]]:
    try:
        return research_workflow_agent.events(workflow_id)
    except WorkflowNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/workflows/{workflow_id}/execute")
def execute_research_workflow(workflow_id: str, request_body: WorkflowCreateRequest) -> dict[str, object]:
    """Execute existing bounded agents only after the real knowledge-base guard passes."""
    try:
        return research_workflow_agent.execute(workflow_id, request_body.paper_ids)
    except WorkflowNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except EmbeddingRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.post("/tasks/run")
def run_researchos_task(request_body: ResearchOSTaskRequest) -> dict[str, object]:
    """Run the evidence-grounded ResearchOS orchestration workflow."""
    try:
        result = master_agent.run_task(
            request_body.user_goal,
            request_body.selected_agents,
            request_body.paper_ids,
        )
        workspace = workspace_intelligence_service.resolve_or_create(
            request_body.user_goal, request_body.workspace_id
        )
        result["research_workspace"] = workspace_intelligence_service.save_run(
            str(workspace["workspace_id"]), result
        )
        return result
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except EmbeddingConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except EmbeddingRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-workspaces")
def list_research_workspaces() -> list[dict[str, object]]:
    """List persistent Research Master workspaces and their latest run state."""
    return workspace_intelligence_service.list_workspaces()


@router.get("/research-workspaces/{workspace_id}")
def get_research_workspace(workspace_id: str) -> dict[str, object]:
    try:
        return workspace_intelligence_service.get_workspace(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/resume")
def resume_research_workspace(workspace_id: str) -> dict[str, object]:
    try:
        return workspace_intelligence_service.resume(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/quality")
def get_research_workspace_quality(workspace_id: str) -> dict[str, object]:
    try:
        return workspace_intelligence_service.quality_metrics(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/copilot")
def get_workspace_copilot(workspace_id: str) -> dict[str, object]:
    try:
        return copilot_service.intelligence(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/copilot/memory")
def get_research_goal_memory() -> dict[str, object]:
    return goal_memory_service.get()


@router.get("/copilot/actions")
def list_copilot_actions(workspace_id: str | None = None) -> list[dict[str, object]]:
    return copilot_action_service.list(workspace_id)


@router.post("/copilot/actions")
def create_copilot_action(payload: CopilotActionCreate) -> dict[str, object]:
    return copilot_action_service.create(payload.model_dump())


@router.post("/copilot/actions/{action_id}/review")
def review_copilot_action(action_id: str, payload: CopilotActionReview) -> dict[str, object]:
    try:
        return copilot_action_service.review(action_id, payload.status)
    except CopilotActionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/document-versions")
def list_document_versions(workspace_id: str) -> list[dict[str, object]]:
    return document_collaboration_service.list(workspace_id)


@router.post("/document-versions/{revision_id}/comment")
def comment_document_version(revision_id: str, payload: DocumentCommentCreate) -> dict[str, object]:
    try:
        return document_collaboration_service.comment(revision_id, payload.reviewer_comment)
    except DocumentRevisionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/decision-candidate")
def get_research_workspace_decision_candidate(workspace_id: str) -> dict[str, object]:
    try:
        return workspace_intelligence_service.decision_candidate(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/research-workspaces/{workspace_id}/deliverables/{deliverable_type}")
def generate_research_workspace_deliverable(workspace_id: str, deliverable_type: str) -> dict[str, object]:
    try:
        snapshot = workspace_intelligence_service.get_workspace(workspace_id)
        decision = workspace_intelligence_service.decision_candidate(workspace_id)
        return research_deliverable_service.generate(snapshot, decision, deliverable_type)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/members")
def get_research_workspace_members(workspace_id: str) -> list[dict[str, object]]:
    try:
        return workspace_workflow_service.members(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/workflow")
def get_research_workspace_workflow(workspace_id: str) -> dict[str, object]:
    try:
        return workspace_workflow_service.workflow(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/reviews")
def get_research_workspace_reviews(workspace_id: str) -> list[dict[str, object]]:
    try:
        return workspace_workflow_service.review_items(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/research-workspaces/{workspace_id}/reviews/{item_id}")
def review_research_workspace_item(
    workspace_id: str, item_id: str, payload: WorkspaceReviewRequest
) -> dict[str, object]:
    try:
        return workspace_workflow_service.submit_review(
            workspace_id, item_id, payload.reviewer_role, payload.status, payload.reviewer_note
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ReviewItemNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (WorkflowPermissionError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/research-workspaces/{workspace_id}/evidence-graph")
def get_research_workspace_evidence_graph(workspace_id: str) -> dict[str, object]:
    try:
        return workspace_workflow_service.evidence_graph(workspace_id)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/research-workspaces/{workspace_id}/research-brief")
def generate_research_brief(workspace_id: str) -> dict[str, object]:
    try:
        snapshot = workspace_intelligence_service.get_workspace(workspace_id)
        decision = workspace_intelligence_service.decision_candidate(workspace_id)
        brief = research_deliverable_service.generate(snapshot, decision, "research_brief")
        if brief.get("status") == "draft":
            workspace_workflow_service.mark_deliverable_draft(workspace_id, brief)
        return brief
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (WorkflowPermissionError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/research-workspaces/{workspace_id}/complete")
def complete_research_workspace(workspace_id: str, payload: WorkspaceCompleteRequest) -> dict[str, object]:
    try:
        return workspace_workflow_service.complete(workspace_id, payload.role)
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (WorkflowPermissionError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
