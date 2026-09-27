"""Small, safe summaries for CSV/XLSX experimental datasets.

This is intentionally not arbitrary Python execution. It performs bounded
descriptive analysis only and keeps the autonomous workspace safe.
"""

from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from app.tools.workspace_file_tool import WorkspaceFileTool


class DataAnalysisTool:
    name = "data_analysis"

    def __init__(self, file_tool: WorkspaceFileTool | None = None) -> None:
        self._file_tool = file_tool or WorkspaceFileTool()

    def summarize(self, relative_path: str) -> dict[str, object]:
        path = self._file_tool._safe_path(relative_path)
        if path.suffix.lower() == ".csv":
            return self._summarize_csv(path)
        if path.suffix.lower() == ".xlsx":
            return self._summarize_xlsx(path)
        raise ValueError("数据分析工具仅支持 CSV 或 XLSX 文件。")

    @staticmethod
    def _summarize_csv(path: Path) -> dict[str, object]:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            rows = list(csv.reader(handle))
        headers = rows[0] if rows else []
        return {
            "file": path.name,
            "format": "CSV",
            "row_count": max(0, len(rows) - 1),
            "column_count": len(headers),
            "columns": headers[:30],
            "note": "仅完成结构摘要；统计结论仍需结合实验设计与人工复核。",
        }
    @staticmethod
    def _summarize_xlsx(path: Path) -> dict[str, object]:
        try:
            with zipfile.ZipFile(path) as archive:
                names = [name for name in archive.namelist() if name.startswith("xl/worksheets/") and name.endswith(".xml")]
                row_count = 0
                max_columns = 0
                for name in names[:20]:
                    root = ElementTree.fromstring(archive.read(name))
                    rows = [node for node in root.iter() if node.tag.endswith("}row")]
                    row_count += len(rows)
                    for row in rows:
                        max_columns = max(max_columns, len([node for node in row if node.tag.endswith("}c")]))
        except (zipfile.BadZipFile, ElementTree.ParseError) as error:
            raise ValueError("Excel 文件无法读取。") from error
        return {
            "file": path.name,
            "format": "XLSX",
            "sheet_count": len(names),
            "row_count": row_count,
            "column_count": max_columns,
            "note": "仅完成表格结构摘要；未执行任意代码或自动生成实验结论。",
        }
