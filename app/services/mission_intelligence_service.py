"""Finite task understanding and replanning for the existing AI Worker Runtime."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy import select

from app.models.mission_state import MissionState
from app.services.database import SessionLocal, initialize_database
from app.services.skill_capability_registry import SkillCapabilityRegistry


class MissionIntelligenceService:
    """Plans only existing Skills and persists user-readable state summaries."""

    MAX_REPLAN_COUNT = 2

    def __init__(self, session_factory: Callable = SessionLocal, *, initialize: bool = True, capabilities=None):
        if initialize:
            initialize_database()
        self._sessions = session_factory
        self._capabilities = capabilities or SkillCapabilityRegistry()

    def analyze_mission_goal(self, goal: str) -> dict[str, object]:
        normalized = " ".join(str(goal or "").split())
        lowered = normalized.lower()
        required = ["research"]
        outputs = ["Evidence-bounded research summary"]
        objectives = ["Collect traceable Evidence", "Assess Evidence limits and review requirements"]
        if any(term in lowered for term in ("report", "proposal", "deliverable", "报告", "方案", "交付")):
            required.append("delivery"); outputs.append("Reviewable delivery draft")
        if any(term in lowered for term in ("computer", "code", "ui", "file", "代码", "界面", "文件")):
            required.append("computer"); objectives.append("Prepare a controlled Computer Skill action")
        risk = "HIGH" if any(term in lowered for term in ("upload", "submit", "write", "修改", "上传", "提交", "写入")) else "NORMAL"
        return {"goal_summary": normalized or "Mission goal requires clarification.", "objectives": objectives, "required_capabilities": required, "expected_outputs": outputs, "risk_level": risk}

    def build_task_plan(self, mission_id: str, understanding: Mapping[str, object]) -> list[dict[str, object]]:
        tasks: list[dict[str, object]] = []
        for index, capability in enumerate(understanding.get("required_capabilities", []), start=1):
            skill = str(capability)
            action = self._capabilities.capabilities_for(skill)[0] if self._capabilities.capabilities_for(skill) else "request_approval"
            tasks.append({"task_id": f"{mission_id}-{index}", "task_type": action.upper(), "required_skill": skill, "dependency": tasks[-1]["task_id"] if tasks else None, "status": "PENDING"})
        tasks.append({"task_id": f"{mission_id}-review", "task_type": "REQUEST_APPROVAL", "required_skill": "review", "dependency": tasks[-1]["task_id"] if tasks else None, "status": "REVIEW_REQUIRED"})
        return tasks

    def ensure_state(self, mission_id: str, workspace_id: str, plan: list[dict[str, object]] | None = None) -> dict[str, object]:
        if not workspace_id:
            raise ValueError("Mission State requires a workspace boundary.")
        session = self._sessions()
        try:
            row = session.scalar(select(MissionState).where(MissionState.mission_id == mission_id))
            if row and row.workspace_id != workspace_id:
                raise PermissionError("Cross-workspace Mission State access denied.")
            if row is None:
                row = MissionState(mission_id=mission_id, workspace_id=workspace_id, max_replan_count=self.MAX_REPLAN_COUNT, pending_tasks=self._encode(plan or []))
                session.add(row); session.commit(); session.refresh(row)
            return self._data(row)
        finally:
            session.close()

    def set_phase(self, mission_id: str, workspace_id: str, phase: str, *, quality_status: str | None = None, blocked_reason: str | None = None) -> dict[str, object]:
        session = self._sessions()
        try:
            row = self._row(session, mission_id, workspace_id)
            row.current_phase = phase
            if quality_status is not None: row.quality_status = quality_status
            if blocked_reason is not None: row.blocked_reason = blocked_reason[:160]
            session.commit(); session.refresh(row)
            return self._data(row)
        finally:
            session.close()

    def complete_skill_task(self, mission_id: str, workspace_id: str, skill: str, *, blocked: bool = False) -> dict[str, object]:
        session = self._sessions()
        try:
            row = self._row(session, mission_id, workspace_id)
            pending = self._decode(row.pending_tasks)
            completed = self._decode(row.completed_tasks)
            task = next((item for item in pending if item.get("required_skill") == skill), None)
            if task:
                pending.remove(task); task["status"] = "BLOCKED" if blocked else "COMPLETED"; completed.append(task)
            row.pending_tasks = self._encode(pending); row.completed_tasks = self._encode(completed)
            session.commit(); session.refresh(row)
            return self._data(row)
        finally:
            session.close()

    def replan_mission(self, mission_id: str, workspace_id: str, observation: Mapping[str, object], evidence_count: int) -> dict[str, object]:
        session = self._sessions()
        try:
            row = self._row(session, mission_id, workspace_id)
            if row.replan_count >= min(row.max_replan_count, self.MAX_REPLAN_COUNT):
                row.current_phase = "WAITING_REVIEW"; row.blocked_reason = "REPLAN_LIMIT_REACHED"
            elif evidence_count == 0:
                row.replan_count += 1; row.current_phase = "REPLAN"
                pending = self._decode(row.pending_tasks)
                if not any(item.get("task_type") == "RETRIEVE_EVIDENCE" and item.get("status") == "PENDING" for item in pending):
                    pending.insert(0, {"task_id": f"{mission_id}-replan-{row.replan_count}", "task_type": "RETRIEVE_EVIDENCE", "required_skill": "research", "dependency": None, "status": "PENDING"})
                row.pending_tasks = self._encode(pending); row.blocked_reason = "INSUFFICIENT_EVIDENCE"
            session.commit(); session.refresh(row)
            return self._data(row)
        finally:
            session.close()

    def snapshot(self, mission_id: str, workspace_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            return self._data(self._row(session, mission_id, workspace_id))
        finally:
            session.close()

    def _row(self, session, mission_id: str, workspace_id: str) -> MissionState:
        row = session.scalar(select(MissionState).where(MissionState.mission_id == mission_id))
        if row is None or row.workspace_id != workspace_id:
            raise PermissionError("Mission State is not available in this Workspace.")
        return row

    @staticmethod
    def _encode(value: object) -> str: return json.dumps(value, ensure_ascii=False)
    @staticmethod
    def _decode(value: str) -> list[dict[str, object]]:
        try:
            result = json.loads(value or "[]")
            return result if isinstance(result, list) else []
        except (TypeError, json.JSONDecodeError): return []
    def _data(self, row: MissionState) -> dict[str, object]:
        return {"mission_id": row.mission_id, "workspace_id": row.workspace_id, "current_phase": row.current_phase, "completed_tasks": self._decode(row.completed_tasks), "pending_tasks": self._decode(row.pending_tasks), "blocked_reason": row.blocked_reason, "replan_count": row.replan_count, "max_replan_count": min(row.max_replan_count, self.MAX_REPLAN_COUNT), "quality_status": row.quality_status}
