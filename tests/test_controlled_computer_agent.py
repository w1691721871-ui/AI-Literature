"""P24 tests: all writes occur only in a disposable temporary workspace."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent.verification_agent import VerificationAgent
from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.agent_trace import AgentTrace
from app.models.computer_file_change import ComputerFileChange
from app.models.computer_mission import ComputerMission
from app.services.computer_use_service import ComputerUseService
from app.services.controlled_computer_mission_service import ControlledComputerMissionService
from app.services.diff_generator_service import DiffGeneratorService
from app.services.workspace_service import WorkspaceManager


class PassingVerifier:
    def verify(self, _path):
        return {"status": "PASS", "commands": ["npm_check"], "results": [], "suggestion": "review", "boundary": "fixture"}


class FailingVerifier:
    def verify(self, _path):
        return {"status": "FAIL", "commands": ["npm_check"], "results": [], "suggestion": "check syntax", "boundary": "fixture"}


class ControlledComputerAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "app").mkdir(); (self.root / "frontend").mkdir()
        (self.root / "frontend" / "styles.css").write_text(".home-research-input{}\n", encoding="utf-8")
        (self.root / ".env").write_text("secret=blocked", encoding="utf-8")
        self.engine = create_engine("sqlite:///:memory:")
        AIMission.__table__.create(self.engine); AIMissionEvent.__table__.create(self.engine); AgentTrace.__table__.create(self.engine)
        ComputerMission.__table__.create(self.engine); ComputerFileChange.__table__.create(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        manager = WorkspaceManager(self.root)
        self.service = ControlledComputerMissionService(
            self.sessions, initialize=False, workspace=manager,
            diffs=DiffGeneratorService(manager._actions),
            changes=ComputerUseService(self.sessions, initialize=False), verifier=PassingVerifier(),
        )

    def tearDown(self):
        self.engine.dispose(); self.temp.cleanup()

    def _analyzed(self):
        created = self.service.create({"mission_id": "parent-mission", "task": "优化首页 UI 样式", "reason": "fixture"})
        self.assertFalse(created["execution_allowed"])
        return self.service.analyze(created["id"])

    def test_workspace_scan_and_sensitive_file_boundary(self):
        profile = WorkspaceManager(self.root).scan()
        self.assertEqual(profile["project_type"], "AI Application")
        with self.assertRaises(ValueError):
            WorkspaceManager(self.root).inspect_file(".env")

    def test_verification_catalog_is_fixed_and_includes_required_safe_checks(self):
        catalog = VerificationAgent().sandbox.terminal.catalog()
        self.assertTrue({"compileall", "pytest", "npm_check", "npm_test", "git_diff"}.issubset(catalog))

    def test_plan_and_diff_are_created_without_writing_file(self):
        mission = self._analyzed()
        self.assertEqual(mission["status"], "WAITING_APPROVAL")
        self.assertIn("Diff Generator", str(mission["action_plan"]))
        self.assertIn("Controlled Computer Mission", mission["diff_content"])
        self.assertNotIn("Controlled Computer Mission", (self.root / "frontend" / "styles.css").read_text(encoding="utf-8"))

    def test_execution_is_blocked_before_approval_then_verified_afterwards(self):
        mission = self._analyzed()
        with self.assertRaises(ValueError):
            self.service.execute(mission["id"])
        approved = self.service.approve(mission["id"], "APPROVED", "approved fixture")
        self.assertTrue(approved["execution_allowed"])
        completed = self.service.execute(mission["id"])
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["verification"]["status"], "PASS")
        self.assertTrue(any(row["action"] == "File Modified" for row in completed["execution_log"]))

    def test_failure_requires_human_revision_and_is_bounded(self):
        manager = WorkspaceManager(self.root)
        failing = ControlledComputerMissionService(
            self.sessions, initialize=False, workspace=manager, diffs=DiffGeneratorService(manager._actions),
            changes=ComputerUseService(self.sessions, initialize=False), verifier=FailingVerifier(),
        )
        created = failing.create({"task": "优化首页 UI"}); analyzed = failing.analyze(created["id"])
        failing.approve(analyzed["id"], "APPROVED")
        failed = failing.execute(analyzed["id"])
        self.assertEqual(failed["status"], "NEEDS_REVISION")
        self.assertFalse(failed["execution_allowed"])
        self.assertEqual(failed["retry_count"], 1)
        self.assertLessEqual(failed["retry_count"], failing.MAX_RETRIES)

    def test_rejection_never_enables_execution(self):
        mission = self._analyzed()
        rejected = self.service.approve(mission["id"], "REJECTED", "not now")
        self.assertEqual(rejected["status"], "FAILED")
        self.assertFalse(rejected["execution_allowed"])

    def test_parent_mission_receives_user_readable_computer_timeline_events(self):
        session = self.sessions()
        session.add(AIMission(id="parent-mission", title="Parent", mission_type="RESEARCH", goal="fixture"))
        session.commit(); session.close()
        self._analyzed()
        session = self.sessions()
        events = session.query(AIMissionEvent).filter_by(mission_id="parent-mission", stage="Computer Agent").all()
        session.close()
        self.assertTrue(any(event.action == "Workspace Scanned" for event in events))
        self.assertTrue(any(event.action == "Waiting Approval" for event in events))


if __name__ == "__main__":
    unittest.main()
