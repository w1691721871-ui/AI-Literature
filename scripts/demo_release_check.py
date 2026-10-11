"""Read-only release gate for the isolated Golden Demo.

The command never creates a Mission, Evidence, Review, Artifact, user, or
index. It proves that the running API and static frontend are serving the same
prepared Demo environment before an operator begins an FDE presentation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.demo_environment import DemoEnvironmentError, apply_demo_environment, isolated_demo_environment


EXPECTED_RELEASE = "researchos-demo-v200"
EXPECTED_ENVIRONMENT = "demo"


def _json_url(url: str) -> tuple[dict[str, object] | None, str | None]:
    try:
        with urlopen(url, timeout=10) as response:  # nosec B310 - operator-supplied local Demo URLs only
            if response.status != 200:
                return None, f"HTTP {response.status}"
            payload = json.loads(response.read().decode("utf-8"))
            return payload, None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        return None, type(error).__name__


def _result(name: str, passed: bool, detail: str) -> bool:
    print(f"{name}: {'PASS' if passed else 'FAIL'} — {detail}")
    return passed


def _local_demo_state(environment) -> dict[str, object]:
    """Read the Demo database after the process is isolated to its workdir."""
    from sqlalchemy import func, select
    from app.models.ai_mission import AIMission
    from app.models.artifact import Artifact
    from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
    from app.models.paper import Paper
    from app.models.paper_chunk import PaperChunk
    from app.models.solution_project import SolutionProject
    from app.services.database import SessionLocal
    from app.services.identity_service import IdentityService
    from scripts.check_demo_corpus import _faiss_status

    session = SessionLocal()
    try:
        workspace = session.scalar(select(GovernanceWorkspace).where(
            GovernanceWorkspace.name == IdentityService.demo_workspace_name
        ))
        workspace_id = workspace.id if workspace else None
        other_workspaces = list(session.scalars(select(GovernanceWorkspace.id).where(
            GovernanceWorkspace.id != workspace_id
        ))) if workspace_id else []
        roles = set(session.scalars(select(WorkspaceUserRole.role).where(
            WorkspaceUserRole.workspace_id == workspace_id
        ))) if workspace_id else set()
        papers = int(session.scalar(select(func.count(Paper.paper_id))) or 0)
        chunks = int(session.scalar(select(func.count(PaperChunk.id))) or 0)
        embeddings = int(session.scalar(select(func.count(PaperChunk.id)).where(
            PaperChunk.embedding != ""
        )) or 0)
        artifacts = int(session.scalar(select(func.count(Artifact.id)).join(
            AIMission, Artifact.mission_id == AIMission.id,
        ).where(AIMission.workspace_id == workspace_id)) or 0) if workspace_id else 0
        review_rows = session.execute(
            select(AIMission.status, SolutionProject.review_status)
            .outerjoin(SolutionProject, SolutionProject.id == AIMission.solution_project_id)
            .where(AIMission.workspace_id == workspace_id)
        ).all() if workspace_id else []
    finally:
        session.close()

    approved_reviews = sum(
        1 for mission_status, project_status in review_rows
        if str(mission_status or "").upper() in {"APPROVED", "DELIVERY_READY", "COMPLETED"}
        or str(project_status or "").upper() == "APPROVED"
    )
    return {
        "workspace_id": workspace_id,
        "isolated": bool(workspace_id and not other_workspaces),
        "roles": roles,
        "papers": papers,
        "chunks": chunks,
        "embeddings": embeddings,
        "faiss": _faiss_status(embeddings),
        "artifacts": artifacts,
        "approved_reviews": approved_reviews,
        "database_exists": environment.database_path.exists(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only ResearchOS Golden Demo release gate")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="running Demo API base URL")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173", help="running Demo frontend base URL")
    args = parser.parse_args()

    try:
        environment = isolated_demo_environment()
        apply_demo_environment(environment)
        state = _local_demo_state(environment)
    except DemoEnvironmentError as error:
        print(f"environment: FAIL — {error}")
        return 2
    except Exception as error:
        print(f"environment: FAIL — {type(error).__name__}")
        return 2

    api_base = args.api_url.rstrip("/")
    frontend_base = args.frontend_url.rstrip("/")
    health, health_error = _json_url(f"{api_base}/health")
    identity, identity_error = _json_url(f"{api_base}/api/version")
    readiness, readiness_error = _json_url(f"{api_base}/api/release/demo-readiness")
    frontend, frontend_error = _json_url(f"{frontend_base}/release-info.json")
    local_frontend = json.loads((PROJECT_ROOT / "frontend" / "release-info.json").read_text(encoding="utf-8"))

    checks: list[bool] = []
    checks.append(_result("environment", state["database_exists"] and state["isolated"], (
        f"{environment.database_path}; isolated Demo Workspace={state['workspace_id'] or 'missing'}"
    )))
    checks.append(_result("database", bool(state["database_exists"]), "dedicated Demo SQLite database is available"))
    checks.append(_result("corpus", bool(
        state["papers"] > 0 and state["chunks"] > 0 and state["embeddings"] > 0 and state["faiss"] == "PASS"
    ), f"papers={state['papers']}, chunks={state['chunks']}, embeddings={state['embeddings']}, FAISS={state['faiss']}"))
    checks.append(_result("reviewer permissions", {"OWNER", "REVIEWER"}.issubset(state["roles"]), (
        "Demo Owner and Demo Reviewer memberships are present" if {"OWNER", "REVIEWER"}.issubset(state["roles"])
        else "Demo Owner and Demo Reviewer memberships are required"
    )))
    checks.append(_result("artifact flow", bool(state["artifacts"] and state["approved_reviews"]), (
        f"artifacts={state['artifacts']}, approved Mission reviews={state['approved_reviews']}"
    )))
    checks.append(_result("backend health", bool(health and health.get("status") == "ok"), health_error or "API health is ok"))

    identity_ok = bool(
        identity
        and identity.get("release") == EXPECTED_RELEASE
        and identity.get("environment") == EXPECTED_ENVIRONMENT
        and identity.get("commit")
        and identity.get("commit") != "not-configured"
        and identity.get("frontend_version") == local_frontend.get("frontend_version")
    )
    checks.append(_result("release identity", identity_ok, identity_error or (
        f"release={identity.get('release')}, commit={identity.get('commit')}, "
        f"frontend={identity.get('frontend_version')}, environment={identity.get('environment')}"
    )))
    frontend_ok = bool(frontend and frontend.get("frontend_version") == local_frontend.get("frontend_version"))
    checks.append(_result("frontend version", frontend_ok, frontend_error or (
        f"served={frontend.get('frontend_version')}, expected={local_frontend.get('frontend_version')}"
    )))
    readiness_ok = bool(
        readiness
        and readiness.get("overall") == "PASS"
        and readiness.get("demo_workspace_id") == state["workspace_id"]
    )
    checks.append(_result("live Demo alignment", readiness_ok, readiness_error or (
        f"overall={readiness.get('overall')}, workspace={readiness.get('demo_workspace_id')}"
    )))

    final = all(checks)
    print(f"\nDEMO RELEASE CHECK: {'PASS' if final else 'FAIL'}")
    return 0 if final else 2


if __name__ == "__main__":
    raise SystemExit(main())
