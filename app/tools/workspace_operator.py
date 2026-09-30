"""Read-only environment awareness for the Research Operator."""

from app.tools.file_operator import FileOperator


class WorkspaceOperator:
    name = "workspace_operator"
    description = "Builds a read-only workspace profile from permitted research files; it cannot modify workspace contents."

    def __init__(self, file_operator: FileOperator | None = None) -> None:
        self._files = file_operator or FileOperator()

    def profile(self) -> dict[str, object]:
        inventory = self._files.inspect()
        by_type: dict[str, int] = {}
        for asset in inventory["files"]:
            label = str(asset["type"])
            by_type[label] = by_type.get(label, 0) + 1
        return {"status": "completed", "file_count": inventory["file_count"], "asset_types": by_type, "boundary": "工作空间画像仅来自当前允许目录的真实文件清单；不会读取无关位置或改动文件。"}
