"""Sentence-level deterministic Claim Extraction fixtures only."""

import unittest

from app.services.evidence_claim_service import extract_evidence_claims
from app.services.evidence_conflict_service import detect_evidence_conflicts


def evidence(paper_id: str, chunk_id: str, content: str) -> dict[str, object]:
    return {
        "paper_id": paper_id,
        "chunk_id": chunk_id,
        "section": "Abstract",
        "filename": f"{paper_id}.pdf",
        "content": content,
        "score": 0.9,
    }


class EvidenceClaimServiceTests(unittest.TestCase):
    def test_positive_claim(self) -> None:
        claims = extract_evidence_claims(evidence("p", "c", "CoT prompting improves reasoning performance."))
        self.assertEqual(claims[0]["claim_direction"], "positive")
        self.assertEqual(claims[0]["direction"], "positive")

    def test_negative_claim_has_priority(self) -> None:
        claims = extract_evidence_claims(evidence("p", "c", "CoT prompting does not improve spatial reasoning performance."))
        self.assertEqual(claims[0]["claim_direction"], "negative")

    def test_one_chunk_can_produce_multiple_claims(self) -> None:
        claims = extract_evidence_claims(evidence(
            "p", "c", "CoT prompting improves performance on arithmetic tasks. CoT prompting does not improve performance on spatial tasks."
        ))
        self.assertEqual([claim["claim_direction"] for claim in claims], ["positive", "negative"])

    def test_real_cot_evidence_context_difference(self) -> None:
        # Exact sentences extracted from the two real PDFs uploaded through the
        # normal paper-library endpoint; fixture never writes production data.
        positive = evidence(
            "b8cb4bc0-1173-42f7-a564-bc436d4153c6",
            "366acc05-77f3-485a-b4e0-21ae70c442ad",
            "Experiments on three large language models show that chain-of-thought prompting improves performance on a range of arithmetic, commonsense, and symbolic reasoning tasks.",
        )
        negative = evidence(
            "c6fb2963-fc95-4a65-8491-2d9d1caa5cc4",
            "d3235df5-51fc-40e0-b7dc-c666b8c6ba01",
            "chain of thought (CoT) prompting does not improve model performance on complex multi-hop questions involving spatial relations.",
        )
        report = detect_evidence_conflicts([positive, negative])
        self.assertEqual(report["status"], "context_difference")
        self.assertTrue(report["requires_human_review"])
        claims = report["conflicts"][0]["normalized_claims"]
        self.assertEqual([claim["direction"] for claim in claims], ["positive", "negative"])


if __name__ == "__main__":
    unittest.main()
