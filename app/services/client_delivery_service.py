"""Generate a bounded client-delivery PDF from existing Worker run data only."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.services.database import WORK_DIRECTORY


class ClientDeliveryService:
    """Produces a minimal PDF without a new dependency or any scientific inference."""

    def preview(self, run: dict[str, object]) -> dict[str, object]:
        result = run.get("result", {}) if isinstance(run.get("result"), dict) else {}
        knowledge = result.get("knowledge_tool", {}) if isinstance(result.get("knowledge_tool"), dict) else {}
        file_result = result.get("file_tool", {}) if isinstance(result.get("file_tool"), dict) else {}
        return {
            "client_requirement": run.get("user_goal", ""),
            "ai_analysis": {"available_files": file_result.get("asset_count", 0), "evidence_count": knowledge.get("source_count", 0), "technical_route": "仅在存在可引用 Evidence 时由现有 Research Worker 形成待人工复核建议。"},
            "deliverables": ["技术分析报告", "项目规划（待人工确认）", "风险/资料不足说明", "下一步建议"],
            "evidence": knowledge.get("sources", []),
            "human_review_required": True,
            "boundary_note": "AI辅助生成，需人工审核；资料不足时不应将内容视为科研结论。",
        }

    def export_pdf(self, run: dict[str, object]) -> dict[str, str]:
        preview = self.preview(run)
        directory = WORK_DIRECTORY / "client_delivery_reports"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"client_delivery_{uuid4()}.pdf"
        # ASCII-only content intentionally avoids claiming a Unicode-capable PDF font.
        lines = [
            "ResearchOS Client Delivery Report",
            "AI-assisted report - Human review required",
            f"Client requirement: {self._ascii(preview['client_requirement'])[:140]}",
            f"Available files: {preview['ai_analysis']['available_files']}",
            f"Evidence references: {preview['ai_analysis']['evidence_count']}",
            "Deliverables: technical analysis / project plan / risk note / next actions",
            "Boundary: no scientific conclusion is generated when verifiable evidence is unavailable.",
        ]
        self._write_minimal_pdf(path, lines)
        return {"path": str(path.relative_to(WORK_DIRECTORY)), "notice": "AI辅助生成，需人工审核。"}

    @staticmethod
    def _ascii(value: object) -> str:
        return str(value).encode("ascii", "replace").decode("ascii")

    @staticmethod
    def _write_minimal_pdf(path: Path, lines: list[str]) -> None:
        content = "BT /F1 11 Tf 50 760 Td " + " ".join(f"({line.replace('(', '[').replace(')', ']')}) Tj 0 -18 Td" for line in lines) + " ET"
        objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>", "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>", f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
        output = ["%PDF-1.4\n"]
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(sum(len(part.encode("latin-1")) for part in output))
            output.append(f"{index} 0 obj\n{obj}\nendobj\n")
        xref = sum(len(part.encode("latin-1")) for part in output)
        output.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:]))
        output.append(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n")
        path.write_bytes("".join(output).encode("latin-1"))
