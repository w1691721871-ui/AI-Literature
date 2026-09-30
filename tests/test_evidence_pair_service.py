"""Fixture-only tests for deterministic complementary Evidence planning."""

from __future__ import annotations

import unittest

from app.services.evidence_claim_service import extract_evidence_claims
from app.services.evidence_pair_service import plan_complementary_retrieval


def evidence(content: str) -> dict[str, object]:
    return {
        "paper_id": "fixture-paper",
        "chunk_id": "fixture-chunk",
        "section": "Abstract",
        "content": content,
    }


class EvidencePairServiceTests(unittest.TestCase):
    def test_positive_claim_generates_negative_search(self) -> None:
        claim = extract_evidence_claims(
            evidence("CoT prompting improves reasoning performance.")
        )[0]
        plan = plan_complementary_retrieval([claim])
        self.assertIsNotNone(plan)
        self.assertIn("does not improve", plan["query"])

    def test_negative_claim_generates_positive_search(self) -> None:
        claim = extract_evidence_claims(
            evidence("CoT prompting does not improve reasoning performance.")
        )[0]
        plan = plan_complementary_retrieval([claim])
        self.assertIsNotNone(plan)
        self.assertIn("improves", plan["query"])
        self.assertNotIn("does not improve", plan["query"])

    def test_subject_and_property_are_preserved(self) -> None:
        claim = extract_evidence_claims(
            evidence("CoT prompting improves reasoning performance.")
        )[0]
        plan = plan_complementary_retrieval([claim])
        self.assertIn("cot prompting", plan["query"])
        self.assertIn("performance", plan["query"])

    def test_duplicate_query_is_not_generated(self) -> None:
        claim = extract_evidence_claims(
            evidence("CoT prompting improves reasoning performance.")
        )[0]
        first = plan_complementary_retrieval([claim])
        self.assertIsNotNone(first)
        self.assertIsNone(plan_complementary_retrieval([claim], {first["query"]}))

    def test_real_cot_pair_fixture_uses_opposite_direction_query(self) -> None:
        # Sentences are exact, user-uploaded PDF Evidence text represented as
        # a no-write fixture; no production paper/chunk/index is changed.
        claim = extract_evidence_claims(evidence(
            "Experiments on three large language models show that "
            "chain-of-thought prompting improves performance on a range of "
            "arithmetic, commonsense, and symbolic reasoning tasks."
        ))[0]
        plan = plan_complementary_retrieval([claim])
        self.assertEqual(plan["reason"], "search_opposite_claim")
        self.assertIn("does not improve performance", plan["query"])


if __name__ == "__main__":
    unittest.main()
