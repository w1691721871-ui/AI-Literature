"""Small SQLite setup for the local research paper library."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORK_DIRECTORY = PROJECT_ROOT / "work"
DATABASE_PATH = WORK_DIRECTORY / "research_library.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


class Base(DeclarativeBase):
    """Base class shared by all local SQLite models."""


def _build_engine():
    """Create the SQLite engine after ensuring its ignored work directory exists."""
    WORK_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def initialize_database() -> None:
    """Create local paper-library and report-history tables when first used."""
    # Importing models registers them with Base.metadata without a circular import.
    from app.models.analysis_record import AnalysisRecord  # noqa: F401
    from app.models.agent_trace import AgentTrace  # noqa: F401
    from app.models.paper import Paper  # noqa: F401
    from app.models.paper_chunk import PaperChunk  # noqa: F401
    from app.models.research_project import ResearchProject  # noqa: F401
    from app.models.rag_query_record import RagQueryRecord  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()


def _apply_lightweight_migrations() -> None:
    """Add small SQLite columns safely for local projects created before RAG v3."""
    columns = {column["name"] for column in inspect(engine).get_columns("papers")}
    if "quality_status" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE papers ADD COLUMN quality_status VARCHAR(50) NOT NULL DEFAULT 'parsed'")
            )
    if "document_type" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE papers ADD COLUMN document_type VARCHAR(50) NOT NULL DEFAULT 'paper'")
            )


def get_database_session() -> Generator[Session, None, None]:
    """Yield a short-lived database session for future FastAPI routes."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
