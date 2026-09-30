"""Evidence-bounded mission lifecycle and dashboard projections."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.notification import Notification
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.solution_deliverable import SolutionDeliverable
from app.models.solution_project import SolutionProject
from app.services.database import SessionLocal, initialize_database


class AIMissionNotFoundError(ValueError):
    pass


class AIMissionService:
    """Creates planning records only; it neither invokes models nor fabricates Evidence."""

    allowed_statuses = {"CREATED", "PLANNING", "RUNNING", "WAITING_REVIEW", "COMPLETED", "FAILED"}

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal, *, initialize: bool = True) -> None:
        if initialize:
            initialize_database()
        self._sessions = session_factory

    def create(self, payload: dict[str, str]) -> dict[str, object]:
        session = self._sessions()
        try:
            mission = AIMission(title=payload["title"].strip(), mission_type=payload.get("mission_type", "RESEARCH").strip(), goal=payload.get("goal", "").strip())
            session.add(mission); session.flush()
            self._event(session, mission, "Requirement Analysis", "Mission created", "CREATED", 0, "任务已创建，等待可审阅的研究规划。")
            mission.status, mission.progress, mission.current_step = "PLANNING", 15, "Requirement Analysis"
            self._event(session, mission, "Requirement Analysis", "Planning mission scope", "PLANNING", 0, "仅记录任务目标；尚未发起检索或生成研究结论。")
            session.add(Notification(notification_type="MISSION_CREATED", message=f"AI Mission 已创建：{mission.title}"))
            session.commit(); session.refresh(mission)
            return self._mission(mission)
        finally:
            session.close()

    def list(self) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            return [self._mission(row) for row in session.scalars(select(AIMission).order_by(AIMission.updated_at.desc())).all()]
        finally:
            session.close()

    def detail(self, mission_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            mission = self._require(session, mission_id)
            return {**self._mission(mission), "timeline": self._timeline(session, mission.id), "team": self._team(mission), "evidence_graph": self._evidence_graph(mission)}
        finally:
            session.close()

    def timeline(self, mission_id: str) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            self._require(session, mission_id)
            return self._timeline(session, mission_id)
        finally:
            session.close()

    def notifications(self) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            return [{"id": row.id, "type": row.notification_type, "message": row.message, "read": row.read, "created_at": row.created_at}
                    for row in session.scalars(select(Notification).order_by(Notification.created_at.desc()).limit(30)).all()]
        finally:
            session.close()

    def mark_notification_read(self, notification_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            row = session.get(Notification, notification_id)
            if row is None:
                raise AIMissionNotFoundError("Notification 不存在。")
            row.read = True; session.commit(); session.refresh(row)
            return {"id": row.id, "read": row.read}
        finally:
            session.close()

    def dashboard(self) -> dict[str, object]:
        session = self._sessions()
        try:
            missions = self.list()
            project_count = int(session.scalar(select(func.count(SolutionProject.id))) or 0)
            review_count = int(session.scalar(select(func.count(SolutionProject.id)).where(SolutionProject.review_status.in_(("PENDING", "NEEDS_REVISION")))) or 0)
            paper_count = int(session.scalar(select(func.count(Paper.paper_id))) or 0)
            chunk_count = int(session.scalar(select(func.count(PaperChunk.id))) or 0)
            deliverable_count = int(session.scalar(select(func.count(SolutionDeliverable.id))) or 0)
            return {"metrics": {"projects": project_count, "active_missions": sum(item["status"] in {"PLANNING", "RUNNING", "WAITING_REVIEW"} for item in missions), "pending_reviews": review_count, "knowledge_size": paper_count, "evidence_count": chunk_count, "deliverables": deliverable_count},
                    "recent_missions": missions[:6], "team_status": self._team(None), "latest_deliverables": deliverable_count,
                    "boundary": "Dashboard 仅聚合已持久化记录；不会生成虚假任务、Evidence 或交付物。"}
        finally:
            session.close()

    @staticmethod
    def _event(session: Session, mission: AIMission, stage: str, action: str, status: str, evidence_count: int, result: str) -> None:
        session.add(AIMissionEvent(mission_id=mission.id, stage=stage, action=action, status=status, evidence_count=evidence_count, result_summary=result))

    @staticmethod
    def _require(session: Session, mission_id: str) -> AIMission:
        mission = session.get(AIMission, mission_id)
        if mission is None:
            raise AIMissionNotFoundError("AI Mission 不存在。")
        return mission

    @staticmethod
    def _mission(row: AIMission) -> dict[str, object]:
        return {"id": row.id, "title": row.title, "type": row.mission_type, "goal": row.goal, "status": row.status, "progress": row.progress, "current_step": row.current_step, "created_at": row.created_at, "updated_at": row.updated_at}

    @staticmethod
    def _timeline(session: Session, mission_id: str) -> list[dict[str, object]]:
        return [{"id": row.id, "stage": row.stage, "action": row.action, "status": row.status, "evidence_count": row.evidence_count, "result": row.result_summary, "created_at": row.created_at}
                for row in session.scalars(select(AIMissionEvent).where(AIMissionEvent.mission_id == mission_id).order_by(AIMissionEvent.created_at.asc())).all()]

    @staticmethod
    def _team(mission: AIMission | None) -> list[dict[str, str]]:
        status = mission.status if mission else "READY"
        return [
            {"name": "Research Agent", "role": "任务规划", "status": status, "last_action": mission.current_step if mission else "等待任务"},
            {"name": "Literature Agent", "role": "知识检索", "status": "WAITING" if mission else "READY", "last_action": "仅在任务调用真实检索时运行"},
            {"name": "Innovation Agent", "role": "方案草稿", "status": "WAITING" if mission else "READY", "last_action": "依赖 Evidence 与 Human Review"},
            {"name": "Risk Agent", "role": "风险检查", "status": "READY", "last_action": "高风险输出须人工确认"},
            {"name": "Delivery Agent", "role": "交付生成", "status": "WAITING" if mission else "READY", "last_action": "仅生成审核后的交付草稿"},
        ]

    @staticmethod
    def _evidence_graph(mission: AIMission) -> dict[str, object]:
        return {"nodes": [{"id": "mission", "type": "mission", "label": mission.title}, {"id": "evidence:pending", "type": "evidence", "label": "尚未关联 Evidence"}, {"id": "review:pending", "type": "review", "label": "Human Review"}],
                "edges": [{"from": "mission", "to": "evidence:pending", "relation": "requires"}, {"from": "evidence:pending", "to": "review:pending", "relation": "before"}],
                "boundary": "该 Mission 尚未运行检索；图中不包含也不暗示任何科研证据。"}
