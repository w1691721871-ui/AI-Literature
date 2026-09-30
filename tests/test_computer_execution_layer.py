"""Isolated tests for the P15 approval-gated Computer Operator loop."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.code_patch import CodePatch
from app.models.computer_task_checkpoint import ComputerTaskCheckpoint
from app.services.code_patch_service import CodePatchService
from app.services.computer_action_executor import ComputerActionExecutor
from app.services.computer_checkpoint_service import ComputerCheckpointService
from app.services.database import Base
from app.tools.computer.file_system_tool import FileSystemTool


class _Files:
    def __init__(self, root: Path): self.workspace_root = root
    def inspect(self): return {"file_count": 0}
    def organization_plan(self): return {"proposals": []}


class ComputerExecutionLayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[CodePatch.__table__, ComputerTaskCheckpoint.__table__])
        self.sessions = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose(); self.temp.cleanup()

    def test_file_action_requires_approval_then_moves_inside_workspace(self):
        workspace = self.root / "research_workspace"; workspace.mkdir()
        (workspace / "raw.txt").write_text("real fixture", encoding="utf-8")
        files = FileSystemTool(_Files(workspace))
        executor = ComputerActionExecutor(files=files)
        blocked = executor.execute("move_files", {"source": "raw.txt", "target": "organized/raw.txt"}, approved=False)
        self.assertEqual(blocked["status"], "WAITING_APPROVAL")
        moved = executor.execute("move_files", {"source": "raw.txt", "target": "organized/raw.txt"}, approved=True)
        self.assertEqual(moved["verification"], "SUCCESS")
        self.assertTrue((workspace / "organized" / "raw.txt").exists())
        updated = executor.execute("update_file", {"source": "organized/raw.txt", "content": "reviewed fixture"}, approved=True)
        self.assertEqual(updated["verification"], "SUCCESS")
        self.assertEqual((workspace / "organized" / "raw.txt").read_text(encoding="utf-8"), "reviewed fixture")

    def test_patch_is_reviewable_and_applies_only_after_approval(self):
        frontend = self.root / "frontend"; frontend.mkdir()
        target = frontend / "styles.css"; target.write_text(".a{color:red}\n", encoding="utf-8")
        patches = CodePatchService(self.sessions, self.root, initialize=False)
        proposed = patches.propose_home_ui_focus("task-1")
        self.assertEqual(proposed["status"], "WAITING_APPROVAL")
        self.assertIn("focus-within", proposed["diff_content"])
        executor = ComputerActionExecutor(patches=patches)
        self.assertEqual(executor.execute("apply_code_patch", {"patch_id": proposed["id"]}, approved=False)["status"], "WAITING_APPROVAL")
        applied = executor.execute("apply_code_patch", {"patch_id": proposed["id"]}, approved=True)
        self.assertEqual(applied["verification"], "SUCCESS")
        self.assertIn("focus-within", target.read_text(encoding="utf-8"))

    def test_checkpoint_preserves_public_progress_without_task_content(self):
        checkpoints = ComputerCheckpointService(self.sessions, initialize=False)
        value = checkpoints.save("task-2", "verification", [{"action": "read", "status": "COMPLETED"}], [{"action": "move", "status": "PENDING_APPROVAL"}])
        self.assertEqual(value["current_step"], "verification")
        self.assertEqual(checkpoints.get("task-2")["remaining_actions"][0]["action"], "move")

    def test_stale_patch_fails_verification_without_overwriting_newer_file(self):
        frontend = self.root / "frontend"; frontend.mkdir()
        target = frontend / "styles.css"; target.write_text(".old{color:red}\n", encoding="utf-8")
        patches = CodePatchService(self.sessions, self.root, initialize=False)
        proposed = patches.propose_home_ui_focus("task-3")
        target.write_text(".new{color:blue}\n", encoding="utf-8")
        result = ComputerActionExecutor(patches=patches).execute("apply_code_patch", {"patch_id": proposed["id"]}, approved=True)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(target.read_text(encoding="utf-8"), ".new{color:blue}\n")


if __name__ == "__main__":
    unittest.main()
