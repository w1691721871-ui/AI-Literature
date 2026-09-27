"""Controlled Markdown/DOCX delivery generation for Research Worker."""

import shutil

from app.services.database import WORK_DIRECTORY
from app.tools.document_tool import DocumentTool as ExistingDocumentTool, OUTPUT_DIRECTORY
from app.tools.research_worker.base import Tool


class DocumentTool(Tool):
    name = "document_tool"
    description = "基于已有工具结果生成 Markdown 或 DOCX 交付物。"

    def __init__(self, tool: ExistingDocumentTool | None = None) -> None:
        self._tool = tool or ExistingDocumentTool()

    def execute(self, run_id: str, title: str, content: str, *, generate_docx: bool = False) -> dict[str, object]:
        output = {"markdown": self._tool.generate_markdown(run_id, title, content)}
        if generate_docx:
            output["docx"] = self._tool.generate_docx(run_id, title, content)
        delivery_dir = OUTPUT_DIRECTORY / run_id
        delivery_dir.mkdir(parents=True, exist_ok=True)
        renamed: dict[str, object] = {}
        for key, filename in (("markdown", "research_report.md"), ("docx", "research_summary.docx")):
            if key in output:
                source = WORK_DIRECTORY / str(output[key]["path"])
                target = delivery_dir / filename
                shutil.move(str(source), target)
                renamed[key] = {"format": output[key]["format"], "path": str(target.relative_to(WORK_DIRECTORY))}
        return renamed
