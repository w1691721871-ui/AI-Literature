"""Architecture guardrails for the public AI Worker execution path."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SingleRuntimeArchitectureTests(unittest.TestCase):
    def test_public_mission_run_uses_unified_ai_worker_runtime(self):
        source = (ROOT / "app" / "routes" / "missions.py").read_text(encoding="utf-8")
        handler = source[source.index("def run_mission"):source.index("@router.get(\"/missions/{mission_id}/control\")")]
        self.assertIn("ai_worker_runtime.execute(mission_id, actor=context)", handler)
        self.assertNotIn("service.run(mission_id)", handler)

    def test_legacy_runtimes_are_admin_compatibility_only(self):
        legacy = (ROOT / "app" / "routes" / "researchos.py").read_text(encoding="utf-8")
        llm = (ROOT / "app" / "routes" / "llm_runtime.py").read_text(encoding="utf-8")
        self.assertIn("dependencies=[Depends(require_legacy_compatibility_admin)]", legacy)
        execute = llm[llm.index("def execute("):llm.index("@router.get(\"/missions/{mission_id}/observations\")")]
        self.assertIn("permissions.admin_console(context)", execute)

    def test_architecture_document_states_the_only_enterprise_runtime(self):
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        self.assertIn("AIWorkerRuntime", architecture)
        self.assertIn("Single execution gateway", architecture)


if __name__ == "__main__":
    unittest.main()
