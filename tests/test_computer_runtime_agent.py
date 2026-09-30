"""Fixture-only P16 runtime tests; no production database, FAISS, or files."""

from __future__ import annotations

import unittest

from app.agent.research_computer_runtime_agent import ResearchComputerRuntimeAgent


class _Service:
    def __init__(self): self.items = {}; self.count = 0
    def get(self, task_id): return self.items[task_id]
    def update_session(self, task_id, **data): self.items[task_id].update(data); return self.items[task_id]


class _Operator:
    def __init__(self): self.service = _Service(); self.event_rows = []
    def create_task(self, goal, mode, workspace_id):
        self.service.count += 1; task = {"id": f"runtime-{self.service.count}", "user_goal": goal, "status": "planning", "plan": [], "artifact": {}, "actions": []}; self.service.items[task["id"]] = task; return task
    def execute(self, task_id):
        item = self.service.get(task_id); item.update({"status": "waiting_approval", "artifact": {"type": "code_optimization_plan"}, "actions": [{"id": "action-1", "status": "PENDING_APPROVAL"}]}); return item
    def approve(self, action_id, note):
        item = next(iter(self.service.items.values())); item["status"] = "completed"; return item
    def get(self, task_id):
        item = dict(self.service.get(task_id)); item["patches"] = [{"id": "patch-1", "status": "WAITING_APPROVAL", "file_path": "frontend/styles.css"}]; return item
    def events(self, task_id): return [event for event in self.event_rows if event["task_id"] == task_id]
    def _event(self, task_id, agent, event_type, status, message, summary=""):
        self.event_rows.append({"task_id": task_id, "agent_name": agent, "event_type": event_type, "status": status, "message": message, "result_summary": summary})


class _Explorer:
    def map(self): return {"status": "OBSERVED", "workspace_map": {"project_type": "Python + FastAPI"}}


class _Intelligence:
    def analyze(self): return {"python_files": 2, "javascript_files": 1}


class _Sandbox:
    def validate(self, operation): return {"status": "COMPLETED", "verification": "SUCCESS", "result": {"operation": operation}}


class RuntimeAgentTests(unittest.TestCase):
    def setUp(self): self.operator = _Operator(); self.agent = ResearchComputerRuntimeAgent(self.operator, _Explorer(), _Intelligence(), _Sandbox())

    def test_runtime_generates_structured_execution_plan(self):
        task = self.agent.create("分析 Python 项目性能问题并优化")
        self.assertEqual(task["runtime_status"], "PLANNING")
        self.assertEqual(len(task["plan"]), 4)
        self.assertIn("verification_method", task["plan"][0])

    def test_runtime_records_observation_and_code_analysis_before_operator_execution(self):
        task = self.agent.create("优化 Python 代码性能")
        output = self.agent.execute(task["id"])
        kinds = [event["event_type"] for event in output["events"]]
        self.assertIn("OBSERVING", kinds); self.assertIn("THINKING", kinds)
        self.assertEqual(output["runtime_status"], "WAITING_REVIEW")

    def test_artifacts_expose_patch_status_without_applying_it(self):
        task = self.agent.create("优化首页 UI")
        artifacts = self.agent.artifacts(task["id"])
        self.assertEqual(artifacts[0]["type"], "Code Patch")
        self.assertEqual(artifacts[0]["status"], "WAITING_APPROVAL")

    def test_approve_requires_existing_pending_action(self):
        task = self.agent.create("优化首页 UI"); self.agent.execute(task["id"])
        output = self.agent.approve(task["id"], "已确认")
        self.assertEqual(output["status"], "completed")

    def test_retry_has_three_attempt_limit_and_requires_failure(self):
        task = self.agent.create("分析项目")
        with self.assertRaises(ValueError): self.agent.retry(task["id"])
        item = self.operator.service.get(task["id"]); item["status"] = "failed"; item["artifact"] = {"recovery_attempts": 3}
        with self.assertRaises(ValueError): self.agent.retry(task["id"])


if __name__ == "__main__": unittest.main()
