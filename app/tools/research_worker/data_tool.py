"""Bounded experiment-data summaries for Research Worker."""

import csv
from pathlib import Path

from app.tools.data_analysis_tool import DataAnalysisTool
from app.tools.workspace_file_tool import WorkspaceFileTool
from app.tools.research_worker.base import Tool


class DataTool(Tool):
    name = "data_tool"
    description = "对 CSV/XLSX 实验数据输出结构摘要；不执行任意 Python 代码。"

    def __init__(self, workspace_tool: WorkspaceFileTool | None = None) -> None:
        self._workspace = workspace_tool or WorkspaceFileTool()
        self._tool = DataAnalysisTool(self._workspace)

    def execute(self) -> dict[str, object]:
        data_assets = [item for item in self._workspace.scan() if item["type"] in {"CSV", "Excel"}]
        summaries: list[dict[str, object]] = []
        for asset in data_assets[:5]:
            try:
                summaries.append(self.analyze_file(str(asset["path"])))
            except ValueError as error:
                summaries.append({"file": asset["path"], "error": str(error)})
        return {"dataset_count": len(data_assets), "summaries": summaries, "boundary_note": "仅输出结构和基础规模摘要，不自动给出实验因果结论。"}

    def analyze_file(self, relative_path: str) -> dict[str, object]:
        """Return factual structure metrics for one allow-listed data file."""
        path = self._workspace._safe_path(relative_path)
        summary = self._tool.summarize(relative_path)
        if path.suffix.lower() != ".csv":
            return {"filename": relative_path, "type": "XLSX", "structure": {"row_count": summary.get("row_count"), "column_count": summary.get("column_count"), "fields": []}, "available_information": {"data_types": {}, "missing_values": {}, "data_size_bytes": path.stat().st_size}, "limitations": ["当前安全解析仅确认 XLSX 工作表规模；字段类型与缺失值需转换为 CSV 后进行精确统计。"], "row_count": summary.get("row_count", 0), "column_count": summary.get("column_count", 0)}
        profile = self._csv_profile(path)
        return {"filename": relative_path, "type": "CSV", "structure": {"row_count": profile["row_count"], "column_count": len(profile["fields"]), "fields": profile["fields"]}, "available_information": {"data_types": profile["data_types"], "missing_values": profile["missing_values"], "data_size_bytes": path.stat().st_size, "numeric_statistics": self._csv_numeric_statistics(relative_path)}, "limitations": ["统计基于前 500 行计算，用于结构检查，不代表实验因果结论。"], "row_count": profile["row_count"], "column_count": len(profile["fields"])}

    @staticmethod
    def _infer_type(values: list[str]) -> str:
        values = [item.strip() for item in values if item and item.strip()]
        if not values:
            return "unknown"
        try:
            [float(item) for item in values]
            return "number"
        except ValueError:
            return "text"

    def _csv_profile(self, path: Path) -> dict[str, object]:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            samples, missing = {field: [] for field in fields}, {field: 0 for field in fields}
            row_count = 0
            for row in reader:
                row_count += 1
                if row_count > 500:
                    break
                for field in fields:
                    value = row.get(field) or ""
                    samples[field].append(value)
                    if not value.strip():
                        missing[field] += 1
        return {"fields": fields, "row_count": row_count, "data_types": {field: self._infer_type(values) for field, values in samples.items()}, "missing_values": missing}

    def _csv_numeric_statistics(self, relative_path: str) -> dict[str, dict[str, float | int]]:
        """Compute bounded descriptive statistics for numeric CSV columns only."""
        path = self._workspace._safe_path(relative_path)
        values: dict[str, list[float]] = {}
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            rows = csv.DictReader(handle)
            for row_index, row in enumerate(rows):
                if row_index >= 500:
                    break
                for column, raw_value in row.items():
                    try:
                        value = float((raw_value or "").strip())
                    except ValueError:
                        continue
                    values.setdefault(column, []).append(value)
        return {
            column: {"count": len(items), "min": min(items), "max": max(items), "mean": round(sum(items) / len(items), 6)}
            for column, items in values.items() if items
        }
