"""Central risk classification for computer-layer actions."""


class PermissionManager:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    def assess(self, action_type: str) -> dict[str, object]:
        if action_type in {"move_files", "copy_files", "rename_files", "delete_files", "download_source", "import_knowledge", "apply_code_patch"}:
            level = self.HIGH
        elif action_type in {"create_document", "create_folder", "create_file", "update_file"}:
            level = self.MEDIUM
        else:
            level = self.LOW
        return {"risk_level": level, "approval_required": level != self.LOW, "status": "PENDING_APPROVAL" if level != self.LOW else "APPROVED_READ_ONLY"}
