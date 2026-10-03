"""Deterministic source-candidate scoring; never upgrades a candidate to Evidence."""
from __future__ import annotations


class SourceQualityService:
    def evaluate(self, candidates: list[dict[str, object]], topic: str) -> list[dict[str, object]]:
        seen: set[str] = set(); out = []
        tokens = {word for word in str(topic).lower().split() if len(word) > 2}
        for candidate in candidates:
            url = str(candidate.get("url") or "")
            if not url or url in seen: continue
            seen.add(url)
            title = str(candidate.get("title") or "")
            overlap = sum(token in title.lower() for token in tokens)
            score = min(100, 45 + overlap * 12 + (18 if "doi.org" in url else 0))
            out.append({**candidate, "candidate_score": score, "source_quality": "SCHOLARLY_METADATA" if "doi.org" in url else "PUBLIC_METADATA", "status": "CANDIDATE", "evaluation_summary": "Candidate relevance and source metadata were scored; existing Evidence validation is still required."})
        return sorted(out, key=lambda item: int(item["candidate_score"]), reverse=True)
