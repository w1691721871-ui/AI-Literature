"""Read-only, metadata-only map of the current authorized project workspace."""

from __future__ import annotations

from pathlib import Path

from app.services.database import PROJECT_ROOT


class WorkspaceExplorer:
    name = "workspace_explorer"
    _blocked_names = {".env", ".env.local", "secrets", "credentials"}

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or PROJECT_ROOT).resolve()

    def map(self) -> dict[str, object]:
        visible = [path for path in self.root.iterdir() if path.name not in self._blocked_names and path.name != ".venv"]
        names = {path.name for path in visible}
        technology = []
        if "app" in names: technology.extend(["Python", "FastAPI"])
        if "frontend" in names: technology.extend(["Vue", "JavaScript"])
        if "requirements.txt" in names: technology.append("Python dependencies")
        return {
            "status": "OBSERVED",
            "workspace_map": {
                "root": self.root.name,
                "top_level": sorted(path.name for path in visible if path.is_dir())[:24],
                "project_type": " + ".join(technology) or "Unknown",
                "backend": "Python" if "app" in names else "未识别",
                "frontend": "Vue" if "frontend" in names else "未识别",
                "database": "SQLite" if "work" in names else "未识别",
                "ai_stack": "Qwen + FAISS" if "app" in names else "未识别",
                "config_files": sorted(path.name for path in visible if path.is_file() and path.suffix in {".txt", ".yaml", ".yml", ".json"})[:12],
            },
            "boundary": "仅返回项目结构与配置文件名；不会读取 .env、凭据、源码正文或用户私密文件。",
        }
