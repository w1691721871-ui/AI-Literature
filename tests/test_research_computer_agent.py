"""Fixture-only regression tests for the P8 Computer Execution Layer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.agent.research_computer_agent import ResearchComputerAgent
from app.tools.computer.browser_tool import BrowserTool
from app.tools.computer.file_system_tool import FileSystemTool
from app.tools.computer.permission_manager import PermissionManager
from app.tools.file_operator import FileOperator


class FakeService:
    def __init__(self): self.items = {}; self.actions = []; self.count = 0
    def create_session(self, **data):
        self.count += 1; item = {"id": f"computer-{self.count}", **data}; self.items[item["id"]] = item; return item
    def add_action(self, task_id, **data):
        result = {"id": f"action-{len(self.actions)+1}", "task_id": task_id, **data}; self.actions.append(result); return result
    def update_session(self, task_id, **data): self.items[task_id].update(data); self.items[task_id]["actions"] = list(self.actions); return self.items[task_id]
    def get(self, task_id): return self.items[task_id]
    def list(self): return list(self.items.values())
    def review_action(self, action_id, *, approved, reviewer_note):
        action = next(item for item in self.actions if item["id"] == action_id); action["status"] = "APPROVED" if approved else "REJECTED"; return self.items[action["task_id"]], action


class FakeKnowledge:
    def __init__(self, records): self.records = records
    def search(self, query, paper_ids=None, top_k=6): return self.records


class FakeDocument:
    name = "computer_document_generator"; description = "fixture"
    def create_draft(self, task_id, task_type, goal, evidence_refs):
        if not evidence_refs: return {"status":"INSUFFICIENT_EVIDENCE"}
        return {"status":"draft_ready", "artifacts":[{"format":"docx","path":f"{task_id}.docx"}], "human_review_required":True}


class ResearchComputerAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = FakeService()
        self.agent = ResearchComputerAgent(service=self.service, file_tool=FileSystemTool(FileOperator(Path(self.tmp.name))), knowledge_tool=FakeKnowledge([]), document_tool=FakeDocument())

    def tearDown(self): self.tmp.cleanup()

    def test_file_task_creates_only_approval_plan(self):
        Path(self.tmp.name, "paper.pdf").write_bytes(b"fixture")
        item = self.agent.create_task("整理我的论文目录")
        self.assertEqual(item["status"], "waiting_approval")
        self.assertEqual(item["artifact"]["status"], "PENDING_APPROVAL")
        self.assertTrue(Path(self.tmp.name, "paper.pdf").exists())

    def test_document_task_without_evidence_is_blocked(self):
        item = self.agent.create_task("根据当前知识库生成RAG综述")
        self.assertEqual(item["status"], "insufficient_evidence")
        self.assertEqual(item["artifact"]["status"], "INSUFFICIENT_EVIDENCE")

    def test_document_action_waits_for_explicit_approval(self):
        source = {"paper_id":"p","chunk_id":"c","paper_title":"Source","section":"Method"}
        self.agent._knowledge = FakeKnowledge([source])
        item = self.agent.create_task("根据当前知识库生成RAG综述")
        self.assertEqual(item["status"], "waiting_approval")
        action = next(value for value in self.service.actions if value["action_type"] == "create_document")
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertEqual(self.agent.approve_action(action["id"], "reviewed")["status"], "completed")

    def test_browser_connector_has_no_invented_candidates(self):
        result = BrowserTool().request("寻找最新 Agent 论文")
        self.assertEqual(result["status"], "connector_not_configured")
        self.assertEqual(result["candidate_sources"], [])

    def test_permission_levels_gate_mutation(self):
        permissions = PermissionManager()
        self.assertFalse(permissions.assess("scan_workspace")["approval_required"])
        self.assertTrue(permissions.assess("create_document")["approval_required"])
        self.assertTrue(permissions.assess("delete_files")["approval_required"])

    def test_catalog_does_not_expose_shell(self):
        names = {item["name"] for item in self.agent.tool_catalog()}
        self.assertIn("safe_terminal", names)
        self.assertNotIn("shell", names)


if __name__ == "__main__": unittest.main()
