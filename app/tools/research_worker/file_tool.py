"""Safe, factual file understanding for the bounded Research Worker."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader

from app.tools.research_worker.base import Tool
from app.tools.research_worker.data_tool import DataTool
from app.tools.workspace_file_tool import WorkspaceFileTool

_SECTION_PATTERN = re.compile(r"^(摘要|abstract|引言|introduction|相关工作|related work|方法|methods?|实验|experiments?|结果|results?|讨论|discussion|结论|conclusion|references|参考文献)", re.IGNORECASE)
_STOP_WORDS = {"the", "and", "for", "with", "this", "that", "from", "研究", "方法", "实验", "结果", "论文", "分析"}


class FileTool(Tool):
    name = "file_tool"
    description = "扫描并提取 research_workspace 中允许文件的真实结构摘要，不生成文件中不存在的信息。"

    def __init__(self, workspace_tool: WorkspaceFileTool | None = None) -> None:
        self._workspace = workspace_tool or WorkspaceFileTool()
        self._data_tool = DataTool(self._workspace)

    def execute(self, *, max_files: int = 5) -> dict[str, object]:
        assets = self._workspace.scan()
        reports, excerpts = [], []
        for asset in assets[:max_files]:
            try:
                report = self._analyze_asset(asset)
                reports.append(report)
                excerpts.append({"path": asset["path"], "type": asset["type"], "text_length": report.get("text_length", 0), "excerpt": str(report.get("available_information", ""))[:500]})
            except (ValueError, OSError, BadZipFile) as error:
                reports.append(self._failure_report(asset, str(error)))
                excerpts.append({"path": asset["path"], "type": asset["type"], "error": str(error)})
        return {"asset_count": len(assets), "assets": assets, "read_items": excerpts, "file_reports": reports}

    def _analyze_asset(self, asset: dict[str, object]) -> dict[str, object]:
        relative_path, file_type = str(asset["path"]), str(asset["type"])
        path = self._workspace._safe_path(relative_path)
        if file_type == "PDF":
            return self._pdf_report(path, relative_path)
        if file_type == "DOCX":
            return self._docx_report(path, relative_path)
        if file_type in {"CSV", "Excel"}:
            return self._data_tool.analyze_file(relative_path)
        if file_type == "TXT":
            return self._text_report(relative_path, "TXT", self._workspace.read_text(relative_path, max_chars=20_000))
        return self._failure_report(asset, "该文件类型不在 Worker 可理解范围内。")

    def _pdf_report(self, path: Path, relative_path: str) -> dict[str, object]:
        try:
            reader = PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as error:
            raise ValueError("PDF 文件无法提取文本结构。") from error
        return {"filename": relative_path, "type": "PDF", "structure": {"page_count": len(reader.pages), "detected_sections": self._detect_sections(text)}, "text_length": len(text), "available_information": {"keywords": self._keywords(text), "text_available": bool(text.strip())}, "limitations": [] if text.strip() else ["PDF 未提取到可用文本，不能据此生成科研结论。"]}

    def _docx_report(self, path: Path, relative_path: str) -> dict[str, object]:
        try:
            with ZipFile(path) as archive:
                root = ElementTree.fromstring(archive.read("word/document.xml"))
        except (KeyError, BadZipFile, ElementTree.ParseError) as error:
            raise ValueError("DOCX 文件无法读取。") from error
        paragraphs, headings = [], []
        for paragraph in root.findall(".//{*}p"):
            text = "".join(node.text or "" for node in paragraph.findall(".//{*}t")).strip()
            if not text:
                continue
            paragraphs.append(text)
            style = paragraph.find(".//{*}pStyle")
            if style is not None and "heading" in str(style.attrib).lower():
                headings.append(text)
        raw_text = "\n".join(paragraphs)
        return {"filename": relative_path, "type": "DOCX", "structure": {"paragraph_count": len(paragraphs), "title_structure": headings[:20]}, "text_length": len(raw_text), "available_information": {"content_summary": raw_text[:400], "keywords": self._keywords(raw_text)}, "limitations": [] if paragraphs else ["DOCX 没有可读取段落，不能据此生成科研结论。"]}

    def _text_report(self, relative_path: str, file_type: str, text: str) -> dict[str, object]:
        return {"filename": relative_path, "type": file_type, "structure": {"detected_sections": self._detect_sections(text)}, "text_length": len(text), "available_information": {"content_summary": text[:400], "keywords": self._keywords(text)}, "limitations": [] if text else ["文件没有可读取文本，不能据此生成科研结论。"]}

    @staticmethod
    def _failure_report(asset: dict[str, object], message: str) -> dict[str, object]:
        return {"filename": str(asset.get("path", "")), "type": str(asset.get("type", "文件")), "structure": {}, "available_information": {}, "limitations": [message]}

    @staticmethod
    def _detect_sections(text: str) -> list[str]:
        seen = []
        for line in text.splitlines():
            candidate = " ".join(line.split()).strip()
            if candidate and len(candidate) <= 80 and _SECTION_PATTERN.match(candidate) and candidate not in seen:
                seen.append(candidate)
        return seen[:20]

    @staticmethod
    def _keywords(text: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}|[\u4e00-\u9fff]{2,8}", text.lower())
        counts = Counter(token for token in tokens if token not in _STOP_WORDS)
        return [token for token, _ in counts.most_common(12)]
