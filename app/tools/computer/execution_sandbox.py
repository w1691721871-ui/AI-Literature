"""Safe validation wrapper around the pre-existing fixed command allow-list."""

from __future__ import annotations

from app.tools.computer.pro_terminal_tool import ProSafeTerminalTool


class ExecutionSandbox:
    name = "execution_sandbox"

    def __init__(self, terminal: ProSafeTerminalTool | None = None) -> None:
        self.terminal = terminal or ProSafeTerminalTool()

    def validate(self, operation: str = "compileall") -> dict[str, object]:
        if operation not in set(self.terminal.catalog()):
            return {"status": "BLOCKED", "verification": "NOT_RUN", "message": "验证操作不在安全白名单中。"}
        result = self.terminal.execute(operation)
        return {"status": result.get("status"), "verification": "SUCCESS" if result.get("status") == "COMPLETED" else "FAILED", "result": result}
