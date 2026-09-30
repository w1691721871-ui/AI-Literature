"""Read-only environment profiling for the controlled Computer Operator."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.services.database import PROJECT_ROOT


class ComputerEnvironmentScanner:
    """Scans only approved roots and returns metadata, never document content."""

    _ignored = {".git", ".venv", "work", "__pycache__", "node_modules", ".pytest_cache"}
    _document_suffixes = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx"}

    def __init__(self, project_root: Path | None = None, workspace_root: Path | None = None) -> None:
        self.project_root = (project_root or PROJECT_ROOT).resolve()
        self.workspace_root = (workspace_root or self.project_root / "research_workspace").resolve()

    def scan(self) -> dict[str, object]:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        workspace = self._profile(self.workspace_root, "research_workspace")
        project = self._project_profile()
        return {
            "status": "OBSERVED",
            "workspace": workspace,
            "project": project,
            "boundary": "仅扫描用户授权工作区与当前项目的文件元数据；未读取私密文件内容、未修改任何文件。",
        }

    def _profile(self, root: Path, label: str) -> dict[str, object]:
        types: Counter[str] = Counter()
        duplicates: Counter[tuple[str, int]] = Counter()
        count = 0
        for item in self._files(root):
            count += 1
            suffix = item.suffix.lower() or "[no extension]"
            types[suffix] += 1
            duplicates[(item.name.lower(), item.stat().st_size)] += 1
        return {
            "root": label,
            "file_count": count,
            "file_types": dict(sorted(types.items())),
            "document_count": sum(amount for suffix, amount in types.items() if suffix in self._document_suffixes),
            "possible_duplicate_count": sum(amount - 1 for amount in duplicates.values() if amount > 1),
        }

    def _project_profile(self) -> dict[str, object]:
        profile = self._profile(self.project_root, "current_project")
        technologies = []
        if (self.project_root / "app").exists(): technologies.extend(["Python", "FastAPI"])
        if (self.project_root / "frontend").exists(): technologies.extend(["Vue", "JavaScript"])
        if (self.project_root / "requirements.txt").exists(): technologies.append("Python dependencies")
        profile.update({"project_name": self.project_root.name, "technology": technologies})
        return profile

    def _files(self, root: Path):
        for item in root.rglob("*"):
            if any(part in self._ignored for part in item.parts) or not item.is_file() or item.is_symlink():
                continue
            try:
                resolved = item.resolve()
            except OSError:
                continue
            if resolved.is_relative_to(root):
                yield item
