"""Research Memory product service with explicit Workspace ownership."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from sqlalchemy import select

from app.models.workspace_memory import WorkspaceMemory
from app.services.database import SessionLocal, initialize_database


class WorkspaceMemoryError(ValueError):
    pass


class WorkspaceMemoryService:
    """Creates, explains, lists and removes only compact, traceable summaries."""

    _TYPES = {"WORKSPACE", "USER", "MISSION", "KNOWLEDGE"}
    _FORBIDDEN = re.compile(r"(?i)(prompt|chain[ -]?of[ -]?thought|api[_-]?key|password|bearer\s+|secret)")

    def __init__(self, sessions=SessionLocal, *, initialize=True):
        if initialize:
            initialize_database()
        self._sessions = sessions

    def save_user_preference(self, workspace_id: str, user_id: str, title: str, summary: str) -> dict[str, object]:
        return self._save(workspace_id, "USER", title, summary, owner_id=user_id, source_type="USER_CONFIRMED")

    def record_mission_summary(self, mission: Mapping[str, object], *, owner_id: str | None = None) -> dict[str, object] | None:
        workspace_id = str(mission.get("workspace_id") or "")
        mission_id = str(mission.get("id") or "")
        if not workspace_id or not mission_id:
            return None
        evidence_refs = mission.get("evidence_refs") if isinstance(mission.get("evidence_refs"), list) else []
        summary = (
            f"Mission status: {mission.get('status') or 'CREATED'}. "
            f"Current step: {mission.get('current_step') or 'Not started'}. "
            f"Traceable Evidence references: {len(evidence_refs)}. "
            "Human review remains required before any important release."
        )
        session = self._sessions()
        try:
            row = session.scalar(select(WorkspaceMemory).where(
                WorkspaceMemory.workspace_id == workspace_id,
                WorkspaceMemory.mission_id == mission_id,
                WorkspaceMemory.memory_type == "MISSION",
            ))
            if row is None:
                row = WorkspaceMemory(
                    workspace_id=workspace_id,
                    owner_id=owner_id,
                    mission_id=mission_id,
                    memory_type="MISSION",
                    title=f"Mission record · {str(mission.get('title') or 'Untitled mission')[:140]}",
                    summary=summary,
                    references_json=json.dumps(evidence_refs[:20]),
                    source_type="RUNTIME_SUMMARY",
                )
                session.add(row)
            else:
                row.summary = summary
                row.references_json = json.dumps(evidence_refs[:20])
            session.commit(); session.refresh(row)
            return self._item(row)
        finally:
            session.close()

    def list(self, workspace_id: str, *, user_id: str | None = None, mission_id: str | None = None) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            query = select(WorkspaceMemory).where(WorkspaceMemory.workspace_id == workspace_id, WorkspaceMemory.status == "ACTIVE")
            if mission_id:
                query = query.where(WorkspaceMemory.mission_id == mission_id)
            if user_id:
                query = query.where((WorkspaceMemory.owner_id.is_(None)) | (WorkspaceMemory.owner_id == user_id))
            return [self._item(row) for row in session.scalars(query.order_by(WorkspaceMemory.updated_at.desc())).all()]
        finally:
            session.close()

    def context_slice(self, workspace_id: str, *, user_id: str | None, mission_id: str | None) -> dict[str, list[dict[str, object]]]:
        rows = self.list(workspace_id, user_id=user_id)
        return {
            "workspace": [row for row in rows if row["memory_type"] == "WORKSPACE"][:3],
            "user": [row for row in rows if row["memory_type"] == "USER"][:3],
            "mission": [row for row in rows if row["memory_type"] == "MISSION" and row["mission_id"] == mission_id][:3],
            "knowledge": [row for row in rows if row["memory_type"] == "KNOWLEDGE"][:3],
        }

    def explain(self, memory_id: str, workspace_id: str, *, user_id: str | None = None) -> dict[str, object]:
        row = self._row(memory_id, workspace_id)
        if row.owner_id and row.owner_id != user_id:
            raise PermissionError("User memory belongs to another Workspace member.")
        item = self._item(row)
        return {**item, "explanation": "This is a compact, traceable workspace summary. It never includes prompts, model reasoning, credentials, or source-document bodies."}

    def delete(self, memory_id: str, workspace_id: str, *, user_id: str | None = None, allow_workspace_delete: bool = False) -> dict[str, object]:
        session = self._sessions()
        try:
            row = session.get(WorkspaceMemory, memory_id)
            if row is None or row.workspace_id != workspace_id:
                raise WorkspaceMemoryError("Memory is not available in this Workspace.")
            if row.owner_id and row.owner_id != user_id and not allow_workspace_delete:
                raise PermissionError("Only the memory owner or an authorized reviewer can remove this memory.")
            if row.owner_id is None and not allow_workspace_delete:
                raise PermissionError("Workspace memory requires an authorized reviewer to remove.")
            row.status = "DELETED"; session.commit()
            return {"id": memory_id, "deleted": True}
        finally:
            session.close()

    def _save(self, workspace_id: str, memory_type: str, title: str, summary: str, *, owner_id: str | None, source_type: str) -> dict[str, object]:
        clean_title, clean_summary = title.strip(), summary.strip()
        if not workspace_id or memory_type not in self._TYPES or not clean_title or not clean_summary:
            raise WorkspaceMemoryError("Memory requires a Workspace, supported type, title and summary.")
        if len(clean_title) > 180 or len(clean_summary) > 1200 or self._FORBIDDEN.search(clean_title + " " + clean_summary):
            raise WorkspaceMemoryError("Memory must be a compact non-sensitive summary.")
        session = self._sessions()
        try:
            row = WorkspaceMemory(workspace_id=workspace_id, owner_id=owner_id, memory_type=memory_type, title=clean_title, summary=clean_summary, source_type=source_type)
            session.add(row); session.commit(); session.refresh(row)
            return self._item(row)
        finally:
            session.close()

    def _row(self, memory_id: str, workspace_id: str) -> WorkspaceMemory:
        session = self._sessions()
        try:
            row = session.get(WorkspaceMemory, memory_id)
            if row is None or row.workspace_id != workspace_id or row.status != "ACTIVE":
                raise WorkspaceMemoryError("Memory is not available in this Workspace.")
            session.expunge(row)
            return row
        finally:
            session.close()

    @staticmethod
    def _item(row: WorkspaceMemory) -> dict[str, object]:
        try:
            references = json.loads(row.references_json or "[]")
        except json.JSONDecodeError:
            references = []
        return {"id": row.id, "workspace_id": row.workspace_id, "owner_id": row.owner_id, "mission_id": row.mission_id, "memory_type": row.memory_type, "title": row.title, "summary": row.summary, "references": references, "source_type": row.source_type, "created_at": row.created_at, "updated_at": row.updated_at}
