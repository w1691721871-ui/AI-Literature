"""Safe discovery and reading for the local research workspace."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from app.services.database import PROJECT_ROOT
from app.services.pdf_service import extract_pdf_text


RESEARCH_WORKSPACE = PROJECT_ROOT / "research_workspace"
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".csv", ".xlsx"}


class WorkspaceFileTool:
    """Read only selected, local research files below ``research_workspace/``."""

    name = "workspace_file"

    def scan(self) -> list[dict[str, object]]:
        """Return a safe inventory; no contents are returned during scanning."""
        RESEARCH_WORKSPACE.mkdir(parents=True, exist_ok=True)
        assets: list[dict[str, object]] = []
        for candidate in sorted(RESEARCH_WORKSPACE.rglob("*")):
            if not candidate.is_file() or candidate.is_symlink() or candidate.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            resolved = candidate.resolve()
            if not resolved.is_relative_to(RESEARCH_WORKSPACE.resolve()):
                continue
            assets.append(
                {
                    "path": str(candidate.relative_to(RESEARCH_WORKSPACE)).replace("\\", "/"),
                    "type": self._asset_type(candidate.suffix),
                    "size": candidate.stat().st_size,
                }
            )
        return assets

    def read_text(self, relative_path: str, max_chars: int = 8_000) -> str:
        """Read text from a permitted workspace asset without path traversal."""
        path = self._safe_path(relative_path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = extract_pdf_text(path.read_bytes())
        elif suffix == ".docx":
            text = self._read_docx(path)
        elif suffix == ".txt":
            text = path.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".csv":
            text = self._read_csv(path)
        elif suffix == ".xlsx":
            text = "Excel 实验数据请通过 data_analysis 工具读取摘要。"
        else:
            raise ValueError("该文件类型不支持读取。")
        return " ".join(text.split())[:max_chars]

    @staticmethod
    def _asset_type(suffix: str) -> str:
        return {
            ".pdf": "PDF", ".docx": "DOCX", ".txt": "TXT", ".csv": "CSV", ".xlsx": "Excel",
        }.get(suffix.lower(), "文件")

    @staticmethod
    def _read_docx(path: Path) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                document = archive.read("word/document.xml")
            root = ElementTree.fromstring(document)
            return " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as error:
            raise ValueError("DOCX 文件无法读取。") from error

    @staticmethod
    def _read_csv(path: Path) -> str:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            return " ".join(" | ".join(row) for row in list(csv.reader(handle))[:30])

    @staticmethod
    def _safe_path(relative_path: str) -> Path:
        candidate = (RESEARCH_WORKSPACE / relative_path).resolve()
        if not candidate.is_relative_to(RESEARCH_WORKSPACE.resolve()) or not candidate.is_file():
            raise ValueError("文件不属于 Research Workspace 或不存在。")
        if candidate.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError("该文件类型不在允许范围内。")
        return candidate
