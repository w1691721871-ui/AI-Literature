"""Fixture-only tests for the bounded ResearchOS P2 loop.

These tests use in-memory retrieval fixtures.  They never write SQLite,
FAISS, embeddings, or the production knowledge base.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app.agent.finite_research_loop import FiniteResearchLoop
from app.agent.research_master_agent import ResearchMasterAgent


def source(chunk_id: str, content: str = "该资料记录了可追溯的实验方法与结果。") -> dict[str, object]:
    return {
        "paper_id": f"paper-{chunk_id}",
        "chunk_id": chunk_id,
        "paper_title": f"资料 {chunk_id}",
        "filename": f"资料-{chunk_id}.pdf",
        "section": "方法章节",
        "content": content,
        "score": 0.8,
    }


class FixtureRetriever:
    def __init__(self, responses: list[list[dict[str, object]]]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def retrieve(self, question: str, paper_ids=None, top_k: int = 5):  # noqa: ANN001
        self.calls.append(question)
        return self.responses.pop(0) if self.responses else []


class FixedDiagnostics:
    def __init__(self, counts: dict[str, int]) -> None:
        self.counts = counts

    def run(self) -> dict[str, object]:
        return {"counts": self.counts}


class UnusedLoop:
    def __init__(self) -> None:
        self.called = False

    def execute(self, *args, **kwargs):  # noqa: ANN002, ANN003
        self.called = True
        return {}


class FiniteResearchLoopTest(unittest.TestCase):
    def loop(self, responses: list[list[dict[str, object]]], *, conflict=None) -> FiniteResearchLoop:
        return FiniteResearchLoop(
            FixtureRetriever(responses),
            query_rewriter=lambda value: value,
            conflict_detector=conflict or (lambda items: {
                "status": "no_conflict", "requires_human_review": True, "reason": "fixture",
            }),
        )

    def test_empty_knowledge_base_is_blocked_before_loop_and_model_calls(self) -> None:
        unused_loop = UnusedLoop()
        master = ResearchMasterAgent(
            retrieval_service=FixtureRetriever([]),
            finite_loop=unused_loop,
            diagnostic_service=FixedDiagnostics({"papers": 0, "chunks": 0, "embedded_chunks": 0}),
        )
        with self.assertRaises(ValueError):
            master.run_task("分析实验资料")
        self.assertFalse(unused_loop.called)

    def test_single_subtask_can_complete_with_evidence(self) -> None:
        loop = self.loop([[source("one")], [source("two")]])
        result = loop.execute("总结研究方法", {"detected_intents": ["knowledge_analysis"]})
        self.assertEqual(result["stop_reason"], "SUFFICIENT_EVIDENCE")
        self.assertEqual(result["retrieval_rounds"], 2)
        self.assertTrue(result["subtasks"][0]["evidence_refs"])

    def test_multiple_subtasks_keep_independent_evidence_scopes(self) -> None:
        loop = self.loop([[source("one")], [source("two")]])
        result = loop.execute("比较方法差异", {"detected_intents": ["comparison"]})
        first, second = result["subtasks"][:2]
        self.assertNotEqual(first["evidence_refs"], second["evidence_refs"])
        self.assertEqual(result["stop_reason"], "SUFFICIENT_EVIDENCE")

    def test_insufficient_evidence_creates_and_executes_a_replan_subtask(self) -> None:
        loop = self.loop([[], [], [source("new")]])
        result = loop.execute("分析研究方向", {"detected_intents": ["knowledge_analysis"]})
        self.assertEqual(result["retrieval_rounds"], 3)
        self.assertTrue(any(item["title"] == "补充证据检索" for item in result["subtasks"]))
        self.assertTrue(any(item["evidence_count"] for item in result["subtasks"]))
        self.assertEqual(len({item["subtask_id"] for item in result["subtasks"]}), len(result["subtasks"]))

    def test_repeated_evidence_stops_the_loop(self) -> None:
        repeated = source("same")
        loop = self.loop([[repeated], [repeated]])
        result = loop.execute("总结研究结果", {"detected_intents": ["knowledge_analysis"]})
        self.assertEqual(result["stop_reason"], "NO_NEW_EVIDENCE")
        self.assertEqual(result["subtasks"][-1]["decision"]["stop_reason"], "NO_NEW_EVIDENCE")

    def test_conflict_requires_human_review_without_auto_resolution(self) -> None:
        conflict = lambda items: {
            "status": "potential_conflict", "requires_human_review": True, "reason": "fixture conflict",
        }
        loop = self.loop([[source("one")], [source("two")]], conflict=conflict)
        result = loop.execute("分析材料结果", {"detected_intents": ["knowledge_analysis"]})
        self.assertEqual(result["stop_reason"], "NEEDS_HUMAN_REVIEW")
        self.assertTrue(result["requires_human_review"])

    def test_complementary_retrieval_pairs_opposing_claims_once(self) -> None:
        positive = source("positive", "CoT prompting improves performance on arithmetic tasks.")
        negative = source("negative", "CoT prompting does not improve model performance on spatial tasks.")
        retriever = FixtureRetriever([[positive], [negative]])
        loop = FiniteResearchLoop(retriever, query_rewriter=lambda value: value)
        result = loop.execute("比较 CoT prompting 在不同任务条件下的性能影响", {
            "detected_intents": ["comparison"],
        })
        self.assertEqual(result["stop_reason"], "NEEDS_HUMAN_REVIEW")
        self.assertEqual(result["retrieval_rounds"], 2)
        self.assertEqual(len(retriever.calls), 2)
        self.assertTrue(result["subtasks"][0]["complementary_retrieval"])
        self.assertIn(
            "complementary_retrieval",
            [event["phase"] for event in result["execution_timeline"]],
        )

    def test_complementary_retrieval_respects_retrieval_budget(self) -> None:
        positive = source("positive", "CoT prompting improves performance on arithmetic tasks.")
        retriever = FixtureRetriever([[positive]])
        loop = FiniteResearchLoop(retriever, query_rewriter=lambda value: value)
        loop.MAX_RETRIEVAL_ROUNDS = 1
        result = loop.execute("比较 CoT prompting 在不同任务条件下的性能影响", {
            "detected_intents": ["comparison"],
        })
        self.assertEqual(result["stop_reason"], "MAX_RETRIEVAL_ROUNDS_REACHED")
        self.assertEqual(len(retriever.calls), 1)

    def test_paired_conflict_reaches_master_synthesis_context(self) -> None:
        positive = source("positive", "CoT prompting improves performance on arithmetic tasks.")
        negative = source("negative", "CoT prompting does not improve model performance on spatial tasks.")
        retriever = FixtureRetriever([[positive], [negative]])
        loop = FiniteResearchLoop(retriever, query_rewriter=lambda value: value)
        master = ResearchMasterAgent(
            retrieval_service=retriever,
            finite_loop=loop,
            diagnostic_service=FixedDiagnostics({"papers": 1, "chunks": 2, "embedded_chunks": 2}),
        )
        payload = {
            "executive_summary": "资料存在条件差异，待人工复核。",
            "literature_analysis": {}, "knowledge_insights": {}, "trend_insights": {},
            "innovation_opportunities": {}, "project_plan": {}, "report": {},
        }
        with patch("app.agent.research_master_agent.complete_research_prompt", return_value=json.dumps(payload)) as synthesis:
            result = master.run_task("比较 CoT prompting 在不同任务条件下的性能影响")
        self.assertEqual(result["finite_loop"]["stop_reason"], "NEEDS_HUMAN_REVIEW")
        self.assertEqual(result["conflict_report"]["status"], "context_difference")
        self.assertTrue(result["conflict_report"]["requires_human_review"])
        self.assertEqual(synthesis.call_count, 1)
        self.assertIn("context_difference", synthesis.call_args.args[0])
        self.assertIn("paper-positive:positive", synthesis.call_args.args[0])
        self.assertIn("paper-negative:negative", synthesis.call_args.args[0])

    def test_max_steps_stops_before_retrieval(self) -> None:
        loop = self.loop([[source("one")]])
        loop.MAX_STEPS = 2
        result = loop.execute("分析材料结果", {"detected_intents": ["knowledge_analysis"]})
        self.assertEqual(result["stop_reason"], "MAX_STEPS_REACHED")
        self.assertEqual(result["retrieval_rounds"], 0)

    def test_max_retrieval_rounds_stops_additional_subtasks(self) -> None:
        loop = self.loop([[source("one")], [source("two")]])
        loop.MAX_RETRIEVAL_ROUNDS = 1
        result = loop.execute("总结研究方法", {"detected_intents": ["knowledge_analysis"]})
        self.assertEqual(result["stop_reason"], "MAX_RETRIEVAL_ROUNDS_REACHED")
        self.assertEqual(result["retrieval_rounds"], 1)

    def test_max_model_calls_reserves_final_synthesis_budget(self) -> None:
        loop = self.loop([[source("one")]])
        loop.MAX_MODEL_CALLS = 1
        result = loop.execute("分析材料结果", {"detected_intents": ["knowledge_analysis"]})
        self.assertEqual(result["stop_reason"], "MAX_MODEL_CALLS_REACHED")
        self.assertEqual(result["model_calls"], 0)

    def test_trace_contains_real_execution_fields(self) -> None:
        loop = self.loop([[source("one")], [source("two")]])
        result = loop.execute("总结研究方法", {"detected_intents": ["knowledge_analysis"]})
        expected = {
            "subtask_id", "retrieval_round", "phase", "tool", "evidence_count",
            "validation_status", "conflict_status", "decision", "stop_reason",
        }
        self.assertTrue(all(expected.issubset(event) for event in result["execution_timeline"]))

    def test_final_synthesis_context_preserves_subtask_conflict_and_stop_data(self) -> None:
        loop_result = {
            "stop_reason": "NEEDS_HUMAN_REVIEW",
            "requires_human_review": True,
            "subtasks": [{
                "subtask_id": "subtask_1",
                "research_question": "比较材料方法",
                "intermediate_result": "已获得可追溯资料。",
                "evidence_refs": [{"evidence_id": "paper-a:chunk-1"}],
                "validation": {"status": "requires_human_review"},
                "conflict_report": {"status": "potential_conflict", "conflicts": [{"evidence_refs": []}]},
                "decision": {"status": "sufficient", "stop_reason": "SUFFICIENT_EVIDENCE"},
            }],
        }
        context = ResearchMasterAgent._build_loop_synthesis_context(
            "比较材料方法", loop_result, [source("one")]
        )
        self.assertEqual(context["stop_reason"], "NEEDS_HUMAN_REVIEW")
        self.assertTrue(context["requires_human_review"])
        self.assertEqual(context["subtasks"][0]["subtask_id"], "subtask_1")
        self.assertEqual(context["subtasks"][0]["conflict_report"]["status"], "potential_conflict")
        self.assertTrue(context["subtasks"][0]["evidence_refs"])

    def test_shared_model_budget_counts_rewrites_and_final_synthesis(self) -> None:
        # The first subtask has no usable evidence; the normal second task and
        # the executed replan then provide independent, traceable evidence.
        retriever = FixtureRetriever([[], [source("two")], [source("new")]])
        loop = FiniteResearchLoop(
            retriever,
            query_rewriter=lambda value: value,
            conflict_detector=lambda items: {"status": "no_conflict", "requires_human_review": True},
        )
        master = ResearchMasterAgent(
            retrieval_service=retriever,
            finite_loop=loop,
            diagnostic_service=FixedDiagnostics({"papers": 1, "chunks": 1, "embedded_chunks": 1}),
        )
        payload = {
            "executive_summary": "依据资料形成待人工复核的结论。",
            "literature_analysis": {}, "knowledge_insights": {}, "trend_insights": {},
            "innovation_opportunities": {}, "project_plan": {}, "report": {},
        }
        with patch("app.agent.research_master_agent.complete_research_prompt", return_value=json.dumps(payload)) as synthesis:
            result = master.run_task("分析研究方向")
        self.assertEqual(result["finite_loop"]["model_calls"], 4)
        self.assertEqual(result["finite_loop"]["max_model_calls"], 4)
        self.assertEqual(synthesis.call_count, 1)
        self.assertIn("subtask_1", synthesis.call_args.args[0])
        self.assertIn("stop_reason", synthesis.call_args.args[0])
        with self.assertRaises(RuntimeError):
            FiniteResearchLoop.consume_model_call({"model_calls": 4, "max_model_calls": 4})

    def test_low_relevance_traceable_sources_trigger_replan_and_safe_stop(self) -> None:
        unrelated = []
        for identifier in ("unrelated-one", "unrelated-two", "unrelated-three"):
            item = source(identifier)
            item["score"] = 0.2
            unrelated.append([item])
        loop = self.loop(unrelated)
        result = loop.execute("评估与资料无关的材料耐酸性能", {"detected_intents": ["knowledge_analysis"]})
        self.assertTrue(any(item.get("replan_for") == "subtask_1" for item in result["subtasks"]))
        self.assertEqual(result["stop_reason"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("相关且可追溯", result["subtasks"][0]["decision"]["missing_evidence"][0])

    def test_evaluator_missing_evidence_is_used_by_replan_question(self) -> None:
        class GapEvaluator:
            def __init__(self) -> None:
                self.calls = 0

            def evaluate(self, sources, workspace_assets, master_completed, goal):  # noqa: ANN001
                self.calls += 1
                if self.calls == 1:
                    return {
                        "has_evidence": True, "source_integrity": True,
                        "needs_more_retrieval": True, "sufficient": False,
                        "missing_evidence": ["缺少不同实验条件下的对比证据"],
                    }
                return {
                    "has_evidence": True, "source_integrity": True,
                    "needs_more_retrieval": False, "sufficient": True,
                    "missing_evidence": [],
                }

        loop = FiniteResearchLoop(
            FixtureRetriever([[source("one")], [source("two")], [source("three")]]),
            evaluator=GapEvaluator(),
            query_rewriter=lambda value: value,
            conflict_detector=lambda items: {"status": "no_conflict", "requires_human_review": True},
        )
        result = loop.execute("分析材料方法", {"detected_intents": ["knowledge_analysis"]})
        replanned = next(item for item in result["subtasks"] if item["title"] == "补充证据检索")
        self.assertIn("缺少不同实验条件下的对比证据", replanned["research_question"])
        self.assertGreaterEqual(result["retrieval_rounds"], 3)


if __name__ == "__main__":
    unittest.main()
