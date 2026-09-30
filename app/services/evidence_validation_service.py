"""Small, deterministic checks for evidence-grounded ResearchOS output.

This is deliberately not an automated fact checker.  It validates only
observable properties of the retrieved sources and the returned citation
markers, then asks for human review where claim-level validation is not
possible from local metadata alone.
"""

from __future__ import annotations

import re


def validate_evidence_grounding(
    sources: list[dict[str, object]], output_text: str = ""
) -> dict[str, object]:
    """Return factual evidence-coverage signals without inventing confidence."""
    valid_sources = [
        source for source in sources
        if str(source.get("paper_id", "")).strip()
        and str(source.get("section", "")).strip()
        and str(source.get("content", "")).strip()
    ]
    scores = [
        float(source.get("score", 0.0)) for source in valid_sources
        if isinstance(source.get("score", 0.0), (int, float))
    ]
    cited_indexes = {int(item) for item in re.findall(r"\[证据\s*(\d+)\]", output_text)}
    source_count = len(sources)
    valid_count = len(valid_sources)
    citation_count = len(cited_indexes)
    if not valid_count:
        status = "insufficient_evidence"
        message = "暂无可验证资料，不能将输出视为科研结论。"
    elif output_text and not citation_count:
        status = "requires_validation"
        message = "已检索到资料，但输出未包含可识别的证据编号；需要人工复核。"
    else:
        status = "requires_human_review"
        message = "已关联可追溯资料；结论仍需由科研负责人核验，不代表事实已被自动验证。"
    return {
        "status": status,
        "source_count": source_count,
        "valid_source_count": valid_count,
        "average_relevance": round(sum(scores) / len(scores), 4) if scores else None,
        "citation_marker_count": citation_count,
        "requires_human_review": True,
        "message": message,
    }
