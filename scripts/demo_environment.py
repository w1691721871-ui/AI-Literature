"""Safe configuration primitives for the isolated Golden Demo environment."""
from __future__ import annotations

import os
import subprocess
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
DEMO_ENV_FILE = DEMO_ROOT / ".env"
DEMO_RELEASE = "researchos-demo-v200"
DEMO_COMMIT = "35fc0eb8709e141c6fa66124242660905acab476"
DEMO_FRONTEND_VERSION = "v200"
DEMO_ENVIRONMENT = "demo"


class DemoEnvironmentError(RuntimeError):
    """Raised when a command could reach a non-Demo persistence target."""


def load_demo_environment_file() -> None:
    """Load local Demo variables without overriding explicit process values.

    The file is ignored by Git and is only read by Demo utilities.  This makes
    the preflight and bootstrap commands repeatable without ever reading a
    development ``.env`` or printing any credential value.
    """
    if not DEMO_ENV_FILE.exists():
        return
    for raw_line in DEMO_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _current_git_commit() -> str:
    """Return the checked-out commit for a local Demo without logging it."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


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
    load_demo_environment_file()
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
    """Select isolated persistence and public release identity before app import."""
    environment.work_directory.mkdir(parents=True, exist_ok=True)
    environment.database_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = environment.database_url
    os.environ["WORK_DIRECTORY"] = str(environment.work_directory)
    # These are public, non-secret Demo release values. Explicit process or
    # ``demo/.env`` values still win so a future release can advance them.
    if not os.getenv("RESEARCHOS_RELEASE", "").strip():
        os.environ["RESEARCHOS_RELEASE"] = DEMO_RELEASE
    if not os.getenv("RESEARCHOS_COMMIT", "").strip():
        os.environ["RESEARCHOS_COMMIT"] = _current_git_commit() or DEMO_COMMIT
    if not os.getenv("RESEARCHOS_FRONTEND_VERSION", "").strip():
        os.environ["RESEARCHOS_FRONTEND_VERSION"] = DEMO_FRONTEND_VERSION
    if not os.getenv("RESEARCHOS_ENVIRONMENT", "").strip():
        os.environ["RESEARCHOS_ENVIRONMENT"] = DEMO_ENVIRONMENT
    if not os.getenv("RESEARCHOS_RELEASE_GUARD", "").strip():
        os.environ["RESEARCHOS_RELEASE_GUARD"] = "true"
    # The isolated launcher is used with a same-machine static frontend. This
    # opt-in stays inside the Demo process; managed deployments keep it false
    # and admit only their configured public frontend origin.
    if not os.getenv("RESEARCHOS_ALLOW_LOCAL_CORS", "").strip():
        os.environ["RESEARCHOS_ALLOW_LOCAL_CORS"] = "true"
