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

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.database import DATABASE_PATH, DATABASE_URL, SessionLocal
from app.services.vector_store import INDEX_PATH, MAPPING_PATH


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
        return 2
    session = SessionLocal()
    try:
        papers = int(session.scalar(select(func.count(Paper.paper_id))) or 0)
        chunks = int(session.scalar(select(func.count(PaperChunk.id))) or 0)
        embeddings = int(session.scalar(select(func.count(PaperChunk.id)).where(PaperChunk.embedding != "")) or 0)
    except Exception as error:
        print(f"database: unavailable ({type(error).__name__})")
        return 2
    finally:
        session.close()
    faiss_status = _faiss_status(embeddings)
    print("database: available")
    print(f"papers: {papers}")
    print(f"chunks: {chunks}")
    print(f"embeddings: {embeddings}")
    print(f"faiss: {faiss_status}")
    return 0 if papers >= 5 and chunks > 0 and embeddings > 0 and faiss_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(check())
