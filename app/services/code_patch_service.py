"""Creates and applies explicit, reviewable patches without shell access."""

from __future__ import annotations

import difflib
from pathlib import Path

from sqlalchemy import select

from app.models.code_patch import CodePatch
from app.services.database import PROJECT_ROOT, SessionLocal, initialize_database


class CodePatchNotFoundError(Exception):
    pass


class CodePatchService:
    """Code changes are persisted as a diff plus exact before/after content."""

    def __init__(self, session_factory=SessionLocal, project_root: Path | None = None, *, initialize: bool = True) -> None:
        if initialize:
            initialize_database()
        self._session_factory = session_factory
        self.root = (project_root or PROJECT_ROOT).resolve()

    def propose_home_ui_focus(self, task_id: str) -> dict[str, object]:
        relative = "frontend/styles.css"; path = self._safe_path(relative)
        before = path.read_text(encoding="utf-8")
        addition = "\n/* Computer Operator Pro: approved focus visibility for the research command. */\n.home-research-input:focus-within{border-color:rgba(99,241,220,.42)!important;box-shadow:0 0 0 3px rgba(99,241,220,.08),0 20px 65px rgba(0,0,0,.4)!important}\n"
        after = before if addition.strip() in before else before.rstrip() + addition
        diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=relative, tofile=relative))
        return self._create(task_id, relative, before, after, diff)

    def get(self, patch_id: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            item = session.get(CodePatch, patch_id)
            if item is None: raise CodePatchNotFoundError("Code Patch 不存在。")
            return self._payload(item)
        finally: session.close()

    def list_for_task(self, task_id: str) -> list[dict[str, object]]:
        session = self._session_factory()
        try: return [self._payload(row) for row in session.scalars(select(CodePatch).where(CodePatch.task_id == task_id).order_by(CodePatch.created_at.asc())).all()]
        finally: session.close()

    def apply(self, patch_id: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            item = session.get(CodePatch, patch_id)
            if item is None: raise CodePatchNotFoundError("Code Patch 不存在。")
            if item.status != "WAITING_APPROVAL": raise ValueError("该 Patch 当前不能应用。")
            path = self._safe_path(item.file_path)
            current = path.read_text(encoding="utf-8")
            if current != item.original_content:
                item.status = "REJECTED"; session.commit()
                return {**self._payload(item), "verification": "FAILED", "message": "源文件已变化，已拒绝应用过期 Patch。"}
            path.write_text(item.patched_content, encoding="utf-8")
            item.status = "APPLIED"; session.commit(); session.refresh(item)
            verified = path.read_text(encoding="utf-8") == item.patched_content
            return {**self._payload(item), "verification": "SUCCESS" if verified else "FAILED", "message": "Patch 已写入并完成内容校验。"}
        except Exception:
            session.rollback(); raise
        finally: session.close()

    def reject(self, patch_id: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            item = session.get(CodePatch, patch_id)
            if item is None: raise CodePatchNotFoundError("Code Patch 不存在。")
            item.status = "REJECTED"; session.commit(); session.refresh(item); return self._payload(item)
        finally: session.close()

    def _create(self, task_id, file_path, before, after, diff):
        session = self._session_factory()
        try:
            item = CodePatch(task_id=task_id, file_path=file_path, diff_content=diff, status="WAITING_APPROVAL", original_content=before, patched_content=after)
            session.add(item); session.commit(); session.refresh(item); return self._payload(item)
        finally: session.close()

    def _safe_path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or not path.is_file(): raise ValueError("Patch 文件必须位于当前项目且已经存在。")
        return path

    @staticmethod
    def _payload(item: CodePatch) -> dict[str, object]:
        return {"id": item.id, "task_id": item.task_id, "file_path": item.file_path, "diff_content": item.diff_content, "status": item.status, "created_at": item.created_at, "updated_at": item.updated_at}
