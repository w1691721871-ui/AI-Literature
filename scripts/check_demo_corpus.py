"""Read-only verification of the persisted Golden Demo corpus.

This script never initializes a database, downloads a paper, invokes an
embedding provider, or changes FAISS. Missing storage is reported as such.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import func, select

from app.models.governance import GovernanceWorkspace
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.database import DATABASE_PATH, DATABASE_URL, SessionLocal
from app.services.identity_service import IdentityService
from app.services.vector_store import INDEX_PATH, MAPPING_PATH


# A non-empty index is not enough: the Golden Demo must use the exact public
# building-materials corpus documented for the customer scenario.
REQUIRED_SCENARIO_FILENAMES = {
    "ge_2022_low_carbon_concrete.pdf",
    "he_2025_recycled_concrete_aggregate_leachate.pdf",
    "toboso_2025_virgin_aggregate_lca.pdf",
    "martinez_2021_incinerator_bottom_ash_concrete.pdf",
    "deb_2022_concrete_aggregate_grading.pdf",
    "dixit_2024_building_lca_energy_efficiency.pdf",
}


def _sqlite_database_exists() -> bool:
    if not DATABASE_URL.startswith("sqlite:") or ":memory:" in DATABASE_URL:
        return True
    return DATABASE_PATH.exists()


def _faiss_status(embeddings: int) -> str:
    if not INDEX_PATH.exists() or not MAPPING_PATH.exists():
        return "missing"
    try:
        import faiss
        index = faiss.read_index(str(INDEX_PATH))
        mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
        chunk_ids = mapping.get("chunk_ids", [])
        return "PASS" if index.ntotal > 0 and index.ntotal == len(chunk_ids) == embeddings else "invalid"
    except ImportError:
        return "unavailable"
    except Exception:
        return "invalid"


def check() -> int:
    if not _sqlite_database_exists():
        print("database: missing")
        print("papers: 0")
        print("chunks: 0")
        print("embeddings: 0")
        print("faiss: missing")
        print("scenario papers: 0/6")
        print("scenario chunks: 0")
        print("scenario embeddings: 0")
        print("scenario alignment: missing")
        print("demo workspace: missing")
        print("workspace safety: not verified")
        return 2
    session = SessionLocal()
    try:
        papers = int(session.scalar(select(func.count(Paper.paper_id))) or 0)
        chunks = int(session.scalar(select(func.count(PaperChunk.id))) or 0)
        embeddings = int(session.scalar(select(func.count(PaperChunk.id)).where(PaperChunk.embedding != "")) or 0)
        persisted_filenames = set(session.scalars(select(Paper.filename)).all())
        scenario_paper_ids = list(session.scalars(select(Paper.paper_id).where(
            Paper.filename.in_(REQUIRED_SCENARIO_FILENAMES)
        )))
        scenario_chunks = int(session.scalar(select(func.count(PaperChunk.id)).where(
            PaperChunk.paper_id.in_(scenario_paper_ids)
        )) or 0) if scenario_paper_ids else 0
        scenario_embeddings = int(session.scalar(select(func.count(PaperChunk.id)).where(
            PaperChunk.paper_id.in_(scenario_paper_ids), PaperChunk.embedding != ""
        )) or 0) if scenario_paper_ids else 0
        demo_workspace = session.scalar(select(GovernanceWorkspace).where(
            GovernanceWorkspace.name == IdentityService.demo_workspace_name
        ))
        other_workspaces = list(session.scalars(select(GovernanceWorkspace.id).where(
            GovernanceWorkspace.id != demo_workspace.id
        ))) if demo_workspace else []
    except Exception as error:
        print(f"database: unavailable ({type(error).__name__})")
        return 2
    finally:
        session.close()
    faiss_status = _faiss_status(embeddings)
    scenario_papers = len(REQUIRED_SCENARIO_FILENAMES & persisted_filenames)
    scenario_indexed = scenario_chunks > 0 and scenario_chunks == scenario_embeddings
    scenario_aligned = scenario_papers == len(REQUIRED_SCENARIO_FILENAMES) and scenario_indexed
    demo_workspace_ready = demo_workspace is not None
    dedicated_demo_deployment = demo_workspace_ready and not other_workspaces
    workspace_safety = (
        "dedicated demo deployment" if dedicated_demo_deployment
        else "shared deployment blocked" if demo_workspace_ready
        else "not verified"
    )
    print("database: available")
    print(f"papers: {papers}")
    print(f"chunks: {chunks}")
    print(f"embeddings: {embeddings}")
    print(f"faiss: {faiss_status}")
    print(f"scenario papers: {scenario_papers}/{len(REQUIRED_SCENARIO_FILENAMES)}")
    print(f"scenario chunks: {scenario_chunks}")
    print(f"scenario embeddings: {scenario_embeddings}")
    print(f"scenario alignment: {'PASS' if scenario_aligned else 'missing'}")
    print(f"demo workspace: {'available' if demo_workspace_ready else 'missing'}")
    print(f"workspace safety: {workspace_safety}")
    return 0 if (
        papers >= 5 and chunks > 0 and embeddings > 0 and faiss_status == "PASS"
        and scenario_aligned and dedicated_demo_deployment
    ) else 2


if __name__ == "__main__":
    raise SystemExit(check())
