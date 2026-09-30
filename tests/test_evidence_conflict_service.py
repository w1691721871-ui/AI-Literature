"""Unit fixtures for conflict screening only; they never touch production data."""

import unittest

from app.services.evidence_conflict_service import detect_evidence_conflicts, normalize_evidence


def evidence(paper_id: str, chunk_id: str, content: str, section: str = "实验结果") -> dict[str, object]:
    return {
        "paper_id": paper_id,
        "chunk_id": chunk_id,
        "paper_title": f"测试资料 {paper_id}",
        "filename": f"fixture-{paper_id}.pdf",
        "section": section,
        "content": content,
        "score": 0.8,
    }


class EvidenceConflictServiceTests(unittest.TestCase):
    def test_opposing_comparable_sources_are_potential_conflict(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "方法 X 显著提高材料性能。"),
            evidence("paper-b", "chunk-b", "方法 X 未显著提高材料性能。"),
        ])
        self.assertEqual(report["status"], "potential_conflict")
        self.assertTrue(report["requires_human_review"])
        self.assertEqual(len(report["conflicts"]), 1)

    def test_different_temperature_contexts_are_not_direct_conflict(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "方法 X 在低温条件下显著提高材料性能。"),
            evidence("paper-b", "chunk-b", "方法 X 在高温条件下未显著提高材料性能。"),
        ])
        self.assertEqual(report["status"], "context_difference")
        self.assertTrue(report["requires_human_review"])

    def test_one_evidence_is_insufficient(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "方法 X 显著提高材料性能。"),
        ])
        self.assertEqual(report["status"], "insufficient_evidence")
        self.assertTrue(report["requires_human_review"])

    def test_consistent_direction_is_not_proof_of_agreement(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "方法 X 显著提高材料性能。"),
            evidence("paper-b", "chunk-b", "方法 X 明显改善材料性能。"),
        ])
        self.assertEqual(report["status"], "no_conflict")
        self.assertIn("不代表", str(report["reason"]))

    def test_same_paper_same_section_is_not_marked_as_conflict(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "方法 X 显著提高材料性能。"),
            evidence("paper-a", "chunk-b", "方法 X 未观察到明显性能提高。"),
        ])
        self.assertEqual(report["status"], "no_conflict")

    def test_english_opposing_same_subject_and_property_is_potential_conflict(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "Method X improves retrieval quality."),
            evidence("paper-b", "chunk-b", "Method X does not improve retrieval quality."),
        ])
        self.assertEqual(report["status"], "potential_conflict")
        self.assertTrue(report["requires_human_review"])
        item = report["conflicts"][0]
        self.assertEqual(item["evidence_refs"][0]["evidence_id"], "paper-a:chunk-a")
        self.assertEqual(item["evidence_refs"][1]["evidence_id"], "paper-b:chunk-b")

    def test_english_negation_is_not_misclassified_as_positive(self) -> None:
        for phrase in (
            "Method X does not improve retrieval quality.",
            "Method X does not increase retrieval quality.",
            "Method X does not reduce retrieval quality.",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(normalize_evidence(evidence("paper-a", "chunk-a", phrase))["claim_direction"], "negative")

    def test_different_subjects_are_not_a_conflict(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "Method X improves retrieval quality."),
            evidence("paper-b", "chunk-b", "Method Y does not improve retrieval quality."),
        ])
        self.assertEqual(report["status"], "no_conflict")
        self.assertFalse(report["requires_human_review"])

    def test_different_properties_are_not_a_conflict(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "Method X improves accuracy."),
            evidence("paper-b", "chunk-b", "Method X does not improve latency."),
        ])
        self.assertEqual(report["status"], "no_conflict")
        self.assertFalse(report["requires_human_review"])

    def test_english_context_difference_preserves_conditions(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "Method X improves retrieval quality on Dataset A."),
            evidence("paper-b", "chunk-b", "Method X does not improve retrieval quality on Dataset B."),
        ])
        self.assertEqual(report["status"], "context_difference")
        self.assertTrue(report["requires_human_review"])
        claims = report["conflicts"][0]["normalized_claims"]
        self.assertIn("dataset a", claims[0]["scope"])
        self.assertIn("dataset b", claims[1]["scope"])

    def test_same_direction_with_different_scope_is_not_a_conflict(self) -> None:
        report = detect_evidence_conflicts([
            evidence("paper-a", "chunk-a", "Method X improves retrieval quality on Dataset A."),
            evidence("paper-b", "chunk-b", "Method X improves retrieval quality on Dataset B."),
        ])
        self.assertEqual(report["status"], "no_conflict")
        self.assertFalse(report["requires_human_review"])


if __name__ == "__main__":
    unittest.main()
