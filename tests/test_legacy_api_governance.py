"""Regression checks for legacy technical endpoints behind the identity boundary."""

from pathlib import Path
import unittest


class LegacyApiGovernanceTests(unittest.TestCase):
    def test_legacy_technical_routes_require_session_context(self):
        root = Path(__file__).resolve().parents[1] / "app" / "routes"
        for filename in (
            "runtime.py",
            "agent_collaboration.py",
            "planner.py",
            "evaluations.py",
            "llm_runtime.py",
            "adaptive.py",
            "benchmarks.py",
            "advanced_computer.py",
            "scenarios.py",
        ):
            source = (root / filename).read_text(encoding="utf-8")
            self.assertIn("Depends(permissions.current)", source, filename)

    def test_operational_surfaces_remain_admin_only(self):
        root = Path(__file__).resolve().parents[1] / "app" / "routes"
        for filename in ("runtime.py", "benchmarks.py", "advanced_computer.py"):
            source = (root / filename).read_text(encoding="utf-8")
            self.assertIn("permissions.admin_console(context)", source, filename)

    def test_session_workspace_is_the_only_runtime_authority(self):
        source = (Path(__file__).resolve().parents[1] / "app" / "routes" / "llm_runtime.py").read_text(encoding="utf-8")
        self.assertIn("GovernanceService().policy(context.workspace_id)", source)
        self.assertIn("PermissionService().check(context.workspace_id,context.user_id,action)", source)


if __name__ == "__main__":
    unittest.main()
