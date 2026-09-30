"""Approval-gated mutation executor with an immediate deterministic verifier."""

from __future__ import annotations

from app.services.code_patch_service import CodePatchService
from app.tools.computer.file_system_tool import FileSystemTool
from app.tools.computer.permission_manager import PermissionManager


class ComputerActionExecutor:
    """Executes only a pre-approved, narrow allow-list; it never shells out."""

    def __init__(self, *, permissions: PermissionManager | None = None, files: FileSystemTool | None = None, patches: CodePatchService | None = None) -> None:
        self.permissions = permissions or PermissionManager()
        self.files = files or FileSystemTool()
        self.patches = patches or CodePatchService()

    def execute(self, action_type: str, payload: dict[str, object], *, approved: bool) -> dict[str, object]:
        permission = self.permissions.assess(action_type)
        if bool(permission["approval_required"]) and not approved:
            return {"status": "WAITING_APPROVAL", "verification": "NOT_RUN", "message": "高风险操作必须经人工批准后执行。"}
        if action_type == "apply_code_patch":
            patch_id = str(payload.get("patch_id", ""))
            result = self.patches.apply(patch_id)
            return {"status": "COMPLETED" if result.get("verification") == "SUCCESS" else "FAILED", "result": result, "verification": result.get("verification")}
        if action_type in {"move_files", "copy_files", "rename_files", "create_file", "update_file"}:
            operation = {"move_files": "move", "copy_files": "copy", "rename_files": "rename", "create_file": "create", "update_file": "update"}[action_type]
            result = self.files.execute_approved(operation, str(payload.get("source") or "") or None, str(payload.get("target") or "") or None, str(payload.get("content") or ""))
            return {"status": result.get("status", "FAILED"), "result": result, "verification": "SUCCESS" if result.get("status") == "COMPLETED" else "FAILED"}
        return {"status": "BLOCKED", "verification": "NOT_RUN", "message": "该操作不在受控执行白名单中。"}
