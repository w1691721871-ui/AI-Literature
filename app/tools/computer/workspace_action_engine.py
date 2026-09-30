"""Creates reviewable workspace change proposals; never applies them directly."""

from __future__ import annotations

import difflib
from pathlib import Path

from app.services.database import PROJECT_ROOT


class WorkspaceActionEngine:
    _allowed = {".py", ".js", ".vue", ".json", ".md", ".css", ".html"}
    _blocked = {".env", "secret", "credential", "token", "password"}

    def __init__(self, root: Path | None = None) -> None: self.root = (root or PROJECT_ROOT).resolve()

    def read(self, relative_path: str) -> dict[str, object]:
        path = self._safe(relative_path)
        return {"status": "READ", "file_path": relative_path, "content": path.read_text(encoding="utf-8"), "boundary": "仅允许读取代码与文档白名单文件。"}

    def propose(self, relative_path: str, operation: str, content: str) -> dict[str, object]:
        if operation not in {"create", "update", "append", "replace"}: raise ValueError("不支持该 Workspace Action。")
        path = self._safe(relative_path, allow_new=operation == "create")
        before = path.read_text(encoding="utf-8") if path.exists() else ""
        after = content if operation in {"create", "update", "replace"} else before + content
        diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=relative_path, tofile=relative_path))
        return {"status": "WAITING_APPROVAL", "operation": operation, "file_path": relative_path, "before_summary": f"{len(before)} characters", "after_summary": f"{len(after)} characters", "diff": diff, "risk_level": "MEDIUM", "verification_plan": "审批后运行白名单 compileall / node --check；不自动执行写入。"}

    def _safe(self, relative: str, allow_new: bool = False) -> Path:
        if any(part.lower() in self._blocked or part.lower().startswith(".env") for part in Path(relative).parts): raise ValueError("禁止访问敏感文件。")
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or path.suffix.lower() not in self._allowed or (not allow_new and not path.is_file()): raise ValueError("路径不在受控代码/文档白名单内。")
        return path
