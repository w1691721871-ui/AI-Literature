"""Create factual profiles from files actually present in research_workspace/."""

from collections import Counter
from pathlib import Path

from app.tools.workspace_file_tool import WorkspaceFileTool


class WorkspaceProfileService:
    """Summarize the permitted workspace without inventing material or topics."""

    def __init__(self, file_tool: WorkspaceFileTool | None = None) -> None:
        self._file_tool = file_tool or WorkspaceFileTool()

    def build_profile(self) -> dict[str, object]:
        assets = self._file_tool.scan()
        counts = Counter(str(asset.get("type", "文件")) for asset in assets)
        filename_topics = self._filename_topics([str(asset.get("path", "")) for asset in assets])
        return {
            "documents": len(assets),
            "papers": counts.get("PDF", 0),
            "reports": counts.get("DOCX", 0) + counts.get("TXT", 0),
            "datasets": counts.get("CSV", 0) + counts.get("Excel", 0),
            "by_type": dict(counts),
            "research_topics": filename_topics,
            "assets": assets,
            "boundary_note": "工作区画像完全来自当前目录内的真实文件名与类型；研究方向仅为文件名关键词提示，不是科研事实判断。",
        }

    @staticmethod
    def _filename_topics(paths: list[str]) -> list[str]:
        seen: list[str] = []
        for item in paths:
            stem = Path(item).stem.strip()
            if len(stem) >= 2 and stem not in seen:
                seen.append(stem)
        return seen[:8]
