"""Utilities for validating PDFs and extracting their text."""

from io import BytesIO
import logging

from pypdf import PdfReader


logger = logging.getLogger(__name__)


class InvalidPdfError(Exception):
    """Raised when uploaded bytes are not a readable PDF."""


class PdfTextExtractionError(Exception):
    """Raised when a readable PDF does not provide extractable text."""


def extract_pdf_text(file_content: bytes) -> str:
    """Extract all available text from a PDF uploaded into memory."""
    if not file_content:
        raise InvalidPdfError("上传文件为空，请选择有效的 PDF 文件。")

    if not file_content.startswith(b"%PDF-"):
        raise InvalidPdfError("文件格式不正确，请上传 PDF 文件。")

    try:
        reader = PdfReader(BytesIO(file_content))
        pages_text = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as error:
        logger.warning("PDF parsing failed | type=%s", type(error).__name__, exc_info=True)
        raise InvalidPdfError("PDF 文件无法解析，请确认文件未损坏或加密。") from error

    text = "\n\n".join(part for part in pages_text if part)
    if not text:
        raise PdfTextExtractionError(
            "未提取到论文文本，请上传包含可复制文字的 PDF 文件。"
        )

    return text
