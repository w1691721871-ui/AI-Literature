"""Computer-layer draft generation adapter, grounded in P7 evidence rules."""

from app.tools.document_generator import DocumentGenerator


class ComputerDocumentTool:
    name = "computer_document_generator"
    description = "Creates reviewable MD/DOCX drafts from traceable evidence only."

    def __init__(self, generator: DocumentGenerator | None = None) -> None:
        self._generator = generator or DocumentGenerator()

    def create_draft(self, task_id: str, task_type: str, goal: str, evidence_refs: list[dict[str, object]]) -> dict[str, object]:
        return self._generator.generate(task_id, document_type=task_type, objective=goal, evidence_refs=evidence_refs)
