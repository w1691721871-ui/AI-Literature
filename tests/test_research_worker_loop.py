"""Focused tests for Research Worker's user-visible loop decisions."""

import unittest

from app.agent.research_worker_loop.critic import ResearchWorkerCritic
from app.agent.research_worker_loop.observer import ResearchWorkerObserver
from app.agent.research_worker_loop.planner import ResearchWorkerPlanner
from app.agent.research_worker_loop.replanner import ResearchWorkerReplanner


class ResearchWorkerLoopTest(unittest.TestCase):
    def test_planner_records_tool_reasons(self) -> None:
        plan = ResearchWorkerPlanner().build("分析实验数据", [
            {"name": "file_tool", "reason": "读取资料"},
            {"name": "data_tool", "reason": "检查字段"},
            {"name": "document_tool", "reason": "生成报告"},
        ])
        self.assertEqual(len(plan), 3)
        self.assertEqual(plan[1]["task_name"], "分析数据结构")
        self.assertEqual(plan[1]["required_tool"], "data_tool")
        self.assertTrue(plan[1]["expected_output"])
        self.assertEqual(plan[1]["reason"], "检查字段")

    def test_empty_material_replans_without_claiming_conclusion(self) -> None:
        observation = ResearchWorkerObserver().inspect({"asset_count": 0}, None, {"source_count": 0})
        critic = ResearchWorkerCritic().evaluate("分析研究方向", observation)
        replan = ResearchWorkerReplanner().adjust([], critic, observation)
        self.assertTrue(critic["needs_replan"])
        self.assertFalse(critic["has_verifiable_material"])
        self.assertIn("补充并索引科研资料", replan[0]["action"])

    def test_bad_dataset_replans_to_quality_report(self) -> None:
        observation = ResearchWorkerObserver().inspect(
            {"asset_count": 1},
            {"dataset_count": 1, "summaries": [{"column_count": 0}]},
            {"source_count": 0},
        )
        critic = ResearchWorkerCritic().evaluate("分析实验数据", observation)
        replan = ResearchWorkerReplanner().adjust([], critic, observation)
        self.assertTrue(observation["needs_adjustment"])
        self.assertEqual(replan[0]["action"], "生成数据质量报告")


if __name__ == "__main__":
    unittest.main()
