"""Fixture-only P14 tests; they never touch production SQLite, FAISS or files."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.agent.research_computer_operator_pro import ResearchComputerOperatorPro
from app.services.computer_environment_service import ComputerEnvironmentScanner
from app.tools.computer.code_tool import CodeAgentTool
from app.tools.computer.file_system_tool import FileSystemTool
from app.tools.computer.pro_terminal_tool import ProSafeTerminalTool
from app.tools.file_operator import FileOperator


class _Service:
    def __init__(self): self.items, self.actions, self.event_rows, self.count = {}, [], [], 0
    def create_session(self, **data):
        self.count += 1; item = {"id": f"task-{self.count}", **data, "artifact": {}, "actions": []}; self.items[item["id"]] = item; return item
    def get(self, task_id): return self.items[task_id]
    def update_session(self, task_id, **data):
        self.items[task_id].update(data); self.items[task_id]["actions"] = list(self.actions); return self.items[task_id]
    def add_action(self, task_id, **data):
        item = {"id": f"action-{len(self.actions)+1}", "task_id": task_id, **data}; self.actions.append(item); return item
    def add_event(self, task_id, **data):
        item = {"id": f"event-{len(self.event_rows)+1}", "task_id": task_id, **data}; self.event_rows.append(item); return item
    def events(self, task_id): return [item for item in self.event_rows if item["task_id"] == task_id]
    def review_action(self, action_id, *, approved, reviewer_note):
        action = next(item for item in self.actions if item["id"] == action_id)
        action["status"] = "APPROVED" if approved else "REJECTED"; return self.items[action["task_id"]], action


class _Memory:
    def record_plan(self, **data): return data


class _Checkpoint:
    def __init__(self): self.rows = {}
    def save(self, task_id, current_step, completed, remaining, status="ACTIVE"):
        self.rows[task_id] = {"task_id": task_id, "current_step": current_step, "completed_actions": completed, "remaining_actions": remaining, "status": status}; return self.rows[task_id]
    def get(self, task_id): return self.rows.get(task_id)


class _Patches:
    def __init__(self): self.items = []
    def propose_home_ui_focus(self, task_id):
        item = {"id": f"patch-{len(self.items)+1}", "task_id": task_id, "file_path": "frontend/styles.css", "diff_content": "--- fixture\n+++ fixture", "status": "WAITING_APPROVAL"}; self.items.append(item); return item
    def list_for_task(self, task_id): return [item for item in self.items if item["task_id"] == task_id]


class _Knowledge:
    def __init__(self, rows): self.rows = rows
    def search(self, *_args, **_kwargs): return self.rows


class _Document:
    name = "document"; description = "fixture"
    def create_draft(self, _task_id, _kind, _goal, refs):
        return {"status": "draft_ready" if refs else "INSUFFICIENT_EVIDENCE", "evidence_count": len(refs), "artifacts": []}


class ComputerOperatorProTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); root = Path(self.tmp.name)
        (root / "frontend").mkdir(); (root / "app").mkdir()
        (root / "frontend" / "app.js").write_text("const app = {};", encoding="utf-8")
        (root / "app" / "main.py").write_text("app = None", encoding="utf-8")
        self.service = _Service()
        self.agent = ResearchComputerOperatorPro(
            service=self.service, memory=_Memory(),
            scanner=ComputerEnvironmentScanner(root, root / "research_workspace"),
            file_tool=FileSystemTool(FileOperator(root / "research_workspace")),
            code_tool=CodeAgentTool(root), knowledge=_Knowledge([]), document=_Document(),
            checkpoints=_Checkpoint(), patches=_Patches(),
        )

    def tearDown(self): self.tmp.cleanup()

    def test_environment_scanner_reports_metadata_not_file_content(self):
        workspace = Path(self.tmp.name) / "research_workspace"; workspace.mkdir(exist_ok=True)
        (workspace / "paper.pdf").write_bytes(b"private content")
        profile = self.agent.environment()
        self.assertEqual(profile["workspace"]["file_count"], 1)
        self.assertNotIn("private content", str(profile))

    def test_create_persists_planning_event_and_no_execution(self):
        task = self.agent.create_task("分析当前项目代码")
        self.assertEqual(task["status"], "planning")
        self.assertEqual(task["events"][0]["event_type"], "PLANNING")

    def test_code_execution_is_analysis_then_human_approval(self):
        task = self.agent.create_task("优化首页 UI 代码")
        outcome = self.agent.execute(task["id"])
        self.assertEqual(outcome["status"], "waiting_approval")
        self.assertEqual(outcome["artifact"]["type"], "code_optimization_plan")
        self.assertTrue(any(item["action_type"] == "apply_code_patch" and item["approval_required"] for item in self.service.actions))

    def test_missing_evidence_blocks_research_delivery(self):
        task = self.agent.create_task("根据论文库生成实验方案", mode="research")
        outcome = self.agent.execute(task["id"])
        self.assertEqual(outcome["status"], "insufficient_evidence")
        self.assertEqual(outcome["artifact"]["status"], "INSUFFICIENT_EVIDENCE")
        self.assertTrue(any(item["event_type"] == "RECOVERY" for item in outcome["events"]))

    def test_evidence_document_requires_approval_then_creates_draft(self):
        self.agent.knowledge = _Knowledge([{"paper_id": "p1", "chunk_id": "c1", "paper_title": "Source", "section": "Method"}])
        task = self.agent.create_task("根据论文库生成实验方案", mode="research")
        waiting = self.agent.execute(task["id"])
        action = next(item for item in self.service.actions if item["action_type"] == "create_document")
        self.assertEqual(waiting["status"], "waiting_approval")
        completed = self.agent.approve(action["id"], "已核对")
        self.assertEqual(completed["status"], "completed")
        self.assertTrue(any(item["agent_name"] == "Document Agent" for item in completed["events"]))

    def test_catalog_has_no_shell_or_delete_automation(self):
        catalog = self.agent.catalog()
        names = {item["name"] for item in catalog["tools"]}
        self.assertIn("safe_terminal", names)
        self.assertNotIn("shell", names)
        self.assertIn("删除始终需批准", str(catalog))

    def test_safe_terminal_runs_fixed_catalog_and_blocks_arbitrary_commands(self):
        terminal = ProSafeTerminalTool(Path(self.tmp.name))
        self.assertEqual(terminal.execute("python_version")["status"], "COMPLETED")
        self.assertEqual(terminal.execute("rm -rf / ")["status"], "BLOCKED")

    def test_file_mutation_interface_is_workspace_scoped_only(self):
        tool = FileSystemTool(FileOperator(Path(self.tmp.name) / "research_workspace"))
        self.assertEqual(tool.execute_approved("create", target="notes/plan.md", content="approved draft")["status"], "COMPLETED")
        self.assertEqual(tool.execute_approved("copy", source="notes/plan.md", target="notes/copy.md")["status"], "COMPLETED")
        self.assertEqual(tool.execute_approved("delete", source="../outside.md")["status"], "FAILED")


if __name__ == "__main__": unittest.main()
