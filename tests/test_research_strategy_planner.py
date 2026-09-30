"""Tests for public, deterministic Research Strategy plans."""

from __future__ import annotations

import unittest

from app.agent.research_strategy_planner import ResearchStrategyPlanner


class ResearchStrategyPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = ResearchStrategyPlanner()

    def test_comparison_strategy_generates_dynamic_dimensions(self) -> None:
        strategy = self.planner.plan("比较不同 RAG 方法的效果差异", {"detected_intents": ["comparison"]})
        self.assertEqual(strategy["strategy_type"], "comparison")
        self.assertEqual(
            [item["title"] for item in strategy["subtasks"]],
            ["方法机制比较", "性能与条件比较", "局限与验证边界"],
        )
        self._assert_public_schema(strategy)

    def test_gap_analysis_strategy_uses_gap_specific_subtasks(self) -> None:
        strategy = self.planner.plan(
            "寻找当前资料中的研究空白",
            {"detected_intents": ["gap"]},
            existing_evidence=[{"evidence_id": "paper-a:chunk-1"}],
            research_gap=["缺少不同实验条件下的对比结果"],
        )
        self.assertEqual(strategy["strategy_type"], "gap_analysis")
        self.assertIn("未解决问题", [item["title"] for item in strategy["subtasks"]])
        self.assertIn("已关联 1 条 Evidence", " ".join(strategy["reasoning_basis"]))
        self.assertIn("缺少不同实验条件", " ".join(strategy["reasoning_basis"]))

    def test_evidence_gap_replan_is_a_distinct_executable_task(self) -> None:
        adjustment = self.planner.replan(
            "分析研究方向",
            "检索现有研究资料",
            ["缺少不同实验条件下的对比证据"],
            {"detected_intents": ["direction"]},
        )
        self.assertEqual(adjustment["title"], "补充证据检索")
        self.assertIn("缺少不同实验条件下的对比证据", adjustment["research_question"])
        self.assertIn("可追溯", adjustment["expected_evidence"])

    def test_plan_contains_no_internal_reasoning_or_prompt_fields(self) -> None:
        strategy = self.planner.plan("总结当前研究资料")
        forbidden = {"prompt", "chain_of_thought", "reasoning_trace", "token", "internal_reasoning"}
        self.assertFalse(forbidden & set(strategy))
        self._assert_public_schema(strategy)

    def _assert_public_schema(self, strategy: dict[str, object]) -> None:
        self.assertEqual(
            set(strategy),
            {"strategy_type", "research_objective", "subtasks", "reasoning_basis", "expected_evidence", "stop_condition"},
        )
        self.assertTrue(strategy["subtasks"])
        for subtask in strategy["subtasks"]:
            self.assertEqual(
                set(subtask),
                {"title", "research_question", "expected_evidence", "purpose"},
            )


if __name__ == "__main__":
    unittest.main()
