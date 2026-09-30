"""Narrow, non-shell data inspection helper for Research Operator."""

from __future__ import annotations

from app.tools.data_analysis_tool import DataAnalysisTool


class CodeExecutionTool:
    name = "safe_data_analysis"
    description = "Runs allow-listed CSV/XLSX structure summaries only; it cannot run shell commands or arbitrary code."

    def __init__(self, data_tool: DataAnalysisTool | None = None) -> None:
        self._data_tool = data_tool or DataAnalysisTool()

    def analyze(self, relative_path: str | None = None) -> dict[str, object]:
        if not relative_path:
            return {"status": "NO_DATASET", "message": "未选择可分析的 CSV 或 XLSX 实验数据。", "boundary": "未执行任意代码或系统命令。"}
        try:
            result = self._data_tool.summarize(relative_path)
        except (OSError, ValueError) as error:
            return {"status": "DATASET_UNAVAILABLE", "message": str(error), "boundary": "未执行任意代码或系统命令。"}
        return {"status": "completed", "summary": result, "boundary": "仅进行了允许的数据结构与基础统计分析。"}
