"""Fixture-only checks for the P34 deployment runtime."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.runtime_task import RuntimeTask
from app.services.config_service import ConfigService
from app.services.database import Base
from app.services.runtime_monitor_service import RuntimeMonitor
from app.services.storage_service import StorageProvider
from app.services.task_runtime_service import AgentWorker, TaskQueue


class _MissionSuccess:
    def run(self, _mission_id):
        return {"status": "COMPLETED"}


class _MissionFailure:
    def run(self, _mission_id):
        raise RuntimeError("fixture failure")


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        session = self.sessions(); session.add(AIMission(id="mission-1", title="Runtime fixture")); session.commit(); session.close()

    def tearDown(self):
        self.engine.dispose()

    def test_docker_configuration_exists(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "Dockerfile.backend").is_file())
        self.assertIn("worker:", (root / "docker-compose.yml").read_text(encoding="utf-8"))

    def test_queue_and_worker_success(self):
        task = TaskQueue(self.sessions, initialize=False).enqueue("mission-1")
        result = AgentWorker(self.sessions, mission_service=_MissionSuccess(), worker_id="fixture-worker", initialize=False).run_once()
        self.assertEqual(task["status"], "QUEUED")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["worker_id"], "fixture-worker")

    def test_retry_enters_human_review_after_limit(self):
        queue = TaskQueue(self.sessions, initialize=False); queue.enqueue("mission-1")
        worker = AgentWorker(self.sessions, mission_service=_MissionFailure(), worker_id="fixture-worker", initialize=False)
        for _ in range(3):
            result = worker.run_once()
        self.assertEqual(result["status"], "WAITING_REVIEW")
        self.assertEqual(result["retry_count"], 3)
        self.assertNotIn("fixture failure", result["failure_reason"])

    def test_storage_is_local_and_safe(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = ConfigService()
            # A tiny stub retains the same public configuration contract.
            config.load = lambda: type("Config", (), {"storage_provider": "LOCAL", "storage_root": temporary})()  # type: ignore[method-assign]
            storage = StorageProvider(config)
            self.assertEqual(storage.health()["status"], "PASS")
            path = storage.store_generated("report.txt", b"safe")
            self.assertTrue(Path(path).is_file())
            with self.assertRaises(ValueError):
                storage.store_generated("", b"no")

    def test_config_summary_redacts_values_and_monitor_reports_queue(self):
        summary = ConfigService().summary()
        self.assertTrue(summary["SECURITY_CONFIG"]["secrets_redacted"])
        monitor = RuntimeMonitor(self.sessions)
        snapshot = monitor.snapshot()
        self.assertIn("queue_length", snapshot)
        self.assertIn("database", snapshot["services"])


if __name__ == "__main__":
    unittest.main()
