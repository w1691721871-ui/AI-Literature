"""P18 persistence for reviewable file changes without unrestricted file access."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select

from app.models.computer_file_change import ComputerFileChange
from app.services.database import SessionLocal, initialize_database


class ComputerUseNotFoundError(Exception): pass


class ComputerUseService:
    def __init__(self, session_factory=SessionLocal, *, initialize: bool = True) -> None:
        if initialize: initialize_database()
        self._session_factory = session_factory

    def propose(self, task_id: str, proposal: dict[str, object]) -> dict[str, object]:
        before, after = str(proposal.get("before_content", "")), str(proposal.get("after_content", ""))
        session = self._session_factory()
        try:
            row = ComputerFileChange(task_id=task_id, file_path=str(proposal["file_path"]), operation=str(proposal["operation"]).upper(), before_hash=self._hash(before), after_hash=self._hash(after), diff_content=str(proposal.get("diff", "")), before_content=before, after_content=after, status="PROPOSED")
            session.add(row); session.commit(); session.refresh(row); return self._payload(row)
        finally: session.close()

    def get(self, change_id: str) -> ComputerFileChange:
        session = self._session_factory()
        try:
            row = session.get(ComputerFileChange, change_id)
            if row is None: raise ComputerUseNotFoundError("文件修改提案不存在。")
            session.expunge(row); return row
        finally: session.close()

    def changes(self, task_id: str) -> list[dict[str, object]]:
        session = self._session_factory()
        try: return [self._payload(row) for row in session.scalars(select(ComputerFileChange).where(ComputerFileChange.task_id == task_id).order_by(ComputerFileChange.created_at.asc())).all()]
        finally: session.close()

    def update_status(self, change_id: str, status: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            row = session.get(ComputerFileChange, change_id)
            if row is None: raise ComputerUseNotFoundError("文件修改提案不存在。")
            row.status = status; session.commit(); session.refresh(row); return self._payload(row)
        finally: session.close()

    @staticmethod
    def _hash(value: str) -> str: return hashlib.sha256(value.encode("utf-8")).hexdigest()
    @staticmethod
    def _payload(row: ComputerFileChange) -> dict[str, object]:
        return {"id": row.id, "task_id": row.task_id, "file_path": row.file_path, "operation": row.operation, "before_hash": row.before_hash, "after_hash": row.after_hash, "diff": row.diff_content, "status": row.status, "created_at": row.created_at}
