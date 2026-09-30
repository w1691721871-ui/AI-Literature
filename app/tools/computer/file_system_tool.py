"""Approval-first file operations inside the dedicated research workspace."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.tools.file_operator import FileOperator


class FileSystemTool:
    name = "computer_file_system"
    description = "Reads permitted workspace files and creates non-executing organization plans."

    def __init__(self, file_operator: FileOperator | None = None) -> None:
        self._files = file_operator or FileOperator()

    def scan(self) -> dict[str, object]:
        return self._files.inspect()

    def plan_organization(self) -> dict[str, object]:
        return self._files.organization_plan()

    def execute_approved(self, operation: str, source: str | None = None, target: str | None = None, content: str = "") -> dict[str, object]:
        """Perform one already-approved operation, constrained to the workspace.

        The Computer Operator never calls this method automatically.  API/UI
        approval must be recorded before a future executor may invoke it.
        """
        if operation not in {"create", "update", "copy", "move", "rename", "delete"}:
            return {"status": "BLOCKED", "message": "不支持该文件操作。"}
        try:
            root = self._files.workspace_root.resolve()
            root.mkdir(parents=True, exist_ok=True)
            source_path = self._path(root, source) if source else None
            target_path = self._path(root, target) if target else None
            if operation == "create":
                if target_path is None: raise ValueError("创建文件需要目标路径。")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                return self._result(operation, target_path)
            if source_path is None or not source_path.exists(): raise ValueError("源文件不存在或不在授权工作区。")
            if operation == "update":
                source_path.write_text(content, encoding="utf-8")
                return self._result(operation, source_path)
            if operation == "delete":
                source_path.unlink()
                return {"status": "COMPLETED", "operation": operation, "path": str(source_path.relative_to(root)).replace("\\", "/")}
            if target_path is None: raise ValueError("该操作需要目标路径。")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if operation == "copy": shutil.copy2(source_path, target_path)
            else: source_path.replace(target_path)
            return self._result(operation, target_path)
        except (OSError, ValueError) as error:
            return {"status": "FAILED", "operation": operation, "message": str(error)}

    @staticmethod
    def _path(root: Path, relative: str | None) -> Path:
        if not relative: raise ValueError("路径不能为空。")
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root) or candidate == root:
            raise ValueError("路径必须位于授权 research_workspace 内。")
        return candidate

    @staticmethod
    def _result(operation: str, path: Path) -> dict[str, object]:
        return {"status": "COMPLETED", "operation": operation, "path": path.name, "boundary": "该文件操作应在已记录的人工批准后执行。"}
