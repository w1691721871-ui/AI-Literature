from pydantic import BaseModel
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.paper_agent import (
    ConversationContextTooLongError,
    PaperAnalysisAgent,
    PaperNotFoundError,
    PaperTextTooLongError,
    TaskNotRecognizedError,
)

from app.services.llm_service import (
    LLMConfigurationError,
    LLMRequestError,
    analyze_paper,
)
from app.services.pdf_service import (
    InvalidPdfError,
    PdfTextExtractionError,
    extract_pdf_text,
)


app = FastAPI(title="AI Research Paper Analysis Agent")
paper_agent = PaperAnalysisAgent()

# Allow the local Vue page and the deployed Render frontend to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ai-literature-13.onrender.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FollowUpQuestion(BaseModel):
    """Request body for asking another question about an analyzed paper."""

    question: str


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _request, _error: RequestValidationError
) -> JSONResponse:
    """Keep malformed client requests understandable for beginners."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "请求参数不正确，请检查任务、问题和上传文件。"},
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple status to confirm that the service is running."""
    return {"status": "ok"}


@app.post("/analyze-paper")
async def analyze_uploaded_paper(file: UploadFile = File(...)) -> dict[str, str]:
    """Extract a PDF's text, then ask the LLM for a paper analysis."""
    filename = file.filename or ""
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件格式不正确，请上传 PDF 文件。",
        )

    try:
        paper_text = extract_pdf_text(await file.read())
    except InvalidPdfError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except PdfTextExtractionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    try:
        analysis = analyze_paper(paper_text)
    except LLMConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except LLMRequestError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return {"analysis": analysis}


@app.post("/agent/analyze-paper")
async def agent_analyze_paper(
    task: str = Form(...),
    file: UploadFile = File(...),
    scenario: str = Form("paper"),
    role: str = Form("researcher"),
) -> dict[str, object]:
    """Run the document-analysis Agent for an uploaded PDF and user task."""
    filename = file.filename or ""
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="文件格式不正确，请上传 PDF 文件。")

    try:
        return paper_agent.analyze_pdf(await file.read(), task, scenario, role)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except TaskNotRecognizedError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except InvalidPdfError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PdfTextExtractionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except PaperTextTooLongError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/agent/papers/{paper_id}/questions")
def ask_paper_question(paper_id: str, request: FollowUpQuestion) -> dict[str, object]:
    """Ask a follow-up question about a paper previously analyzed by the agent."""
    try:
        return paper_agent.answer_follow_up(paper_id, request.question)
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ConversationContextTooLongError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMRequestError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
