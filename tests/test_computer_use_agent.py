"""P18 Computer Use tests use a temporary workspace and in-memory SQLite only."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.research_computer_use_agent import ResearchComputerUseAgent
from app.models.computer_file_change import ComputerFileChange
from app.services.computer_use_service import ComputerUseService
from app.services.database import Base
from app.tools.computer.workspace_action_engine import WorkspaceActionEngine


class _Storage:
    def __init__(self): self.rows = {}; self.artifacts = []
    def get(self, rid): return self.rows[rid]
    def add_artifact(self, rid, kind, name, status, metadata): self.artifacts.append({"type": kind, "name": name, "status": status, "metadata": metadata})


class _Auto:
    def __init__(self): self.storage = _Storage(); self.events = []; self.count = 0
    def create(self, goal, mode, workspace):
        self.count += 1; rid = f"use-{self.count}"; self.storage.rows[rid] = {"id": rid, "user_goal": goal, "status": "CREATED"}; return {"id": rid, "user_goal": goal, "plan": [], "status": "CREATED"}
    def execute(self, rid): return {"runtime_status": "WAITING_REVIEW", "artifacts": []}
    def approve(self, rid, note): return {"runtime_status": "COMPLETED", "artifacts": []}
    def get(self, rid): return {**self.storage.rows[rid], "computer_task": {}, "artifacts": list(self.storage.artifacts), "recoveries": [], "timeline": list(self.events)}
    def timeline(self, rid): return list(self.events)
    def artifacts(self, rid): return list(self.storage.artifacts)
    def _event(self, row, agent, phase, status, message, summary=""): self.events.append({"agent_name": agent, "event_type": phase, "status": status})


class _Sandbox:
    def validate(self, _operation): return {"status": "COMPLETED", "verification": "SUCCESS"}

class _Intelligence:
    def __init__(self): self.rows=[]
    def activity(self,*args): self.rows.append({"stage":args[1],"title":args[2],"status":args[4]})
    def activities(self,_): return list(self.rows)
    def review(self,change): return {"status":"PASS","severity":"LOW","issues":[]}
    def verification_plan(self,changes): return [{"command":"compileall"}]
    def diff_summary(self,changes): return {"files_changed":len(changes)}


class _Experience:
    def __init__(self): self.rows = {}
    def create_mission(self, task_id, goal):
        self.rows[task_id] = {"task_id": task_id, "mission_name": "Test mission", "progress": 20, "current_stage": "ANALYZING"}
        return self.rows[task_id]
    def update_mission(self, task_id, progress, stage):
        self.rows[task_id].update({"progress": progress, "current_stage": stage})
        return self.rows[task_id]
    def mission(self, task_id): return self.rows.get(task_id)


class ComputerUseAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        (self.root / "frontend").mkdir(); self.target = self.root / "frontend" / "styles.css"; self.target.write_text(".x{}\n", encoding="utf-8")
        engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine, tables=[ComputerFileChange.__table__]); self.sessions = sessionmaker(bind=engine); self.engine = engine
        self.agent = ResearchComputerUseAgent(_Auto(), ComputerUseService(self.sessions, initialize=False), WorkspaceActionEngine(self.root), _Sandbox(), _Intelligence(), _Experience())

    def tearDown(self): self.engine.dispose(); self.temp.cleanup()

    def test_create_and_start_generates_reviewable_diff(self):
        task = self.agent.create("优化首页 UI")
        result = self.agent.start(task["id"])
        self.assertEqual(result["changes"][0]["status"], "PROPOSED")
        self.assertEqual(result["mission"]["current_stage"], "WAITING_APPROVAL")
        self.assertEqual(self.target.read_text(encoding="utf-8"), ".x{}\n")

    def test_approval_applies_change_and_records_test_result(self):
        task = self.agent.create("优化首页 UI"); self.agent.start(task["id"])
        result = self.agent.approve(task["id"], "approved")
        self.assertEqual(result["changes"][0]["status"], "VERIFIED")
        self.assertIn("focus-within", self.target.read_text(encoding="utf-8"))

    def test_rollback_restores_before_snapshot(self):
        task = self.agent.create("优化首页 UI"); self.agent.start(task["id"]); self.agent.approve(task["id"], "approved")
        self.agent.rollback(task["id"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), ".x{}\n")

    def test_sensitive_file_read_is_blocked(self):
        with self.assertRaises(ValueError): WorkspaceActionEngine(self.root).read(".env")


if __name__ == "__main__": unittest.main()
