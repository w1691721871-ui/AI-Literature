"""Guarded bootstrap for a repeatable, isolated Golden Demo foundation.

The bootstrap can create only the Demo identity and real public-paper corpus.
It deliberately does not auto-run a Mission, approve Evidence, or create a
Delivery: those records must result from the normal governed product flow.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.demo_environment import DEMO_ROOT, DemoEnvironmentError, apply_demo_environment, isolated_demo_environment


def _require_bootstrap_configuration() -> None:
    if os.getenv("DEMO_MODE", "").strip().lower() != "true":
        raise RuntimeError("DEMO_MODE=true is required")
    if not os.getenv("DEMO_OWNER_PASSWORD") or not os.getenv("DEMO_REVIEWER_PASSWORD"):
        raise RuntimeError("DEMO_OWNER_PASSWORD and DEMO_REVIEWER_PASSWORD are required")
    os.environ.setdefault("DEMO_OWNER_NAME", "Demo Owner")
    os.environ.setdefault("DEMO_REVIEWER_NAME", "Demo Reviewer")
    os.environ.setdefault("RESEARCHOS_DEMO_CORPUS_TARGET", "ResearchOS Demo Workspace")
    if os.environ["RESEARCHOS_DEMO_CORPUS_TARGET"] != "ResearchOS Demo Workspace":
        raise RuntimeError("RESEARCHOS_DEMO_CORPUS_TARGET must be ResearchOS Demo Workspace")


def _backup_existing_demo(environment) -> Path | None:
    if not environment.work_directory.exists() and not environment.database_path.exists():
        return None
    backup = DEMO_ROOT / "backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True, exist_ok=False)
    if environment.work_directory.exists():
        shutil.copytree(environment.work_directory, backup / "work")
        shutil.rmtree(environment.work_directory)
    if environment.database_path.exists() and not (backup / "work" / environment.database_path.name).exists():
        shutil.copy2(environment.database_path, backup / environment.database_path.name)
        environment.database_path.unlink()
    return backup


def bootstrap(apply: bool) -> int:
    _require_bootstrap_configuration()
    environment = isolated_demo_environment()
    print(f"Demo database target: {environment.database_path}")
    print(f"Demo work target: {environment.work_directory}")
    print("Bootstrap produces a Demo Workspace, Demo Owner, Demo Reviewer, and real public corpus only.")
    if not apply:
        print("DRY RUN: development DATABASE_URL is ignored; no data is changed. Re-run with --apply to bootstrap the Demo target.")
        return 0

    # No app import has occurred yet. Select the Demo store, then remove only
    # that store after a recoverable backup is made.
    backup = _backup_existing_demo(environment)
    apply_demo_environment(environment)
    if backup:
        print(f"Demo backup: {backup}")

    from app.services.demo_identity_service import DemoIdentitySeeder
    from scripts.seed_demo_corpus import seed
    from scripts.demo_environment_check import main as check_environment

    seeded_identity = DemoIdentitySeeder().seed_if_enabled()
    if not seeded_identity.get("seeded"):
        raise RuntimeError(f"Demo identity bootstrap failed: {seeded_identity.get('reason', 'unknown reason')}")
    print(f"Demo Workspace: {seeded_identity['workspace_id']}")
    if seed() != 0:
        raise RuntimeError("Golden Demo corpus import did not pass; inspect the preserved backup and source/embedding configuration")
    result = check_environment()
    if result != 0:
        raise RuntimeError("Golden Demo environment check did not pass")
    print("BOOTSTRAP COMPLETE: create the Golden Mission through the product and obtain a real Reviewer decision.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the isolated ResearchOS Golden Demo environment")
    parser.add_argument("--apply", action="store_true", help="back up and recreate only the configured demo/ environment")
    args = parser.parse_args()
    try:
        return bootstrap(args.apply)
    except (DemoEnvironmentError, RuntimeError) as error:
        print(f"DEMO BOOTSTRAP BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
