import unittest

from app.services.computer_reflection_service import ComputerReflectionService


class MemoryRecorder:
    def __init__(self): self.calls = []
    def remember(self, workspace_id, memory_type, content):
        self.calls.append((workspace_id, memory_type, content)); return {"workspace_id": workspace_id, "memory_type": memory_type}


class ComputerReflectionServiceTests(unittest.TestCase):
    def test_reflection_is_user_readable_and_does_not_include_internal_content(self):
        reflection = ComputerReflectionService().reflect(
            {"goal": "Prepare a research brief"},
            {"strategy": {"id": "PUBLIC_DISCOVERY", "label": "Collect public research candidates"}, "decision": {"reason": "Evidence-gated route."}, "quality": {"status": "IN_PROGRESS"}, "workspace_state": {"completed_task": False, "failed_task": False, "requires_user_action": False}},
        )
        self.assertEqual(reflection["memory_type"], "TASK_EXPERIENCE")
        self.assertIn("Validate public candidates", reflection["future_advice"])
        self.assertNotIn("prompt", str(reflection).lower())

    def test_failure_learning_is_safely_persisted_through_existing_memory_service(self):
        service, recorder = ComputerReflectionService(), MemoryRecorder()
        reflection = {"task_goal": "Analyze a file", "strategy": "Authorized material", "result": "No result", "future_advice": "Request a supported file.", "memory_type": "FAILURE_LEARNING"}
        saved = service.remember("workspace-a", reflection, recorder)
        self.assertEqual(saved["memory_type"], "FAILURE_LEARNING")
        self.assertEqual(recorder.calls[0][0], "workspace-a")
        self.assertNotIn("Analyze a file", recorder.calls[0][2])


if __name__ == "__main__":
    unittest.main()
