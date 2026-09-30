"""P17 fixture tests; no production SQLite, FAISS, or source workspace writes."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.agent.research_autonomous_computer_agent import ResearchAutonomousComputerAgent
from app.tools.computer.workspace_action_engine import WorkspaceActionEngine


class _Storage:
    def __init__(self): self.rows = {}; self.items = {}; self.recovery = {}; self.count = 0
    def create(self, task_id, goal, plan):
        self.count += 1; row = {"id": f"runtime-{self.count}", "computer_task_id": task_id, "user_goal": goal, "status": "CREATED", "plan": plan, "loop_count": 0}; self.rows[row["id"]] = row; return dict(row)
    def get(self, rid): return dict(self.rows[rid])
    def update(self, rid, status=None, loop_count=None):
        if status is not None: self.rows[rid]["status"] = status
        if loop_count is not None: self.rows[rid]["loop_count"] = loop_count
        return dict(self.rows[rid])
    def add_artifact(self, rid, kind, name, status, metadata): self.items.setdefault(rid, []).append({"type": kind, "name": name, "status": status, "metadata": metadata}); return self.items[rid][-1]
    def artifacts(self, rid): return list(self.items.get(rid, []))
    def add_recovery(self, rid, attempt, status, summary): self.recovery.setdefault(rid, []).append({"attempt_number": attempt, "status": status, "summary": summary})
    def recoveries(self, rid): return list(self.recovery.get(rid, []))


class _Operator:
    def __init__(self): self.events = []
    def _event(self, task, agent, phase, status, message, summary=""): self.events.append({"agent_name": agent, "event_type": phase, "status": status, "message": message})


class _Runtime:
    def __init__(self): self.operator = _Operator(); self.items = {}; self.count = 0
    def create(self, goal, mode, workspace):
        self.count += 1; item = {"id": f"task-{self.count}", "user_goal": goal, "plan": [{"id": "observe"}], "runtime_status": "PLANNING", "artifacts": []}; self.items[item["id"]] = item; return item
    def execute(self, task_id):
        item = self.items[task_id]; item.update({"runtime_status": "WAITING_REVIEW", "artifacts": [{"type": "Code Patch", "status": "WAITING_APPROVAL", "path": "frontend/styles.css"}]}); return item
    def approve(self, task_id, note): self.items[task_id]["runtime_status"] = "COMPLETED"; return self.items[task_id]
    def get(self, task_id): return self.items[task_id]
    def timeline(self, task_id): return self.operator.events


class _Sandbox:
    def validate(self, _operation): return {"status": "COMPLETED", "verification": "SUCCESS"}


class AutonomousComputerTests(unittest.TestCase):
    def setUp(self): self.storage = _Storage(); self.runtime = _Runtime(); self.agent = ResearchAutonomousComputerAgent(self.runtime, self.storage, _Sandbox())

    def test_creates_persistent_plan_and_explainable_events(self):
        session = self.agent.create("分析当前项目代码并寻找优化点")
        self.assertEqual(session["status"], "CREATED")
        self.assertTrue(session["timeline"])

    def test_execution_generates_patch_artifact_but_does_not_apply(self):
        session = self.agent.create("优化首页 UI")
        result = self.agent.execute(session["id"])
        self.assertEqual(result["status"], "EDITING")
        self.assertEqual(result["artifacts"][0]["status"], "WAITING_APPROVAL")

    def test_approval_runs_verification_and_marks_success(self):
        session = self.agent.create("优化首页 UI"); self.agent.execute(session["id"])
        result = self.agent.approve(session["id"], "已批准")
        self.assertEqual(result["status"], "SUCCESS")

    def test_recovery_is_bounded(self):
        session = self.agent.create("分析代码"); self.storage.update(session["id"], status="FAILED", loop_count=5)
        result = self.agent.retry(session["id"])
        self.assertEqual(result["status"], "FAILED")

    def test_workspace_action_engine_blocks_sensitive_files_and_only_proposes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "app.py").write_text("print('a')\n", encoding="utf-8")
            engine = WorkspaceActionEngine(root)
            proposal = engine.propose("app.py", "append", "print('b')\n")
            self.assertEqual(proposal["status"], "WAITING_APPROVAL")
            self.assertEqual((root / "app.py").read_text(encoding="utf-8"), "print('a')\n")
            with self.assertRaises(ValueError): engine.read(".env")


if __name__ == "__main__": unittest.main()
