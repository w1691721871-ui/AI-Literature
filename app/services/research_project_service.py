"""Independent CRUD service for ResearchOS project lifecycle records."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research_project import ResearchProject
from app.services.database import SessionLocal, initialize_database


class ResearchProjectNotFoundError(Exception):
    """Raised when a project record cannot be found."""


class ResearchProjectService:
    """Persist small project-planning records without a new database service."""

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def list_projects(self) -> list[ResearchProject]:
        session: Session = self._session_factory()
        try:
            records = list(session.scalars(select(ResearchProject).order_by(ResearchProject.updated_at.desc())))
            for record in records:
                session.expunge(record)
            return records
        finally:
            session.close()

    def get_project(self, project_id: str) -> ResearchProject:
        session: Session = self._session_factory()
        try:
            record = session.get(ResearchProject, project_id)
            if record is None:
                raise ResearchProjectNotFoundError("科研项目不存在或已被删除。")
            session.expunge(record)
            return record
        finally:
            session.close()

    def create_project(self, data: dict[str, str]) -> ResearchProject:
        return self._save(None, data)

    def update_project(self, project_id: str, data: dict[str, str]) -> ResearchProject:
        return self._save(project_id, data)

    def _save(self, project_id: str | None, data: dict[str, str]) -> ResearchProject:
        session: Session = self._session_factory()
        try:
            record = ResearchProject(**data) if project_id is None else session.get(ResearchProject, project_id)
            if record is None:
                raise ResearchProjectNotFoundError("科研项目不存在或已被删除。")
            if project_id is not None:
                for field, value in data.items():
                    setattr(record, field, value)
            session.add(record)
            session.commit()
            session.refresh(record)
            session.expunge(record)
            return record
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_project(self, project_id: str) -> None:
        session: Session = self._session_factory()
        try:
            record = session.get(ResearchProject, project_id)
            if record is None:
                raise ResearchProjectNotFoundError("科研项目不存在或已被删除。")
            session.delete(record)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
