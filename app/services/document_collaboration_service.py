"""Version metadata for Evidence-grounded deliverable drafts."""

from __future__ import annotations

import json

from sqlalchemy import func, select

from app.models.research_document_revision import ResearchDocumentRevision
from app.services.database import SessionLocal, initialize_database


class DocumentRevisionNotFoundError(Exception):
    pass


class DocumentCollaborationService:
    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._sessions = session_factory

    def create_revision(self, workspace_id: str, document_type: str, draft: dict[str, object], evidence_refs: list[dict[str, object]]) -> dict[str, object]:
        if draft.get("status") not in {"draft", "draft_ready"} or not evidence_refs:
            return {"status": "insufficient_evidence", "message": "缺少可验证 Evidence，未创建文档版本。"}
        session = self._sessions()
        try:
            maximum = session.scalar(select(func.max(ResearchDocumentRevision.version)).where(ResearchDocumentRevision.workspace_id == workspace_id, ResearchDocumentRevision.document_type == document_type)) or 0
            item = ResearchDocumentRevision(workspace_id=workspace_id, document_type=document_type, version=int(maximum) + 1, title=str(draft.get("title", document_type)), sections_json=json.dumps(draft.get("sections", {}), ensure_ascii=False), evidence_refs_json=json.dumps(evidence_refs, ensure_ascii=False))
            session.add(item); session.commit(); session.refresh(item)
            return self._payload(item)
        finally:
            session.close()

    def list(self, workspace_id: str) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            items = session.scalars(select(ResearchDocumentRevision).where(ResearchDocumentRevision.workspace_id == workspace_id).order_by(ResearchDocumentRevision.updated_at.desc())).all()
            return [self._payload(item) for item in items]
        finally:
            session.close()

    def comment(self, revision_id: str, comment: str) -> dict[str, object]:
        session = self._sessions()
        try:
            item = session.get(ResearchDocumentRevision, revision_id)
            if item is None: raise DocumentRevisionNotFoundError("文档版本不存在。")
            item.reviewer_comment = comment
            item.status = "reviewed"
            session.commit(); session.refresh(item)
            return self._payload(item)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _payload(item: ResearchDocumentRevision) -> dict[str, object]:
        def decode(value: str, fallback: object):
            try: return json.loads(value or "")
            except json.JSONDecodeError: return fallback
        return {"id": item.id, "workspace_id": item.workspace_id, "document_type": item.document_type, "version": item.version, "title": item.title, "sections": decode(item.sections_json, {}), "evidence_refs": decode(item.evidence_refs_json, []), "reviewer_comment": item.reviewer_comment, "status": item.status, "boundary": "版本记录只保存草稿摘要和 Evidence 引用；任何修改建议需由人工确认后另行生成新版本。"}
