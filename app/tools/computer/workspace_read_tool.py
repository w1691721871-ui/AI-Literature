"""Read-only Computer Mission workspace tool."""

from app.services.workspace_service import WorkspaceManager


class WorkspaceReadTool:
    name = "workspace_read"
    description = "Reads allow-listed code and documentation files inside ResearchOS only."

    def __init__(self, manager: WorkspaceManager | None = None) -> None:
        self.manager = manager or WorkspaceManager()

    def execute(self, file_path: str) -> dict[str, object]:
        return self.manager.inspect_file(file_path)
