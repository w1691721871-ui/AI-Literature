"""Approval-first file inventory and organization planning for Research Operator."""

from __future__ import annotations

from pathlib import Path

from app.services.database import PROJECT_ROOT


class FileOperator:
    """Never mutates a workspace until a separately approved operation exists.

    Copy, move and delete are intentionally represented as plans in v1.  This
    keeps the Operator useful for preparation without granting filesystem
    control or allowing destructive behavior.
    """

    name = "file_operator"
    description = "Safely inventories and proposes classification of research files. Mutations require human approval."
    allowed_suffixes = {".pdf", ".docx", ".xlsx", ".pptx", ".md", ".txt", ".csv"}

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or PROJECT_ROOT / "research_workspace").resolve()

    def inspect(self) -> dict[str, object]:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        assets: list[dict[str, object]] = []
        for item in sorted(self.workspace_root.rglob("*")):
            if not item.is_file() or item.is_symlink() or item.suffix.lower() not in self.allowed_suffixes:
                continue
            resolved = item.resolve()
            if not resolved.is_relative_to(self.workspace_root):
                continue
            assets.append({"path": str(item.relative_to(self.workspace_root)).replace("\\", "/"), "type": self._type(item.suffix), "size": item.stat().st_size})
        return {"status": "completed", "workspace": str(self.workspace_root.name), "file_count": len(assets), "files": assets, "boundary": "只读取文件清单；未读取或修改原始文件。"}

    def organization_plan(self) -> dict[str, object]:
        inventory = self.inspect()
        proposals = []
        for asset in inventory["files"]:
            proposals.append({"source": asset["path"], "suggested_group": self._group(str(asset["path"])), "operation": "copy_or_move_requires_approval"})
        return {"status": "approval_required", "file_count": inventory["file_count"], "proposals": proposals, "boundary": "文件移动、复制、创建目录或删除均未执行，必须由负责人逐项批准。"}

    def request_destructive_operation(self, relative_path: str, operation: str) -> dict[str, object]:
        if operation not in {"copy", "move", "delete", "create"}:
            raise ValueError("仅允许受控文件操作计划。")
        return {"status": "approval_required", "operation": operation, "path": relative_path, "boundary": "Research Operator 不会自动执行文件写入、移动或删除。"}

    @staticmethod
    def _type(suffix: str) -> str:
        return {".pdf": "PDF", ".docx": "DOCX", ".xlsx": "XLSX", ".pptx": "PPTX", ".md": "Markdown", ".txt": "Text", ".csv": "CSV"}.get(suffix.lower(), "Document")

    @staticmethod
    def _group(path: str) -> str:
        lowered = path.lower()
        if any(token in lowered for token in ("experiment", "实验", "data", "dataset")):
            return "Experiment"
        if any(token in lowered for token in ("method", "方法", "model")):
            return "Methodology"
        if any(token in lowered for token in ("summary", "综述", "review")):
            return "Summary"
        return "Related_Work"
