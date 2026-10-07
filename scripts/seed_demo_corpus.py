"""Idempotently import the approved public-paper corpus for a Golden Demo.

Run this only against an explicitly provisioned Demo deployment with a real
embedding credential.  The script downloads public PDFs, uses the existing
paper parser/indexer, and creates no Evidence, Insight, Review or Artifact.
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.models.paper import Paper
from app.services.database import SessionLocal, initialize_database
from app.services.document_store import read_pdf_file
from app.services.paper_library_service import PaperLibraryService
from app.services.researchos_diagnostic_service import ResearchOSDiagnosticService


@dataclass(frozen=True)
class PublicPaper:
    filename: str
    title: str
    url: str


PUBLIC_DEMO_CORPUS = (
    PublicPaper("lewis_2020_retrieval_augmented_generation.pdf", "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", "https://arxiv.org/pdf/2005.11401"),
    PublicPaper("yao_2022_react.pdf", "ReAct: Synergizing Reasoning and Acting in Language Models", "https://arxiv.org/pdf/2210.03629"),
    PublicPaper("schick_2023_toolformer.pdf", "Toolformer: Language Models Can Teach Themselves to Use Tools", "https://arxiv.org/pdf/2302.04761"),
    PublicPaper("asai_2023_self_rag.pdf", "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection", "https://arxiv.org/pdf/2310.11511"),
    PublicPaper("yan_2024_corrective_rag.pdf", "Corrective Retrieval Augmented Generation", "https://arxiv.org/pdf/2401.15884"),
    PublicPaper("liu_2023_agentbench.pdf", "AgentBench: Evaluating LLMs as Agents", "https://arxiv.org/pdf/2308.03688"),
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


def seed() -> int:
    initialize_database()
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
    print(f"Imported {imported}; skipped {skipped}; diagnostics={readiness['overall']} counts={readiness['counts']}")
    return 0 if readiness["overall"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(seed())
    except Exception as error:
        print(f"DEMO CORPUS BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
