"""Workspace and task-center aggregation without touching Agent execution logic."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func

from app.models.paper import Paper
from app.models.research_project import ResearchProject
from app.models.research_task import ResearchTask
from app.models.research_workspace import ResearchWorkspace
from app.models.research_worker_run import ResearchWorkerRun
from app.services.database import SessionLocal, initialize_database
from app.services.computer_environment_service import ComputerEnvironmentScanner
from app.tools.computer.workspace_action_engine import WorkspaceActionEngine


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceManager:
    """P24 sandbox boundary for Computer Missions.

    This intentionally has no system-directory discovery and delegates file
    allow-listing to ``WorkspaceActionEngine``. It is not the user-facing
    ResearchWorkspace persistence service below.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path(__file__).resolve().parents[2]).resolve()
        self._scanner = ComputerEnvironmentScanner(project_root=self.root)
        self._actions = WorkspaceActionEngine(self.root)

    def scan(self) -> dict[str, object]:
        raw = self._scanner.scan()
        project = raw["project"]
        technology = list(project.get("technology", []))
        languages = [item for item in technology if item in {"Python", "JavaScript"}]
        frameworks = [item for item in technology if item in {"FastAPI", "Vue"}]
        return {
            "project_type": "AI Application" if frameworks else "Project Workspace",
            "languages": languages,
            "frameworks": frameworks,
            "files_count": int(project.get("file_count", 0)),
            "workspace_files": int(raw["workspace"].get("file_count", 0)),
            "boundary": raw["boundary"],
        }

    def inspect_file(self, relative_path: str) -> dict[str, object]:
        """Read an allow-listed project file only after path validation."""
        payload = self._actions.read(relative_path)
        return {"file_path": payload["file_path"], "content": payload["content"], "boundary": payload["boundary"]}


class WorkspaceService:
    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._sessions = session_factory

    def create(self, name: str, roles: list[str]) -> dict[str, object]:
        session = self._sessions()
        try:
            item = ResearchWorkspace(name=name.strip(), member_roles=json.dumps(roles, ensure_ascii=False))
            session.add(item); session.commit(); session.refresh(item)
            return self._workspace_payload(session, item)
        finally:
            session.close()

    def list(self) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            return [self._workspace_payload(session, item) for item in session.query(ResearchWorkspace).order_by(ResearchWorkspace.created_at.desc()).all()]
        finally:
            session.close()

    def create_task(self, workspace_id: str, payload: dict[str, str]) -> dict[str, object]:
        session = self._sessions()
        try:
            self._workspace(session, workspace_id)
            run = session.get(ResearchWorkerRun, payload.get("worker_run_id", "")) if payload.get("worker_run_id") else None
            task = ResearchTask(
                workspace_id=workspace_id, name=payload["name"], task_type=payload["task_type"],
                worker_run_id=payload.get("worker_run_id", ""),
                project_id=payload.get("project_id"), decision_id=payload.get("decision_id"),
                evidence_refs=json.dumps(payload.get("evidence_refs", []), ensure_ascii=False),
                status=self._task_status(run.status) if run else "Draft",
                evidence_count=self._evidence_count(run) if run else 0,
                output_report=run.output_file if run else "",
            )
            session.add(task); session.commit(); session.refresh(task)
            return self._task_payload(task)
        finally:
            session.close()

    def list_tasks(self, workspace_id: str | None = None) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            query = session.query(ResearchTask)
            if workspace_id:
                self._workspace(session, workspace_id)
                query = query.filter_by(workspace_id=workspace_id)
            return [self._task_payload(item) for item in query.order_by(ResearchTask.updated_at.desc()).all()]
        finally:
            session.close()

    def monitor(self) -> dict[str, object]:
        session = self._sessions()
        try:
            runs = session.query(ResearchWorkerRun).all()
            completed = sum(1 for run in runs if run.status == "completed")
            failed = sum(1 for run in runs if run.status == "failed")
            tool_counts: dict[str, int] = {"File Tool": 0, "Knowledge Tool": 0, "Data Tool": 0, "Document Tool": 0}
            durations: list[float] = []
            for run in runs:
                try:
                    for item in json.loads(run.selected_tools or "[]"):
                        label = {"file_tool": "File Tool", "knowledge_tool": "Knowledge Tool", "data_tool": "Data Tool", "document_tool": "Document Tool"}.get(item.get("name"))
                        if label: tool_counts[label] += 1
                except json.JSONDecodeError:
                    pass
                if run.updated_time and run.created_time:
                    durations.append(max(0.0, (run.updated_time - run.created_time).total_seconds()))
            return {"agents": [{"name": "Research Master", "execution_count": 0, "success_tasks": 0, "failed_tasks": 0, "average_duration_seconds": None, "boundary": "当前未将历史 Master 运行写入监控表。"}, {"name": "Research Worker", "execution_count": len(runs), "success_tasks": completed, "failed_tasks": failed, "average_duration_seconds": round(sum(durations) / len(durations), 2) if durations else None}], "tool_calls": [{"name": name, "count": count} for name, count in tool_counts.items()], "boundary": "指标来自本地 Worker 执行记录；不展示 Token、Prompt 或模型思维链。"}
        finally:
            session.close()

    def _workspace_payload(self, session, item: ResearchWorkspace) -> dict[str, object]:
        tasks = session.query(ResearchTask).filter_by(workspace_id=item.id).count()
        documents = session.query(Paper).count()
        projects = session.query(ResearchProject).count()
        try: roles = json.loads(item.member_roles or "[]")
        except json.JSONDecodeError: roles = []
        return {"id": item.id, "name": item.name, "created_at": item.created_at, "member_roles": roles, "project_count": projects, "document_count": documents, "agent_execution_count": session.query(ResearchWorkerRun).count(), "task_count": tasks}

    @staticmethod
    def _task_payload(item: ResearchTask) -> dict[str, object]:
        try: evidence_refs = json.loads(item.evidence_refs or "[]")
        except json.JSONDecodeError: evidence_refs = []
        return {"id": item.id, "workspace_id": item.workspace_id, "name": item.name, "task_type": item.task_type, "status": item.status, "worker_run_id": item.worker_run_id, "project_id": item.project_id, "decision_id": item.decision_id, "evidence_refs": evidence_refs, "evidence_count": item.evidence_count, "output_report": item.output_report, "created_at": item.created_at, "updated_at": item.updated_at}

    @staticmethod
    def _task_status(status: str) -> str:
        return {"planning": "Draft", "running": "Running", "need_confirmation": "Review", "completed": "Completed", "failed": "Review"}.get(status, "Draft")

    @staticmethod
    def _evidence_count(run: ResearchWorkerRun | None) -> int:
        if not run: return 0
        try: return int(json.loads(run.tool_results or "{}").get("knowledge_tool", {}).get("source_count", 0))
        except (json.JSONDecodeError, ValueError, TypeError): return 0

    @staticmethod
    def _workspace(session, workspace_id: str) -> ResearchWorkspace:
        item = session.get(ResearchWorkspace, workspace_id)
        if item is None: raise WorkspaceNotFoundError("未找到该 Research Workspace。")
        return item
