"""Generate bounded local report artifacts from already-grounded Agent output."""

from __future__ import annotations

from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.services.database import WORK_DIRECTORY


OUTPUT_DIRECTORY = WORK_DIRECTORY / "research_workspace_outputs"


class DocumentTool:
    name = "document_generation"

    def generate_markdown(self, run_id: str, title: str, content: str) -> dict[str, str]:
        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIRECTORY / f"{run_id}.md"
        path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
        return {"format": "markdown", "path": str(path.relative_to(WORK_DIRECTORY))}

    def generate_docx(self, run_id: str, title: str, content: str) -> dict[str, str]:
        """Create a minimal DOCX report without adding a heavyweight dependency."""
        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIRECTORY / f"{run_id}.docx"
        paragraphs = [title, *[line for line in content.splitlines() if line.strip()]]
        body = "".join(f"<w:p><w:r><w:t>{escape(item)}</w:t></w:r></w:p>" for item in paragraphs)
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "<?xml version='1.0'?><Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'><Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/><Default Extension='xml' ContentType='application/xml'/><Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/></Types>")
            archive.writestr("_rels/.rels", "<?xml version='1.0'?><Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='word/document.xml'/></Relationships>")
            archive.writestr("word/document.xml", "<?xml version='1.0'?><w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body>" + body + "<w:sectPr/></w:body></w:document>")
        return {"format": "docx", "path": str(path.relative_to(WORK_DIRECTORY))}
