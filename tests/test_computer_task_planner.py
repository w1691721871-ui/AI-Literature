import unittest

from app.services.computer_task_planner import ComputerTaskPlanner


class ComputerTaskPlannerTests(unittest.TestCase):
    def test_plan_is_workspace_bound_and_evidence_gated(self):
        mission = {"id": "m1", "workspace_id": "w1", "goal": "Research recent papers and prepare a report"}
        context = {"workspace": {"id": "w1"}, "knowledge": {"traceable_evidence_refs": []}}
        plan = ComputerTaskPlanner().plan(mission, context)
        self.assertEqual(plan["steps"][0]["skill_id"], "browser_research")
        self.assertIn("evidence_validation", [step["skill_id"] for step in plan["steps"]])
        self.assertNotIn("prompt", str(plan).lower())

    def test_cross_workspace_context_is_rejected(self):
        with self.assertRaises(PermissionError):
            ComputerTaskPlanner().plan({"id": "m", "workspace_id": "w1", "goal": "research"}, {"workspace": {"id": "w2"}})

    def test_evidence_validation_is_retained_when_multiple_skills_match(self):
        mission = {"id": "m1", "workspace_id": "w1", "goal": "Research data, prepare a document and report"}
        plan = ComputerTaskPlanner().plan(mission, {"workspace": {"id": "w1"}, "knowledge": {}})
        self.assertLessEqual(len(plan["steps"]), ComputerTaskPlanner.MAX_STEPS)
        self.assertIn("evidence_validation", [step["skill_id"] for step in plan["steps"]])

    def test_plan_uses_only_authorized_computer_memory_metadata_and_names_verification(self):
        mission = {"id": "m1", "workspace_id": "w1", "goal": "Research recent papers"}
        plan = ComputerTaskPlanner().plan(mission, {
            "workspace": {"id": "w1"}, "knowledge": {},
            "computer_memory": [{"memory_type": "WORK_PREFERENCE", "summary": "Use a concise research brief."}],
        })
        self.assertEqual(plan["context_basis"]["authorized_computer_memory"], 1)
        self.assertTrue(all(step.get("verification") for step in plan["steps"]))
        self.assertNotIn("concise research brief", str(plan))
