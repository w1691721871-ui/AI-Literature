"""P53 tests for the unified, bounded AI Worker Runtime."""

from __future__ import annotations

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.runtime_execution import RuntimeExecution
from app.services.ai_worker_runtime import AIWorkerRuntime
from app.services.ai_worker_service import AIWorkerService
from app.services.database import Base
from app.services.skill_registry import SkillAdapter, SkillRegistry, SkillResult


class FakeMissionService:
    def __init__(self, mission):
        self.mission = dict(mission)

    def detail(self, mission_id):
        if mission_id != self.mission["id"]:
            return None
        return dict(self.mission)


class FakeAdaptiveService:
    def __init__(self, decision="REQUEST_REVIEW"):
        self.decision = decision
        self.calls = []

    def run_once(self, mission_id):
        self.calls.append(mission_id)
        return {"decision": self.decision, "summary": "Existing adaptive decision preserved."}


class FakeSkill(SkillAdapter):
    def __init__(self, name, result):
        self.name = name
        self.description = f"{name} adapter"
        self.result = result
        self.calls = 0

    def execute(self, mission):
        self.calls += 1
        return self.result


class SequenceSkill(FakeSkill):
    """Deterministic finite results for an adaptive follow-up test."""

    def __init__(self, name, results):
        super().__init__(name, results[-1])
        self.results = list(results)

    def execute(self, mission):
        self.calls += 1
        return self.results[min(self.calls - 1, len(self.results) - 1)]


class FakeContextService:
    """Preserves the legacy runtime fixtures while Context behavior is tested separately."""
    def build(self, mission, *, actor=None):
        return {
            "workspace": {"id": mission["workspace_id"], "name": "Test Workspace"},
            "mission": {"id": mission["id"]}, "knowledge": {},
            "memory": {"workspace": [], "user": [], "mission": [], "knowledge": []},
            "boundary": "test",
        }

    def presentation(self, context):
        return {"workspace": context["workspace"], "mission": context["mission"], "knowledge": {}, "memory_counts": {}, "boundary": "test"}


class FakeWorkspaceMemory:
    def record_mission_summary(self, mission, *, owner_id=None):
        return None


class AIWorkerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.mission = {
            "id": "mission-p53", "title": "Evidence bounded mission", "goal": "Compare traceable evidence",
            "status": "PLANNING", "type": "RESEARCH", "current_step": "Planning",
            "workspace_id": "workspace-p53", "evidence_refs": [], "computer_missions": [],
        }

    def tearDown(self):
        self.engine.dispose()

    def runtime(self, adapters, adaptive=None, mission=None):
        service = FakeMissionService(mission or self.mission)
        return AIWorkerRuntime(
            self.sessions,
            initialize=False,
            mission_service=service,
            worker_service=AIWorkerService(),
            registry=SkillRegistry(adapters=adapters),
            adaptive_service=adaptive or FakeAdaptiveService(),
            context_service=FakeContextService(),
            workspace_memory_service=FakeWorkspaceMemory(),
        )

    def test_loads_mission_contract_and_skill_selection(self):
        research = FakeSkill("Research Skill", SkillResult("SUCCESS", "Evidence observed.", "Research complete."))
        review = FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Review observed.", "Human review required."))
        snapshot = self.runtime({"research": research, "review": review}).snapshot("mission-p53")
        self.assertEqual(snapshot["mission"]["objective"], "Compare traceable evidence")
        self.assertEqual([row["name"] for row in snapshot["skills"]], ["Research Skill", "Review Skill"])
        self.assertEqual(snapshot["mission"]["approval_requirement"], "HUMAN_REVIEW_REQUIRED")

    def test_research_execution_is_recorded(self):
        research = FakeSkill("Research Skill", SkillResult("SUCCESS", "Two Evidence references observed.", "Evidence collection completed."))
        review = FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Review pending.", "Human review required."))
        result = self.runtime({"research": research, "review": review}).execute("mission-p53")
        self.assertEqual(research.calls, 1)
        self.assertEqual(review.calls, 1)
        self.assertEqual(result["timeline"][0]["skill"], "Research Skill")
        self.assertEqual(result["timeline"][-1]["status"], "WAITING_REVIEW")

    def test_evidence_insufficient_calls_existing_adaptive_decision(self):
        adaptive = FakeAdaptiveService()
        research = FakeSkill("Research Skill", SkillResult("NEEDS_EVIDENCE", "No Evidence observed.", "Evidence required.", "COLLECT_EVIDENCE"))
        review = FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Unused", "Unused"))
        result = self.runtime({"research": research, "review": review}, adaptive).execute("mission-p53")
        self.assertEqual(adaptive.calls, ["mission-p53"])
        self.assertEqual(review.calls, 0)
        self.assertEqual(result["timeline"][-1]["status"], "WAITING_REVIEW")
        self.assertIn("Adaptive decision", result["timeline"][-1]["observation_summary"])

    def test_recovered_evidence_runs_one_bounded_read_only_follow_up(self):
        adaptive = FakeAdaptiveService("CONTINUE")
        research = SequenceSkill("Research Skill", [
            SkillResult("NEEDS_EVIDENCE", "No Evidence observed.", "Evidence required.", "COLLECT_EVIDENCE"),
            SkillResult("WAITING_REVIEW", "Traceable Evidence is ready.", "Evidence is ready for human review.", "COLLECT_EVIDENCE"),
        ])
        review = FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Unused", "Unused"))
        result = self.runtime({"research": research, "review": review}, adaptive).execute("mission-p53")
        self.assertEqual(research.calls, 2)
        self.assertEqual(adaptive.calls, ["mission-p53"])
        self.assertEqual(result["timeline"][-2]["status"], "REPLANNING")
        self.assertEqual(result["timeline"][-1]["status"], "WAITING_REVIEW")
        self.assertEqual(review.calls, 0)

    def test_resume_rebuilds_context_then_continues_only_a_runnable_mission(self):
        research = FakeSkill("Research Skill", SkillResult("SUCCESS", "Evidence observed.", "Research complete."))
        review = FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Review pending.", "Human review required."))
        result = self.runtime({"research": research, "review": review}).resume("mission-p53")
        self.assertEqual(research.calls, 1)
        self.assertEqual(result["execution"]["state"], "WAITING_REVIEW")
        self.assertEqual(review.calls, 1)

    def test_computer_skill_waits_for_approval(self):
        computer = FakeSkill("Computer Skill", SkillResult("WAITING_REVIEW", "Diff awaits approval.", "No modification applied."))
        review = FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Unused", "Unused"))
        mission = {**self.mission, "status": "WAITING_REVIEW", "computer_missions": [{"approval_status": "PENDING"}]}
        result = self.runtime({"computer": computer, "review": review}, mission=mission).execute("mission-p53")
        self.assertEqual(computer.calls, 1)
        self.assertEqual(review.calls, 0)
        self.assertEqual(result["timeline"][-1]["skill"], "Computer Skill")

    def test_delivery_skill_runs_only_after_approved_mission(self):
        delivery = FakeSkill("Delivery Skill", SkillResult("SUCCESS", "Draft created.", "Reviewable Artifact generated."))
        review = FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Review pending.", "Artifact review required."))
        mission = {**self.mission, "status": "APPROVED", "evidence_refs": [{"paper_id": "paper-1", "chunk_id": "chunk-1"}]}
        result = self.runtime({"delivery": delivery, "review": review}, mission=mission).execute("mission-p53")
        self.assertEqual(delivery.calls, 1)
        self.assertEqual(review.calls, 1)
        self.assertEqual(result["timeline"][0]["skill"], "Delivery Skill")

    def test_failed_skill_requests_bounded_replan(self):
        adaptive = FakeAdaptiveService("REPLAN")
        research = FakeSkill("Research Skill", SkillResult("FAILED", "Action failed.", "No details leaked."))
        review = FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Unused", "Unused"))
        result = self.runtime({"research": research, "review": review}, adaptive).execute("mission-p53")
        self.assertEqual(adaptive.calls, ["mission-p53"])
        self.assertEqual(result["timeline"][-1]["status"], "FAILED")
        self.assertNotIn("traceback", result["timeline"][-1]["result_summary"].lower())

    def test_runtime_stops_at_first_review_boundary(self):
        research = FakeSkill("Research Skill", SkillResult("WAITING_REVIEW", "Evidence ready.", "Review required."))
        review = FakeSkill("Review Skill", SkillResult("SUCCESS", "Should not run.", "Should not run."))
        result = self.runtime({"research": research, "review": review}).execute("mission-p53")
        self.assertEqual(review.calls, 0)
        self.assertEqual(len(result["timeline"]), 1)

    def test_bounded_adaptive_replan_remains_a_runnable_research_skill(self):
        research = FakeSkill("Research Skill", SkillResult("SUCCESS", "Replanned evidence pass completed.", "A bounded retry completed."))
        mission = {**self.mission, "status": "ADAPTIVE_REPLANNING"}
        result = self.runtime({"research": research, "review": FakeSkill("Review Skill", SkillResult("WAITING_REVIEW", "Review pending.", "Review required."))}, mission=mission).execute("mission-p53")
        self.assertEqual(research.calls, 1)
        self.assertEqual(result["timeline"][0]["skill"], "Research Skill")

    def test_execution_record_excludes_sensitive_reasoning_fields(self):
        self.assertEqual(set(RuntimeExecution.__table__.columns.keys()), {
            "id", "mission_id", "step_id", "skill", "action_type", "status",
            "observation_summary", "result_summary", "created_at",
        })


if __name__ == "__main__":
    unittest.main()
