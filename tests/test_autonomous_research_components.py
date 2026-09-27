"""Fast unit checks for ResearchOS v2 planning and safety boundaries."""

import unittest

from app.agent.research_result_evaluator import ResearchResultEvaluator
from app.agent.research_task_planner import ResearchTaskPlanner
from app.tools.tool_router import ResearchToolRouter


class AutonomousResearchComponentsTest(unittest.TestCase):
    def test_goal_aware_plan_selects_relevant_agents_and_tools(self) -> None:
        plan = ResearchTaskPlanner().build_plan(
            "分析研究趋势、创新机会与企业合作项目成果路径",
            has_ready_papers=True,
            workspace_assets=[{"path": "data.csv", "type": "CSV", "size": 20}],
        )
        self.assertIn("knowledge", plan["selected_agents"])
        self.assertIn("trend", plan["selected_agents"])
        self.assertIn("innovation", plan["selected_agents"])
        self.assertIn("project", plan["selected_agents"])
        self.assertIn("workspace_file", [task["tool"] for task in plan["tasks"]])
        self.assertTrue(all(task.get("tool_selection_reason") for task in plan["tasks"]))

    def test_reflection_never_claims_evidence_when_none_exists(self) -> None:
        reflection = ResearchResultEvaluator().evaluate([], [], False)
        self.assertFalse(reflection["has_evidence"])
        self.assertTrue(reflection["needs_more_retrieval"])
        self.assertIn("暂无可验证资料", reflection["next_decision"])
        self.assertFalse(reflection["goal_coverage"])

    def test_tool_catalog_is_explicit_and_bounded(self) -> None:
        catalog = ResearchToolRouter().catalog()
        self.assertEqual(
            {item["id"] for item in catalog},
            {"workspace_file", "knowledge_retrieval", "data_analysis", "document_generation", "project_planning"},
        )


if __name__ == "__main__":
    unittest.main()
