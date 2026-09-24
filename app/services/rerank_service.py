"""Lightweight local reranking for a small FAISS candidate set."""

import re


def rerank_chunks(question: str, candidates: list[dict[str, object]], top_k: int = 5) -> list[dict[str, object]]:
    """Rerank FAISS candidates by hybrid relevance, coverage, and usable length."""
    keywords = _keywords(question)
    reranked: list[dict[str, object]] = []
    for candidate in candidates:
        content = str(candidate.get("content", ""))
        coverage = _coverage_score(keywords, content)
        hybrid = float(candidate.get("hybrid_score", candidate.get("score", 0.0)))
        length_score = min(len(content) / 900, 1.0)
        final_score = hybrid * 0.7 + coverage * 0.2 + length_score * 0.1
        reranked.append({
            **candidate,
            "keyword_score": round(coverage, 4),
            "score": round(final_score, 4),
        })
    reranked.sort(key=lambda item: float(item["score"]), reverse=True)
    return reranked[:top_k]


def keyword_coverage(question: str, content: str) -> float:
    """Expose the same deterministic keyword score used by hybrid retrieval."""
    return _coverage_score(_keywords(question), content)


def _keywords(text: str) -> list[str]:
    terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{1,}", text.lower())
    return list(dict.fromkeys(terms))


def _coverage_score(keywords: list[str], content: str) -> float:
    if not keywords:
        return 0.0
    normalized = content.lower()
    return sum(keyword in normalized for keyword in keywords) / len(keywords)
