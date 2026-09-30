"""A non-shell terminal abstraction for allow-listed local data inspection."""

from datetime import datetime, timezone

from app.tools.code_execution_tool import CodeExecutionTool


class TerminalTool:
    name = "safe_terminal"
    description = "Allows only fixed data-summary operations; no shell, subprocesses, or system commands."

    def __init__(self, code_tool: CodeExecutionTool | None = None) -> None:
        self._code_tool = code_tool or CodeExecutionTool()

    def execute(self, operation: str, relative_path: str | None = None) -> dict[str, object]:
        if operation != "dataset_summary":
            return {"status": "BLOCKED", "operation": operation, "result": "仅允许 dataset_summary；不支持 shell 或任意命令。", "timestamp": datetime.now(timezone.utc).isoformat()}
        result = self._code_tool.analyze(relative_path)
        return {"status": result.get("status", "completed"), "operation": operation, "result": result, "timestamp": datetime.now(timezone.utc).isoformat()}
