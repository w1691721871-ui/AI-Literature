"""Static, read-only code inspection used by Computer Operator Pro."""

from __future__ import annotations

from pathlib import Path

from app.services.database import PROJECT_ROOT


class CodeAgentTool:
    name = "code_agent"
    description = "Reads approved project source metadata and creates a reviewable optimization plan; it never edits code."
    _suffixes = {".py", ".js", ".html", ".css", ".vue"}

    def __init__(self, project_root: Path | None = None) -> None:
        self.root = (project_root or PROJECT_ROOT).resolve()

    def inspect(self, goal: str) -> dict[str, object]:
        files = [item for item in self.root.rglob("*") if item.is_file() and item.suffix.lower() in self._suffixes and ".git" not in item.parts and ".venv" not in item.parts and "work" not in item.parts]
        counts: dict[str, int] = {}
        frontend = []
        for item in files:
            suffix = item.suffix.lower()
            counts[suffix] = counts.get(suffix, 0) + 1
            if "frontend" in item.parts:
                frontend.append(str(item.relative_to(self.root)).replace("\\", "/"))
        findings = [
            "已识别项目技术栈与源文件分布；当前仅进行静态读取。",
            "代码修改仅会形成 Patch 建议，需人工批准后才能由开发者执行。",
        ]
        if any(word in goal.lower() for word in ("首页", "ui", "样式", "前端")):
            findings.append("建议优先复核 frontend/app.js、frontend/styles.css 与 Service Worker 缓存版本的一致性。")
        return {
            "status": "ANALYZED",
            "source_file_count": len(files),
            "language_distribution": counts,
            "focus_files": frontend[:12],
            "findings": findings,
            "patch_status": "PLAN_ONLY_REQUIRES_APPROVAL",
            "boundary": "没有读取密钥文件、没有执行代码、没有写入 Patch 或修改项目文件。",
        }
