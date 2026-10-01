"""Deterministic, dependency-light parsers for approved enterprise input formats."""
from __future__ import annotations
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from pypdf import PdfReader


class DocumentParserService:
    """Returns transient parsing facts. Callers persist only a compact summary."""
    def parse(self, filename: str, content: bytes, file_type: str) -> dict[str, object]:
        if file_type == "PDF": return self._pdf(content)
        if file_type == "DOCX": return self._docx(content)
        if file_type == "XLSX": return self._xlsx(content)
        if file_type == "PPTX": return self._pptx(content)
        if file_type == "IMAGE": return self._image(content)
        if file_type == "CODE": return self._code(filename, content)
        return self._text(content)

    @staticmethod
    def _clean(parts: list[str]) -> list[str]:
        return [re.sub(r"\s+", " ", part).strip() for part in parts if re.sub(r"\s+", " ", part).strip()]

    def _pdf(self, content: bytes) -> dict[str, object]:
        reader = PdfReader(io.BytesIO(content)); pages = self._clean([(page.extract_text() or "") for page in reader.pages])
        return {"text": "\n".join(pages), "structure": {"pages": len(reader.pages), "title": pages[0][:120] if pages else ""}, "limitations": "仅提取可复制文本；扫描页或加密页可能无法解析。"}

    def _docx(self, content: bytes) -> dict[str, object]:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
        paragraphs = self._clean(["".join(node.itertext()) for node in root.findall(".//{*}p")])
        return {"text": "\n".join(paragraphs), "structure": {"paragraphs": len(paragraphs), "headings": paragraphs[:5]}, "limitations": "解析 DOCX 正文结构，不解释图表或批注。"}

    def _xlsx(self, content: bytes) -> dict[str, object]:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            shared = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml")); shared = self._clean(["".join(x.itertext()) for x in shared_root.findall(".//{*}si")])
            sheets = []
            for name in sorted(x for x in archive.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", x)):
                root = ET.fromstring(archive.read(name)); rows = root.findall(".//{*}row"); first = rows[0] if rows else None; headers = []
                if first is not None:
                    for cell in first.findall("{*}c"):
                        value = cell.findtext("{*}v", default="")
                        headers.append(shared[int(value)] if cell.get("t") == "s" and value.isdigit() and int(value) < len(shared) else value)
                sheets.append({"sheet": Path(name).stem, "rows": len(rows), "fields": self._clean(headers)[:30]})
        text = " ".join(" ".join(x["fields"]) for x in sheets)
        return {"text": text, "structure": {"sheets": sheets, "sheet_count": len(sheets)}, "limitations": "仅提取工作表、首行字段和行数；不推断实验结论。"}

    def _pptx(self, content: bytes) -> dict[str, object]:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            slides = []
            for name in sorted(x for x in archive.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", x)):
                root = ET.fromstring(archive.read(name)); values = self._clean([node.text or "" for node in root.findall(".//{*}t")]); slides.append(values)
        text = "\n".join(" ".join(item) for item in slides)
        return {"text": text, "structure": {"slides": len(slides), "titles": [item[0] for item in slides if item][:10]}, "limitations": "仅提取幻灯片文本；不解释图像、动画或图表。"}

    def _image(self, content: bytes) -> dict[str, object]:
        # OCR is optional. A missing engine is recorded honestly, never replaced with invented text.
        try:
            from PIL import Image
            import pytesseract
            text = pytesseract.image_to_string(Image.open(io.BytesIO(content)))
            return {"text": text.strip(), "structure": {"ocr_status": "COMPLETED"}, "limitations": "OCR 结果可能包含识别误差，需人工核验。"}
        except Exception:
            return {"text": "", "structure": {"ocr_status": "OCR_ENGINE_UNAVAILABLE"}, "limitations": "当前环境未配置可用 OCR 引擎；未提取或生成图像文字。"}

    def _code(self, filename: str, content: bytes) -> dict[str, object]:
        text = content.decode("utf-8", errors="replace"); ext = Path(filename).suffix.lower().lstrip(".") or "text"
        symbols = re.findall(r"(?m)^\s*(?:def|class|function|interface|export\s+(?:class|function))\s+([A-Za-z_]\w*)", text)
        return {"text": text[:60000], "structure": {"language": ext, "lines": len(text.splitlines()), "symbols": symbols[:30]}, "limitations": "只生成代码结构摘要；不会执行、导入或修改代码。"}

    def _text(self, content: bytes) -> dict[str, object]:
        text = content.decode("utf-8", errors="replace")
        return {"text": text[:60000], "structure": {"lines": len(text.splitlines())}, "limitations": "仅解析文本内容，不推断未明确陈述的需求。"}
