"""Read-only preflight for the isolated Golden Demo environment."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.demo_environment import DemoEnvironmentError, apply_demo_environment, isolated_demo_environment


def main() -> int:
    try:
        environment = isolated_demo_environment()
        apply_demo_environment(environment)
    except DemoEnvironmentError as error:
        print(f"demo environment: BLOCKED ({error})")
        return 2

    # Application imports occur only after DATABASE_URL/WORK_DIRECTORY point to
    # the dedicated Demo target.
    from sqlalchemy import func, select
    from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
    from app.models.identity import User
    from app.models.paper import Paper
    from app.models.paper_chunk import PaperChunk
    from app.services.database import SessionLocal
    from app.services.identity_service import IdentityService
    from scripts.check_demo_corpus import REQUIRED_SCENARIO_FILENAMES, _faiss_status

    demo_mode = os.getenv("DEMO_MODE", "").strip().lower() == "true"
    if not environment.database_path.exists():
        print("demo environment: missing database")
        print(f"demo database: {environment.database_path}")
        print(f"demo mode: {'PASS' if demo_mode else 'BLOCKED'}")
        return 2

    session = SessionLocal()
    try:
        workspace = session.scalar(select(GovernanceWorkspace).where(
            GovernanceWorkspace.name == IdentityService.demo_workspace_name
        ))
        workspace_id = workspace.id if workspace else None
        other_workspaces = list(session.scalars(select(GovernanceWorkspace.id).where(
            GovernanceWorkspace.id != workspace_id
        ))) if workspace_id else []
        reviewer_count = int(session.scalar(select(func.count(WorkspaceUserRole.id)).join(
            User, User.id == WorkspaceUserRole.user_id
        ).where(
            WorkspaceUserRole.workspace_id == workspace_id,
            WorkspaceUserRole.role == "REVIEWER",
        )) or 0) if workspace_id else 0
        persisted_filenames = set(session.scalars(select(Paper.filename)).all())
        scenario_ids = list(session.scalars(select(Paper.paper_id).where(
            Paper.filename.in_(REQUIRED_SCENARIO_FILENAMES)
        )))
        scenario_chunks = int(session.scalar(select(func.count(PaperChunk.id)).where(
            PaperChunk.paper_id.in_(scenario_ids)
        )) or 0) if scenario_ids else 0
        scenario_embeddings = int(session.scalar(select(func.count(PaperChunk.id)).where(
            PaperChunk.paper_id.in_(scenario_ids), PaperChunk.embedding != ""
        )) or 0) if scenario_ids else 0
        total_embeddings = int(session.scalar(select(func.count(PaperChunk.id)).where(
            PaperChunk.embedding != ""
        )) or 0)
    except Exception as error:
        print(f"demo environment: unavailable ({type(error).__name__})")
        return 2
    finally:
        session.close()

    scenario_papers = len(REQUIRED_SCENARIO_FILENAMES & persisted_filenames)
    faiss = _faiss_status(total_embeddings)
    isolated = bool(workspace_id and not other_workspaces)
    corpus_ready = (
        scenario_papers == len(REQUIRED_SCENARIO_FILENAMES)
        and scenario_chunks > 0
        and scenario_chunks == scenario_embeddings
        and faiss == "PASS"
    )
    reviewer_ready = reviewer_count > 0

    print(f"demo database: {environment.database_path}")
    print(f"demo work directory: {environment.work_directory}")
    print(f"demo mode: {'PASS' if demo_mode else 'BLOCKED'}")
    print(f"demo workspace: {'PASS' if workspace_id else 'BLOCKED'}")
    print(f"workspace isolation: {'PASS' if isolated else 'BLOCKED'}")
    print(f"reviewer: {'PASS' if reviewer_ready else 'BLOCKED'} ({reviewer_count} reviewer membership(s))")
    print(f"demo corpus: {'PASS' if corpus_ready else 'BLOCKED'} ({scenario_papers}/{len(REQUIRED_SCENARIO_FILENAMES)} approved sources)")
    print(f"demo chunks: {scenario_chunks}")
    print(f"demo embeddings: {scenario_embeddings}")
    print(f"faiss: {faiss}")
    return 0 if demo_mode and isolated and reviewer_ready and corpus_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
