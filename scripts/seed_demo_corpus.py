"""Idempotently import the Golden Demo low-carbon-building-materials corpus.

Run this only against an explicitly provisioned Demo deployment with a real
embedding credential.  The script downloads public PDFs, uses the existing
paper parser/indexer, and creates no Evidence, Insight, Review or Artifact.
"""
from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.models.governance import GovernanceWorkspace
from app.models.paper import Paper
from app.services.database import SessionLocal, initialize_database
from app.services.document_store import read_pdf_file
from app.services.identity_service import IdentityService
from app.services.paper_library_service import PaperLibraryService
from app.services.researchos_diagnostic_service import ResearchOSDiagnosticService


@dataclass(frozen=True)
class PublicPaper:
    filename: str
    title: str
    url: str


PUBLIC_DEMO_CORPUS = (
    PublicPaper("ge_2022_low_carbon_concrete.pdf", "Accelerated Design and Deployment of Low-Carbon Concrete for Data Centers", "https://arxiv.org/pdf/2204.05397"),
    PublicPaper("he_2025_recycled_concrete_aggregate_leachate.pdf", "Assessing the Impact of Contact Time on Leachate Chemistry from Recycled Concrete Aggregates", "https://arxiv.org/pdf/2510.03344"),
    PublicPaper("toboso_2025_virgin_aggregate_lca.pdf", "Understanding the Environmental Impacts of Virgin Aggregates: Critical Literature Review and Primary Comprehensive Life Cycle Assessments", "https://arxiv.org/pdf/2501.10457"),
    PublicPaper("martinez_2021_incinerator_bottom_ash_concrete.pdf", "Valorization of Incinerator Bottom Ash for the Production of Resource-Efficient Eco-Friendly Concrete: Performance and Toxicological Characterization", "https://arxiv.org/pdf/2104.12497"),
    PublicPaper("deb_2022_concrete_aggregate_grading.pdf", "Learning to Sieve: Prediction of Grading Curves from Images of Concrete Aggregate", "https://arxiv.org/pdf/2204.03333"),
    PublicPaper("dixit_2024_building_lca_energy_efficiency.pdf", "LCA and Energy Efficiency in Buildings: Mapping More Than Twenty Years of Research", "https://arxiv.org/pdf/2409.00065"),
)


def _download(paper: PublicPaper) -> bytes:
    request = Request(paper.url, headers={"User-Agent": "ResearchOS-Demo-Corpus/1.0 (public research import)"})
    with urlopen(request, timeout=60) as response:  # nosec B310 - fixed public HTTPS sources only
        payload = response.read()
    if not payload.startswith(b"%PDF"):
        raise RuntimeError(f"{paper.title}: source did not return a PDF")
    return payload


def _existing(filename: str) -> Paper | None:
    session = SessionLocal()
    try:
        return session.scalar(select(Paper).where(Paper.filename == filename))
    finally:
        session.close()


def _require_dedicated_demo_workspace() -> str:
    """Refuse global-library writes unless this is a dedicated Demo deployment.

    ``Paper`` has no workspace foreign key in the existing schema, so the
    library is deployment-level. The seed therefore must never run beside a
    customer Workspace merely because its filenames look demo-related.
    """
    if os.getenv("DEMO_MODE", "").strip().lower() != "true":
        raise RuntimeError("DEMO_MODE=true is required before importing the Golden Demo corpus")
    expected_name = IdentityService.demo_workspace_name
    if os.getenv("RESEARCHOS_DEMO_CORPUS_TARGET", "").strip() != expected_name:
        raise RuntimeError(
            "Set RESEARCHOS_DEMO_CORPUS_TARGET to the exact Demo Workspace name before importing public Demo sources"
        )

    initialize_database()
    session = SessionLocal()
    try:
        demo_workspace = session.scalar(select(GovernanceWorkspace).where(
            GovernanceWorkspace.name == expected_name
        ))
        if not demo_workspace:
            raise RuntimeError("ResearchOS Demo Workspace is not provisioned; create the Demo identity first")
        other_workspaces = list(session.scalars(select(GovernanceWorkspace.name).where(
            GovernanceWorkspace.id != demo_workspace.id
        )))
        if other_workspaces:
            raise RuntimeError(
                "Golden Demo corpus import is blocked in a shared deployment; use a dedicated Demo database and persistent disk"
            )
        return str(demo_workspace.id)
    finally:
        session.close()


def seed() -> int:
    demo_workspace_id = _require_dedicated_demo_workspace()
    library = PaperLibraryService()
    imported = 0
    skipped = 0
    for source in PUBLIC_DEMO_CORPUS:
        payload = _download(source)
        document_hash = hashlib.sha256(payload).hexdigest()
        existing = _existing(source.filename)
        if existing:
            try:
                persisted_hash = hashlib.sha256(read_pdf_file(existing.file_path)).hexdigest()
            except (FileNotFoundError, ValueError) as error:
                raise RuntimeError(f"{source.filename}: existing record has no persisted source PDF; repair storage before reseeding") from error
            if persisted_hash != document_hash:
                raise RuntimeError(f"{source.filename}: public source changed; manual review is required before replacing an approved Demo source")
            print(f"SKIP {source.filename} (matching source hash)")
            skipped += 1
            continue
        library.save_uploaded_paper(payload, source.filename, "paper")
        print(f"IMPORTED {source.filename} · {document_hash[:12]}")
        imported += 1

    readiness = ResearchOSDiagnosticService().run()
    print(
        f"Demo Workspace {demo_workspace_id}: imported {imported}; skipped {skipped}; "
        f"diagnostics={readiness['overall']} counts={readiness['counts']}"
    )
    return 0 if readiness["overall"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(seed())
    except Exception as error:
        print(f"DEMO CORPUS BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
