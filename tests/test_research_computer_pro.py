"""Fixture-only P9 regressions; no production SQLite, FAISS or files are used."""

from __future__ import annotations

import unittest

from app.agent.research_computer_agent import ResearchComputerAgent
from app.agent.research_computer_task_planner import ResearchComputerTaskPlanner
from app.tools.computer.browser_tool import BrowserTool
from app.tools.computer.research_skills import ResearchSkillRouter
from app.tools.document_generator import DocumentGenerator


class _Service:
    def __init__(self): self.items, self.actions, self.counter = {}, [], 0
    def create_session(self, **data):
        self.counter += 1; item = {"id": f"task-{self.counter}", **data}; self.items[item["id"]] = item; return item
    def add_action(self, task_id, **data):
        item = {"id": f"action-{len(self.actions)+1}", "task_id": task_id, **data}; self.actions.append(item); return item
    def update_session(self, task_id, **data): self.items[task_id].update(data); self.items[task_id]["actions"] = list(self.actions); return self.items[task_id]
    def get(self, task_id): return self.items[task_id]
    def list(self): return list(self.items.values())
    def review_action(self, action_id, *, approved, reviewer_note): raise AssertionError("not needed")


class _File:
    name = "file"; description = "fixture"
    def scan(self): return {"status": "completed", "file_count": 0, "files": []}
    def plan_organization(self): return {"status": "approval_required", "proposals": []}


class _Knowledge:
    def search(self, *_args, **_kwargs):
        return [{"paper_id": "real-fixture-paper", "chunk_id": "real-fixture-chunk", "paper_title": "Fixture source", "section": "Method", "score": 0.8}]


class _Document:
    name = "document"; description = "fixture"
    def create_draft(self, *_args): return {"status": "draft_ready", "artifacts": [], "human_review_required": True}


class _Memory:
    def __init__(self): self.calls = []
    def record_plan(self, **data): self.calls.append(data); return data
    def get(self): return {"recent_tasks": [], "memory_boundary": "fixture"}


class ResearchComputerProTests(unittest.TestCase):
    def test_planner_builds_structured_evidence_bound_plan(self):
        preview = ResearchComputerTaskPlanner().preview("分析 RAG 技术发展并生成综述")
        self.assertEqual(preview["task_type"], "literature_review")
        self.assertTrue(all({"id", "task_name", "required_tool", "evidence_requirement", "risk_level"} <= set(step) for step in preview["plan"]))
        self.assertTrue(any(step["evidence_requirement"] for step in preview["plan"]))

    def test_experiment_and_proposal_templates_route_differently(self):
        planner = ResearchComputerTaskPlanner()
        self.assertEqual(planner.preview("设计一个验证实验")["task_type"], "experiment_plan")
        self.assertEqual(planner.preview("准备横向项目方案")["task_type"], "research_proposal")

    def test_skill_catalog_is_transparent_and_not_new_agents(self):
        names = {item["name"] for item in ResearchSkillRouter().catalog()}
        self.assertIn("Paper Reading Skill", names)
        self.assertIn("Research Writing Skill", names)

    def test_document_template_has_evidence_and_human_review_sections(self):
        text = DocumentGenerator._structured_content("literature_review", "比较方法", ["1. Source · Method"])
        self.assertIn("## Evidence references", text)
        self.assertIn("## Method Comparison", text)
        self.assertIn("## Human review", text)

    def test_browser_candidates_stay_external_and_empty_without_connector(self):
        result = BrowserTool().request("研究主题", "search")
        self.assertEqual(result["candidate_sources"], [])
        self.assertEqual(result["status"], "connector_not_configured")

    def test_browser_rejects_private_url_before_any_external_read(self):
        result = BrowserTool().open_and_extract("http://localhost/private")
        self.assertEqual(result["status"], "external_candidate_unavailable")
        self.assertEqual(result["candidate_sources"], [])

    def test_action_timeline_contains_evidence_bound_reading_and_approval(self):
        memory = _Memory()
        agent = ResearchComputerAgent(service=_Service(), file_tool=_File(), knowledge_tool=_Knowledge(), document_tool=_Document(), memory=memory)
        task = agent.create_task("分析 RAG 技术发展")
        actions = {item["action_type"] for item in task["actions"]}
        self.assertEqual(task["status"], "waiting_approval")
        self.assertTrue({"scan_workspace", "retrieve_evidence", "organize_evidence", "create_document"} <= actions)
        self.assertEqual(memory.calls[0]["task_type"], "literature_review")

    def test_fixture_service_does_not_attach_production_memory(self):
        agent = ResearchComputerAgent(
            service=_Service(), file_tool=_File(), knowledge_tool=_Knowledge(), document_tool=_Document()
        )
        self.assertIsNone(agent._memory)
        self.assertIn("隔离执行环境", agent.memory_snapshot()["memory_boundary"])


if __name__ == "__main__":
    unittest.main()
