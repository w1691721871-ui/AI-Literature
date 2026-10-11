"""Read-only Golden Demo readiness report.

The report is safe to run before an interview.  It never initializes a
workspace, downloads content, invokes an embedding provider, or creates a
Mission, Evidence, Review, Insight, or Artifact.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.demo_environment import DemoEnvironmentError, apply_demo_environment, isolated_demo_environment


def mission_review_statuses(session_factory, workspace_id: str | None) -> dict[str, int]:
    """Count persisted Mission-level human-review states for one Workspace.

    The legacy ApprovalRequest queue is not the source of truth for the
    Mission review flow.  This read-only summary instead derives a single
    review state per Mission from its persisted lifecycle and linked Solution
    Project review record.
    """
    states = {"PENDING": 0, "NEEDS_REVISION": 0, "APPROVED": 0, "REJECTED": 0}
    if not workspace_id:
        return states

    from sqlalchemy import select
    from app.models.ai_mission import AIMission
    from app.models.solution_project import SolutionProject

    session = session_factory()
    try:
        rows = session.execute(
            select(AIMission.status, SolutionProject.review_status)
            .outerjoin(SolutionProject, SolutionProject.id == AIMission.solution_project_id)
            .where(AIMission.workspace_id == workspace_id)
        ).all()
    finally:
        session.close()

    for mission_status, project_status in rows:
        mission_state = str(mission_status or "").upper()
        project_state = str(project_status or "").upper()
        if mission_state in {"APPROVED", "DELIVERY_READY", "COMPLETED"} or project_state == "APPROVED":
            states["APPROVED"] += 1
        elif mission_state == "NEEDS_REVISION" or project_state == "NEEDS_REVISION":
            states["NEEDS_REVISION"] += 1
        elif mission_state == "REJECTED" or project_state == "REJECTED":
            states["REJECTED"] += 1
        elif mission_state == "WAITING_REVIEW" or project_state == "PENDING":
            states["PENDING"] += 1
    return states


def main() -> int:
    try:
        environment = isolated_demo_environment()
        apply_demo_environment(environment)
    except DemoEnvironmentError as error:
        print(f"GOLDEN DEMO DIAGNOSTICS BLOCKED: {error}")
        return 2

    # These imports are intentionally delayed until the isolated environment
    # has replaced DATABASE_URL and WORK_DIRECTORY for this process.
    from scripts.check_demo_corpus import check as check_corpus
    from app.services.database import SessionLocal
    from app.services.demo_readiness_service import DemoReadinessService

    print("GOLDEN DEMO DIAGNOSTICS")
    print("mode: read-only")
    print(f"database target: {environment.database_path}")
    corpus_exit = check_corpus()
    if not environment.database_path.exists():
        print("release readiness: BLOCKED (initialize the isolated Demo database with bootstrap_golden_demo.py --apply)")
        print("result: DEMO ENVIRONMENT NOT INITIALIZED.")
        return 2
    try:
        readiness = DemoReadinessService().snapshot()
    except Exception as error:  # Do not hide a missing database or broken deployment.
        print(f"release readiness: unavailable ({type(error).__name__})")
        return 2

    review_states = mission_review_statuses(SessionLocal, readiness["demo_workspace_id"])
    review_total = sum(review_states.values())
    release_counts = {**readiness["counts"], "reviews": review_total}
    print("release readiness:", readiness["overall"])
    print("workspace id:", readiness["demo_workspace_id"] or "missing")
    print("release counts:", json.dumps(release_counts, sort_keys=True))
    print("mission review states:", json.dumps(review_states, sort_keys=True))
    print("mission / evidence / review / delivery:")
    for item in readiness["checks"]:
        if item["id"] in {"research", "evidence_review", "artifact", "computer"}:
            print(f"- {item['id']}: {item['status']} — {item['detail']}")

    # A corpus can be ready while a real Mission and reviewer walkthrough has
    # not happened.  Report this truthfully without making the command fail
    # just because an operator has not yet performed a live review.
    if corpus_exit == 0:
        review_result = (
            "Human Review is recorded in the Mission lifecycle."
            if review_total
            else "Live Mission, human Review, and Delivery remain operator-verified."
        )
        print(f"result: CORPUS READY; {review_result}")
        return 0
    print("result: CORPUS NOT READY; do not present the building-materials scenario as a live evidence walkthrough.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
