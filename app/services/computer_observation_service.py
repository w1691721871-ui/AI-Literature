"""Mandatory pre-action observations for the Computer Operator loop."""

from __future__ import annotations

from app.services.computer_environment_service import ComputerEnvironmentScanner


class ComputerObservationService:
    def __init__(self, scanner: ComputerEnvironmentScanner | None = None) -> None:
        self.scanner = scanner or ComputerEnvironmentScanner()

    def observe(self) -> dict[str, object]:
        profile = self.scanner.scan()
        workspace = profile.get("workspace", {})
        project = profile.get("project", {})
        return {
            "status": "OBSERVED",
            "environment": {
                "workspace": workspace.get("root", "research_workspace"),
                "files": workspace.get("file_count", 0),
                "documents": workspace.get("document_count", 0),
                "project_type": project.get("technology", []),
                "project_name": project.get("project_name", ""),
                "status": "ready_for_controlled_action",
            },
            "profile": profile,
            "boundary": "所有执行动作前均已完成只读环境观察；未读取文件正文、未修改环境。",
        }
