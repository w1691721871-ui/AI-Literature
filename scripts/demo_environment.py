"""Safe configuration primitives for the isolated Golden Demo environment."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = PROJECT_ROOT / "demo"
DEFAULT_WORK_DIRECTORY = DEMO_ROOT / "work"
# The application diagnostics already resolve SQLite persistence through this
# filename beneath WORK_DIRECTORY. Keeping the isolated Demo target aligned
# avoids a false "database missing" result without changing application code.
DEFAULT_DATABASE_PATH = DEFAULT_WORK_DIRECTORY / "research_library.db"


class DemoEnvironmentError(RuntimeError):
    """Raised when a command could reach a non-Demo persistence target."""


@dataclass(frozen=True)
class DemoEnvironment:
    database_url: str
    database_path: Path
    work_directory: Path


def _resolve_local_path(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def isolated_demo_environment() -> DemoEnvironment:
    """Return the only persistence target accepted by Demo utilities.

    The regular ``DATABASE_URL`` is deliberately ignored here. Operators may
    set ``RESEARCHOS_DATABASE_URL_DEMO`` to a different SQLite file, but it
    must remain beneath the repository's ``demo/`` directory.
    """
    configured_url = os.getenv("RESEARCHOS_DATABASE_URL_DEMO", "").strip()
    if not configured_url:
        configured_url = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    try:
        parsed = make_url(configured_url)
    except Exception as error:
        raise DemoEnvironmentError("RESEARCHOS_DATABASE_URL_DEMO is not a valid database URL") from error
    if not parsed.drivername.startswith("sqlite") or not parsed.database or parsed.database == ":memory:":
        raise DemoEnvironmentError("Golden Demo requires a persistent SQLite database beneath demo/")

    database_path = _resolve_local_path(parsed.database)
    work_directory = _resolve_local_path(os.getenv("RESEARCHOS_DEMO_WORK_DIRECTORY", str(DEFAULT_WORK_DIRECTORY)))
    demo_root = DEMO_ROOT.resolve()
    if not database_path.is_relative_to(demo_root):
        raise DemoEnvironmentError("Demo database must remain under the repository demo/ directory")
    if not work_directory.is_relative_to(demo_root):
        raise DemoEnvironmentError("Demo work directory must remain under the repository demo/ directory")
    return DemoEnvironment(configured_url, database_path, work_directory)


def apply_demo_environment(environment: DemoEnvironment) -> None:
    """Select the isolated database before any ``app`` module is imported."""
    environment.work_directory.mkdir(parents=True, exist_ok=True)
    environment.database_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = environment.database_url
    os.environ["WORK_DIRECTORY"] = str(environment.work_directory)
