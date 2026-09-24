"""Rule-based evidence quality summary for RAG citations."""


def build_source_quality(sources: list[dict[str, object]]) -> dict[str, object]:
    """Summarize retrieved evidence; this is retrieval quality, not factual accuracy."""
    scores = [float(source.get("score", 0.0)) for source in sources]
    average_score = sum(scores) / len(scores) if scores else 0.0
    if average_score > 0.8:
        level = "high"
    elif average_score >= 0.6:
        level = "medium"
    else:
        level = "low"
    return {
        "citation_count": len(sources),
        "average_score": round(average_score, 4),
        "evidence_level": level,
    }
