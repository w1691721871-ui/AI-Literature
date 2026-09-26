"""ResearchOS product routes, independent from existing paper and RAG APIs."""

import os

from fastapi import APIRouter, HTTPException, Response, status
from dotenv import load_dotenv
from sqlalchemy import func, select

from app.agent.research_master_agent import ResearchMasterAgent
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.research_project import ResearchProject
from app.schemas.researchos import ResearchOSTaskRequest, ResearchValueRequest
from app.schemas.research_project import (
    EnterpriseMatchRequest,
    ResearchProjectInput,
    ResearchProjectResponse,
)
from app.services.embedding_service import EmbeddingConfigurationError, EmbeddingRequestError
from app.services.llm_service import LLMConfigurationError, LLMRequestError
from app.services.database import SessionLocal, initialize_database
from app.services.evidence_center_service import EvidenceCenterService
from app.services.research_project_service import (
    ResearchProjectNotFoundError,
    ResearchProjectService,
)


router = APIRouter(prefix="/researchos", tags=["researchos"])
master_agent = ResearchMasterAgent()
project_service = ResearchProjectService()
evidence_center_service = EvidenceCenterService()


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
        "version": "ResearchOS v1.0",
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


@router.post("/tasks/run")
def run_researchos_task(request_body: ResearchOSTaskRequest) -> dict[str, object]:
    """Run the evidence-grounded ResearchOS orchestration workflow."""
    try:
        return master_agent.run_task(
            request_body.user_goal,
            request_body.selected_agents,
            request_body.paper_ids,
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
