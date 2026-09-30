"""Deterministic static code intelligence. It never executes or edits source."""

from __future__ import annotations

import ast
from pathlib import Path

from app.services.database import PROJECT_ROOT


class CodeIntelligenceTool:
    name = "code_intelligence"

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or PROJECT_ROOT).resolve()

    def analyze(self) -> dict[str, object]:
        python_files = [path for path in self.root.rglob("*.py") if self._allowed(path)]
        js_files = [path for path in self.root.rglob("*.js") if self._allowed(path)]
        routes, functions, syntax_errors = [], 0, []
        for path in python_files:
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                functions += sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))
                if "routes" in path.parts:
                    routes.append(str(path.relative_to(self.root)).replace("\\", "/"))
            except (SyntaxError, UnicodeDecodeError):
                syntax_errors += 1
        findings = ["已完成静态 AST 与前端文件分布分析；未运行代码、未修改源码。"]
        if syntax_errors:
            findings.append(f"发现 {syntax_errors} 个 Python 文件无法静态解析，建议先运行受控验证。")
        return {
            "status": "ANALYZED", "python_files": len(python_files), "javascript_files": len(js_files),
            "function_count": functions, "route_files": routes[:20], "syntax_error_count": syntax_errors,
            "findings": findings, "boundary": "仅基于源码静态结构生成分析；性能结论需经过实际测试验证。",
        }

    def _allowed(self, path: Path) -> bool:
        return ".git" not in path.parts and ".venv" not in path.parts and "work" not in path.parts
