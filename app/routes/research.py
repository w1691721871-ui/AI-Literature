"""Research paper-library routes, kept separate from the existing Agent routes."""

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status

from app.agent.paper_agent import (
    PaperTextTooLongError,
    TaskNotRecognizedError,
)
from app.agent.research_agent import ResearchAgent
from app.schemas.paper import (
    LibraryPaperAnalysisRequest,
    PaperDetail,
    PaperListItem,
)
from app.schemas.research import (
    ResearchOverview,
    ResearchReportDetail,
    ResearchReportListItem,
)
from app.schemas.rag import (
    RagQueryHistoryDetail,
    RagQueryHistoryItem,
    ResearchQuestionRequest,
    ResearchQuestionResponse,
    ResearchReportRequest,
    ResearchReportResponse,
)
from app.services.analysis_record_service import (
    AnalysisRecordNotFoundError,
    AnalysisRecordService,
)
from app.services.database import PROJECT_ROOT
from app.services.document_store import read_pdf_file
from app.services.embedding_service import (
    EmbeddingConfigurationError,
    EmbeddingRequestError,
)
from app.services.llm_service import LLMConfigurationError, LLMRequestError
from app.services.paper_library_service import (
    LibraryPaperNotFoundError,
    PaperLibraryService,
)
from app.services.rag_query_record_service import (
    RagQueryRecordNotFoundError,
    RagQueryRecordService,
)
from app.services.pdf_service import InvalidPdfError, PdfTextExtractionError
from app.models.paper_chunk import PaperChunk
from app.services.database import SessionLocal
from sqlalchemy import func, select


router = APIRouter(prefix="/research", tags=["research-library"])
paper_library_service = PaperLibraryService()
analysis_record_service = AnalysisRecordService()
research_agent = ResearchAgent()
rag_query_record_service = RagQueryRecordService()


def _relative_file_path(file_path: str) -> str:
    """Avoid exposing the server's absolute filesystem path through the public API."""
    path = Path(file_path)
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return path.name


def _list_item(paper) -> PaperListItem:
    """Map a model to a safe response that does not include text_content."""
    session = SessionLocal()
    try:
        chunk_count = session.scalar(
            select(func.count(PaperChunk.id)).where(PaperChunk.paper_id == paper.paper_id)
        ) or 0
    finally:
        session.close()
    return PaperListItem(
        paper_id=paper.paper_id,
        title=paper.title,
        filename=paper.filename,
        upload_time=paper.upload_time,
        analysis_status=paper.analysis_status,
        document_type=paper.document_type,
        quality_status=paper.quality_status,
        chunk_count=chunk_count,
        updated_at=paper.updated_at,
        text_length=len(paper.text_content),
    )


def _report_list_item(record, paper_title: str) -> ResearchReportListItem:
    """Map persisted report metadata without returning stored result JSON yet."""
    return ResearchReportListItem(
        id=record.id,
        paper_id=record.paper_id,
        paper_title=paper_title,
        task=record.task,
        scenario=record.scenario,
        role=record.role,
        source_type=record.source_type,
        created_at=record.created_at,
    )


@router.post("/questions", response_model=ResearchQuestionResponse)
def ask_research_question(request_body: ResearchQuestionRequest) -> ResearchQuestionResponse:
    """Answer a multi-paper research question through the independent RAG Agent."""
    try:
        result = research_agent.answer_question(
            request_body.question,
            request_body.paper_ids,
        )
        return ResearchQuestionResponse(**result)
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


@router.post("/generate-report", response_model=ResearchReportResponse)
def generate_research_report_endpoint(request_body: ResearchReportRequest) -> ResearchReportResponse:
    """Generate a grounded cross-paper report through the independent ResearchAgent."""
    try:
        return ResearchReportResponse(**research_agent.generate_report(
            request_body.report_type,
            request_body.paper_ids,
        ))
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


@router.get("/questions/history", response_model=list[RagQueryHistoryItem])
def list_rag_question_history() -> list[RagQueryHistoryItem]:
    """List persisted knowledge-question history without duplicating source payloads."""
    return [
        RagQueryHistoryItem(
            id=record.id,
            question=record.question,
            answer=record.answer,
            task_type=record.task_type,
            created_at=record.created_at,
        )
        for record in rag_query_record_service.list_questions()
    ]


@router.get("/questions/history/{record_id}", response_model=RagQueryHistoryDetail)
def get_rag_question_history(record_id: str) -> RagQueryHistoryDetail:
    """Restore a saved RAG answer and citation cards for the knowledge-QA page."""
    try:
        record, sources, paper_ids = rag_query_record_service.get(record_id)
        return RagQueryHistoryDetail(
            id=record.id,
            question=record.question,
            answer=record.answer,
            task_type=record.task_type,
            created_at=record.created_at,
            sources=sources,
            paper_ids=paper_ids,
        )
    except RagQueryRecordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get("/overview", response_model=ResearchOverview)
def get_research_overview() -> ResearchOverview:
    """Return small research-space counters for the product dashboard."""
    return ResearchOverview(**analysis_record_service.get_overview())


@router.get("/reports", response_model=list[ResearchReportListItem])
def list_research_reports() -> list[ResearchReportListItem]:
    """List saved report history without returning full Agent payloads."""
    return [
        _report_list_item(record, paper_title)
        for record, paper_title in analysis_record_service.list_analysis_records()
    ]


@router.get("/reports/{record_id}", response_model=ResearchReportDetail)
def get_research_report(record_id: str) -> ResearchReportDetail:
    """Restore one saved Agent response for the existing assistant result area."""
    try:
        record, paper_title, analysis_result = analysis_record_service.get_analysis_record(record_id)
    except AnalysisRecordNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    return ResearchReportDetail(
        **_report_list_item(record, paper_title).model_dump(),
        analysis_result=analysis_result,
    )


@router.post("/papers/upload", response_model=PaperListItem, status_code=status.HTTP_201_CREATED)
async def upload_research_paper(
    file: UploadFile = File(...),
    document_type: str = Form("paper"),
) -> PaperListItem:
    """Save a source PDF, extract text via the shared parser, and create a library record."""
    filename = file.filename or ""
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件格式不正确，请上传 PDF 文件。",
        )
    allowed_document_types = {"paper", "patent", "experiment_report", "project_material"}
    if document_type not in allowed_document_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的科研资料类型。")

    try:
        paper = paper_library_service.save_uploaded_paper(
            await file.read(), filename, document_type
        )
        return _list_item(paper)
    except InvalidPdfError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except PdfTextExtractionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("/papers", response_model=list[PaperListItem])
def list_research_papers() -> list[PaperListItem]:
    """List stored research papers without returning their extracted full text."""
    return [_list_item(paper) for paper in paper_library_service.list_papers()]


@router.get("/papers/{paper_id}", response_model=PaperDetail)
def get_research_paper(paper_id: str) -> PaperDetail:
    """Return safe paper metadata and text length, never the full text_content field."""
    try:
        paper = paper_library_service.get_paper(paper_id)
    except LibraryPaperNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return PaperDetail(
        **_list_item(paper).model_dump(),
        file_path=_relative_file_path(paper.file_path),
    )


@router.post("/papers/{paper_id}/analyze")
def analyze_library_paper(
    paper_id: str,
    request_body: LibraryPaperAnalysisRequest,
    request: Request,
) -> dict[str, object]:
    """Analyze a stored PDF through the existing shared Agent and preserve its ID."""
    try:
        paper = paper_library_service.get_paper(paper_id)
        file_content = read_pdf_file(paper.file_path)
        paper_agent = request.app.state.paper_agent
        analysis_result = paper_agent.analyze_pdf(
            file_content=file_content,
            task=request_body.task,
            scenario=request_body.scenario,
            role=request_body.role,
            paper_id=paper_id,
        )
        analysis_record_service.save_analysis_record(
            paper_id=paper_id,
            task=request_body.task,
            scenario=request_body.scenario,
            role=request_body.role,
            analysis_result=analysis_result,
            source_type="library",
        )
        return analysis_result
    except LibraryPaperNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except TaskNotRecognizedError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except InvalidPdfError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except PdfTextExtractionError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except PaperTextTooLongError as error:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.delete("/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_research_paper(paper_id: str) -> Response:
    """Delete both the library record and its safely validated source PDF."""
    try:
        paper_library_service.delete_paper(paper_id)
    except LibraryPaperNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
