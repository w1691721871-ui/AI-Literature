"""User-readable verifier over the existing fixed command allow-list."""

from app.tools.computer.execution_sandbox import ExecutionSandbox


class VerificationAgent:
    MAX_RETRIES = 3

    def __init__(self, sandbox: ExecutionSandbox | None = None) -> None:
        self.sandbox = sandbox or ExecutionSandbox()

    def verify(self, changed_file: str) -> dict[str, object]:
        operations = ["compileall"] if changed_file.endswith(".py") else ["npm_check"]
        results = [self.sandbox.validate(operation) for operation in operations]
        passed = all(item.get("verification") == "SUCCESS" for item in results)
        return {
            "status": "PASS" if passed else "FAIL",
            "commands": operations,
            "results": results,
            "suggestion": "验证未通过，请检查 Diff 并创建新的修订提案。" if not passed else "白名单验证通过，结果仍需人工复核。",
            "boundary": "仅运行固定白名单命令；不执行任意 shell 输入。",
        }
