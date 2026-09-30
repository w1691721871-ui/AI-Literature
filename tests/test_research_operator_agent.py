"""Fixture-only tests for the isolated Research Operator layer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.agent.research_operator_agent import ResearchOperatorAgent
from app.tools.browser_research_tool import BrowserResearchTool
from app.tools.file_operator import FileOperator


class FakeTasks:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}
        self.actions: list[dict[str, object]] = []

    def create(self, **values):
        item = {"id": f"task-{len(self.items) + 1}", **values}
        self.items[item["id"]] = item
        return item

    def update_execution(self, task_id, **values):
        self.items[task_id].update(values)
        return self.items[task_id]

    def record_action(self, task_id, **values):
        self.actions.append({"task_id": task_id, **values})

    def get(self, task_id): return self.items[task_id]
    def list(self): return list(self.items.values())
    def approve(self, task_id, note):
        self.items[task_id].update(status="approved", approval_status="approved", reviewer_note=note)
        return self.items[task_id]
    def reject(self, task_id, note):
        self.items[task_id].update(status="rejected", approval_status="rejected", reviewer_note=note)
        return self.items[task_id]


class FakeKnowledge:
    def __init__(self, sources): self.sources = sources
    def search(self, query, paper_ids=None, top_k=6): return self.sources


class FakeDocument:
    name = "document_generator"
    description = "fixture"
    def generate(self, task_id, *, document_type, objective, evidence_refs):
        if not evidence_refs:
            return {"status": "INSUFFICIENT_EVIDENCE", "message": "当前没有可验证资料", "artifacts": []}
        return {"status": "draft_ready", "artifacts": [{"format": "markdown", "path": f"{task_id}.md"}], "evidence_count": len(evidence_refs), "human_review_required": True}


class ResearchOperatorAgentTests(unittest.TestCase):
    def build(self, sources=None):
        self.tempdir = tempfile.TemporaryDirectory()
        files = FileOperator(Path(self.tempdir.name))
        return ResearchOperatorAgent(task_service=FakeTasks(), file_operator=files, knowledge_tool=FakeKnowledge(sources or []), document_generator=FakeDocument())

    def tearDown(self):
        if hasattr(self, "tempdir"): self.tempdir.cleanup()

    def test_document_task_requires_evidence(self):
        task = self.build().create_task("根据当前知识库生成RAG技术综述")
        self.assertEqual(task["status"], "insufficient_evidence")
        self.assertEqual(task["approval_status"], "not_available")
        self.assertEqual(task["artifact"]["status"], "INSUFFICIENT_EVIDENCE")

    def test_evidence_grounded_draft_waits_for_approval(self):
        source = {"paper_id": "paper-real", "chunk_id": "chunk-real", "paper_title": "Fixture source", "section": "Method", "score": .8}
        task = self.build([source]).create_task("根据当前知识库生成RAG技术综述")
        self.assertEqual(task["status"], "waiting_approval")
        self.assertEqual(task["evidence_refs"][0]["chunk_id"], "chunk-real")
        self.assertTrue(task["artifact"]["human_review_required"])

    def test_file_organization_only_makes_an_approval_plan(self):
        agent = self.build()
        Path(self.tempdir.name, "paper.pdf").write_bytes(b"fixture")
        task = agent.create_task("整理我的论文目录")
        self.assertEqual(task["status"], "waiting_approval")
        self.assertEqual(task["artifact"]["status"], "approval_required")
        self.assertTrue(Path(self.tempdir.name, "paper.pdf").exists())

    def test_approval_and_rejection_are_explicit(self):
        source = {"paper_id": "p", "chunk_id": "c", "paper_title": "Source", "section": "Result"}
        agent = self.build([source]); task = agent.create_task("生成技术报告")
        self.assertEqual(agent.approve(task["id"], "reviewed")["approval_status"], "approved")
        task2 = agent.create_task("生成技术报告")
        self.assertEqual(agent.reject(task2["id"], "need scope")["approval_status"], "rejected")

    def test_browser_connector_never_claims_sources(self):
        result = BrowserResearchTool().search("2025 RAG")
        self.assertEqual(result["status"], "connector_not_configured")
        self.assertEqual(result["candidate_sources"], [])

    def test_catalog_is_an_explicit_allow_list(self):
        names = {item["name"] for item in self.build().tool_catalog()}
        self.assertIn("file_operator", names)
        self.assertIn("workspace_operator", names)
        self.assertIn("safe_data_analysis", names)
        self.assertNotIn("shell", names)


if __name__ == "__main__":
    unittest.main()
