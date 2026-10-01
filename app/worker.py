"""Long-running bounded worker entrypoint for container deployments."""
from __future__ import annotations

from time import sleep

from app.services.config_service import ConfigService
from app.services.task_runtime_service import AgentWorker


def main() -> None:
    worker = AgentWorker()
    interval = ConfigService().load().worker_poll_seconds
    while True:
        worker.run_once()
        sleep(interval)


if __name__ == "__main__":
    main()
