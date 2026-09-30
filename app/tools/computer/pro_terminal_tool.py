"""Strict command allow-list for Computer Operator Pro.

No shell is used: commands are fixed argument vectors executed in the project
root.  Any command outside this catalog is blocked before process creation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.services.database import PROJECT_ROOT


class ProSafeTerminalTool:
    name = "safe_terminal"
    description = "Runs a small, fixed read-only verification catalog; no shell or arbitrary command input."

    def __init__(self, project_root: Path | None = None) -> None:
        self.root = project_root or PROJECT_ROOT

    def catalog(self) -> list[str]:
        return ["python_version", "pytest", "compileall", "npm_check", "git_status"]

    def execute(self, operation: str) -> dict[str, object]:
        commands = {
            "python_version": [sys.executable, "--version"],
            "pytest": [sys.executable, "-m", "pytest", "-q"],
            "compileall": [sys.executable, "-m", "compileall", "app"],
            "npm_check": ["node", "--check", "frontend/app.js"],
            "git_status": ["git", "status", "--short"],
        }
        command = commands.get(operation)
        if command is None:
            return {"status": "BLOCKED", "operation": operation, "message": "该命令不在安全白名单中。"}
        completed = subprocess.run(command, cwd=str(self.root), capture_output=True, text=True, timeout=30, shell=False, check=False)
        summary = (completed.stdout or completed.stderr or "命令已完成").strip()[:1600]
        return {"status": "COMPLETED" if completed.returncode == 0 else "FAILED", "operation": operation, "return_code": completed.returncode, "summary": summary, "boundary": "仅执行预定义白名单命令；未启动 shell、未执行任意输入。"}
