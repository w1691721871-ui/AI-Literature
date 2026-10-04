"""Controlled document, data and report work under the existing Computer Skill.

The service has no global file discovery: it can only use FileAsset records
explicitly attached to the current Mission.  It returns compact structural
summaries and reviewable drafts, never raw customer content or auto-released
deliverables.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.file_asset import FileAsset
from app.models.mission_file_source import MissionFileSource
from app.services.artifact_service import ArtifactService
from app.services.database import PROJECT_ROOT, SessionLocal, initialize_database
from app.services.document_parser_service import DocumentParserService


class EnterpriseComputerWorkerService:
    """Execute only review-bounded work over a Mission's authorized inputs."""

    _DOCUMENT_TYPES = {"PDF", "DOCX", "TXT", "PPTX"}

    def __init__(self, sessions: Callable = SessionLocal, *, initialize: bool = True, parser=None, artifacts=None):
        if initialize:
            initialize_database()
        self._sessions = sessions
        self._parser = parser or DocumentParserService()
        self._artifacts = artifacts or ArtifactService(sessions, initialize=False)

    def execute(self, mission: Mapping[str, object]) -> dict[str, object]:
        mission_id = str(mission.get("id") or "")
        if not mission_id:
            return self._result("NEEDS_REVIEW", "Computer work needs a persisted Mission.", "No authorized Mission was available for this action.")
        sources = self._authorized_sources(mission_id)
        if not sources:
            return self._result("NEEDS_REVIEW", "No authorized source material is attached to this Mission.", "Attach a user-authorized document or spreadsheet before requesting Computer work.")
        goal = str(mission.get("goal") or mission.get("title") or "")
        lowered = goal.lower()
        if any(term in lowered for term in ("data", "dataset", "table", "spreadsheet", "数据", "表格")):
            return self._data_work(mission_id, sources)
        if any(term in lowered for term in ("report", "brief", "proposal", "报告", "调研", "方案")):
            return self._report_work(mission, sources)
        return self._document_work(mission_id, sources)

    def _document_work(self, mission_id: str, sources: list[FileAsset]) -> dict[str, object]:
        source = next((item for item in sources if item.file_type in self._DOCUMENT_TYPES), None)
        if source is None:
            return self._result("NEEDS_REVIEW", "No authorized document is available for structure extraction.", "Use a supported document source or select the Data Skill for an attached spreadsheet.")
        try:
            parsed = self._parse(source)
        except Exception:
            return self._result("NEEDS_REVIEW", "The authorized document could not be safely parsed.", "No document summary or research claim was created.")
        structure = parsed.get("structure") if isinstance(parsed.get("structure"), Mapping) else {}
        result = {
            "source": {"id": source.id, "filename": source.filename, "file_type": source.file_type},
            "structure": self._safe_structure(structure),
            "limitations": str(parsed.get("limitations") or ""),
        }
        self._event(mission_id, "DOCUMENT_STRUCTURE_READY", "Authorized document structure was extracted for review.")
        return self._result("SUCCESS", "The AI Worker extracted the structure of an authorized document.", "A document structure summary is ready for review; it is not Evidence or a final report.", result)

    def _data_work(self, mission_id: str, sources: list[FileAsset]) -> dict[str, object]:
        source = next((item for item in sources if item.file_type == "XLSX"), None)
        if source is None:
            return self._result("NEEDS_REVIEW", "No authorized spreadsheet is attached to this Mission.", "A Data Insight Candidate cannot be created without an attached user-provided spreadsheet.")
        try:
            parsed = self._parse(source)
        except Exception:
            return self._result("NEEDS_REVIEW", "The authorized spreadsheet could not be safely parsed.", "No data result or conclusion was generated.")
        structure = parsed.get("structure") if isinstance(parsed.get("structure"), Mapping) else {}
        sheets = structure.get("sheets") if isinstance(structure.get("sheets"), list) else []
        result = {
            "source": {"id": source.id, "filename": source.filename, "file_type": source.file_type},
            "sheets": [{"sheet": str(item.get("sheet") or "Sheet"), "rows": int(item.get("rows") or 0), "fields": [str(value)[:120] for value in (item.get("fields") or [])[:20]]} for item in sheets if isinstance(item, Mapping)],
            "limitations": str(parsed.get("limitations") or ""),
            "classification": "DATA_INSIGHT_CANDIDATE",
        }
        self._event(mission_id, "DATA_INSIGHT_CANDIDATE", "Authorized spreadsheet structure was inspected; no statistical claim was inferred.")
        return self._result("SUCCESS", "The AI Worker prepared a Data Insight Candidate from an authorized spreadsheet.", "The candidate reports available fields and row counts only; a reviewer must validate any analytical interpretation.", result)

    def _report_work(self, mission: Mapping[str, object], sources: list[FileAsset]) -> dict[str, object]:
        if str(mission.get("status") or "").upper() != "APPROVED":
            return self._result("WAITING_REVIEW", "A research report draft requires Mission approval.", "No report draft was generated before the existing human approval gate.")
        evidence = mission.get("evidence_refs") if isinstance(mission.get("evidence_refs"), list) else []
        if not evidence:
            return self._result("WAITING_REVIEW", "A research report draft requires traceable Evidence.", "No research report was generated because the Mission has no traceable Evidence references.")
        try:
            artifact = self._artifacts.generate(str(mission["id"]), "RESEARCH_BRIEF")
        except Exception:
            return self._result("NEEDS_REVIEW", "The reviewable report draft could not be generated.", "No release occurred; an authorized reviewer can inspect the existing Mission and Artifact state.")
        self._event(str(mission["id"]), "REPORT_DRAFT_CREATED", "A versioned research report draft was created and remains pending review.")
        return self._result("WAITING_REVIEW", "The AI Worker created a reviewable Research Brief draft.", "The report is linked to Mission sources and Evidence, and cannot be released until human review.", {"artifact": {"id": artifact.get("id"), "title": artifact.get("title"), "version": artifact.get("version"), "status": artifact.get("status")}, "source_count": len(sources), "evidence_count": len(evidence)})

    def _authorized_sources(self, mission_id: str) -> list[FileAsset]:
        session = self._sessions()
        try:
            if session.get(AIMission, mission_id) is None:
                return []
            rows = session.scalars(select(MissionFileSource).where(MissionFileSource.mission_id == mission_id)).all()
            return [asset for row in rows if (asset := session.get(FileAsset, row.file_id)) is not None and asset.status == "COMPLETED"]
        finally:
            session.close()

    def _parse(self, source: FileAsset) -> dict[str, object]:
        path = Path(source.storage_path).resolve()
        controlled_root = (PROJECT_ROOT / "work").resolve()
        if controlled_root not in path.parents or not path.is_file():
            raise ValueError("Authorized source is outside the controlled input store.")
        return self._parser.parse(source.filename, path.read_bytes(), source.file_type)

    def _event(self, mission_id: str, action: str, summary: str) -> None:
        session = self._sessions()
        try:
            session.add(AIMissionEvent(mission_id=mission_id, stage="Computer Skill", action=action, status="REVIEWABLE", evidence_count=0, result_summary=summary))
            session.commit()
        finally:
            session.close()

    @staticmethod
    def _safe_structure(structure: Mapping[str, object]) -> dict[str, object]:
        allowed = {"pages", "paragraphs", "headings", "slides", "titles", "lines", "language", "symbols"}
        return {str(key): value for key, value in structure.items() if str(key) in allowed}

    @staticmethod
    def _result(status: str, observation: str, summary: str, output: Mapping[str, object] | None = None) -> dict[str, object]:
        return {"status": status, "observation": observation, "summary": summary, "output": dict(output or {}), "verification": "The output contains only metadata or a reviewable Artifact status. No final claim or release is inferred.", "boundary": "Only files explicitly linked to this Mission are read. Raw file content, prompts, credentials and external writes are excluded."}
