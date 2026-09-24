"""Small rule-based RAG retrieval quality evaluation for product display."""


def evaluate_retrieval(sources: list[dict[str, object]]) -> dict[str, object]:
    """Summarize returned evidence quality; it is not a factual-accuracy score."""
    scores = [max(0.0, min(1.0, float(source.get("score", 0.0)))) for source in sources]
    average_score = sum(scores) / len(scores) if scores else 0.0
    highest_score = max(scores, default=0.0)
    if highest_score >= 0.8 and average_score >= 0.65:
        quality = "excellent"
    elif highest_score >= 0.55 or average_score >= 0.45:
        quality = "good"
    else:
        quality = "normal"
    return {
        "retrieval_count": len(sources),
        "citation_count": len(sources),
        "average_score": round(average_score, 4),
        "highest_score": round(highest_score, 4),
        "retrieval_quality": quality,
    }
