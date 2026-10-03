"""Evidence-bound research summaries, trends and gap candidates."""
from __future__ import annotations
from collections import Counter

class ResearchEvidenceAnalyzer:
    def analyze(self, evidence: list[dict[str, object]], question: str) -> dict[str, object]:
        approved=[item for item in evidence if str(item.get("status") or "").upper() in {"APPROVED","VERIFIED"}]
        if not approved:return {"status":"INSUFFICIENT_EVIDENCE","summary":"No approved Evidence is available; no trend or gap conclusion was generated.","themes":[],"trends":[],"gap_candidates":[],"supporting_evidence":[]}
        tokens=Counter(word.lower() for item in approved for word in str(item.get("title") or item.get("claim") or "").replace("-"," ").split() if len(word)>4)
        themes=[word for word,_ in tokens.most_common(4)]
        refs=[{"source":item.get("source"),"title":item.get("title"),"confidence":item.get("confidence")} for item in approved]
        trends=[{"theme":theme,"statement":f"Approved Evidence repeatedly references {theme}.","evidence_sources":[ref["source"] for ref in refs if theme in str(ref["title"] or "").lower()]} for theme in themes]
        gaps=[{"area":theme,"statement":f"Coverage for {theme} is limited to the currently approved Evidence set and requires human review.","status":"CANDIDATE_GAP","evidence_sources":[ref["source"] for ref in refs if theme in str(ref["title"] or "").lower()]} for theme in themes if sum(theme in str(ref["title"] or "").lower() for ref in refs)==1]
        return {"status":"EVIDENCE_BOUND_INSIGHT","summary":f"Analysis is based on {len(approved)} approved Evidence records for: {question[:240]}","themes":themes,"trends":trends,"gap_candidates":gaps,"supporting_evidence":refs,"confidence":round(sum(float(item.get("confidence") or 0) for item in approved)/len(approved),2)}
