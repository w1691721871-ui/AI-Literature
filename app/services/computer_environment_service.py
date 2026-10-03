"""Read-only environment profiling for the controlled Computer Operator."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.computer_environment import ComputerEnvironmentState
from app.services.database import PROJECT_ROOT, SessionLocal


class ComputerEnvironmentScanner:
    """Scans only approved roots and returns metadata, never document content."""

    _ignored = {".git", ".venv", "work", "__pycache__", "node_modules", ".pytest_cache"}
    _blocked_file_names = {".env", ".env.local", ".env.production"}
    _blocked_suffixes = {".db", ".sqlite", ".sqlite3", ".faiss"}
    _document_suffixes = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx"}

    def __init__(self, project_root: Path | None = None, workspace_root: Path | None = None) -> None:
        self.project_root = (project_root or PROJECT_ROOT).resolve()
        self.workspace_root = (workspace_root or self.project_root / "research_workspace").resolve()

    def scan(self) -> dict[str, object]:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        workspace = self._profile(self.workspace_root, "research_workspace")
        project = self._project_profile()
        return {
            "status": "OBSERVED",
            "workspace": workspace,
            "project": project,
            "boundary": "仅扫描用户授权工作区与当前项目的文件元数据；未读取私密文件内容、未修改任何文件。",
        }

    def _profile(self, root: Path, label: str) -> dict[str, object]:
        types: Counter[str] = Counter()
        duplicates: Counter[tuple[str, int]] = Counter()
        count = 0
        for item in self._files(root):
            count += 1
            suffix = item.suffix.lower() or "[no extension]"
            types[suffix] += 1
            duplicates[(item.name.lower(), item.stat().st_size)] += 1
        return {
            "root": label,
            "file_count": count,
            "file_types": dict(sorted(types.items())),
            "document_count": sum(amount for suffix, amount in types.items() if suffix in self._document_suffixes),
            "possible_duplicate_count": sum(amount - 1 for amount in duplicates.values() if amount > 1),
        }

    def _project_profile(self) -> dict[str, object]:
        profile = self._profile(self.project_root, "current_project")
        technologies = []
        if (self.project_root / "app").exists(): technologies.extend(["Python", "FastAPI"])
        if (self.project_root / "frontend").exists(): technologies.extend(["Vue", "JavaScript"])
        if (self.project_root / "requirements.txt").exists(): technologies.append("Python dependencies")
        profile.update({"project_name": self.project_root.name, "technology": technologies})
        return profile

    def _files(self, root: Path):
        for item in root.rglob("*"):
            if (any(part in self._ignored for part in item.parts) or not item.is_file() or item.is_symlink()
                    or item.name.lower() in self._blocked_file_names or item.suffix.lower() in self._blocked_suffixes):
                continue
            try:
                resolved = item.resolve()
            except OSError:
                continue
            if resolved.is_relative_to(root):
                yield item


class ComputerEnvironmentService:
    """Turns a safe observation into a workspace-scoped, explainable environment summary."""

    def __init__(self, session_factory=SessionLocal) -> None:
        self._sessions = session_factory

    def analyze_environment(
        self, observation: dict[str, object], *, mission_id: str, workspace_id: str | None, goal: str
    ) -> dict[str, object]:
        page_state = str(observation.get("page_state") or "unknown")
        actions = [str(action) for action in observation.get("available_actions", []) if isinstance(action, str)]
        vision_demo = observation.get("vision_mode") == "demo_only"
        risk = str(observation.get("risk_level") or "LOW")
        blocked = "真实视觉输入未连接；仅可根据授权元数据进行受控操作。" if vision_demo else ""
        verification_points = observation.get("verification_points", [])
        target = str(verification_points[0]) if isinstance(verification_points, list) and verification_points else "状态变化验证"
        environment = observation.get("environment", {})
        application = str(environment.get("project_name") if isinstance(environment, dict) else "") or "Controlled Workspace"
        direction = "先完成固定验证" if "VERIFY" in actions else "等待人工审核"
        summary = {
            "current_state": page_state,
            "possible_actions": actions,
            "blocked_reason": blocked,
            "recommended_direction": direction,
            "verification_target": target,
            "vision_mode": "demo_only" if vision_demo else "connected",
            "risk_level": risk,
        }
        if workspace_id:
            session: Session = self._sessions()
            try:
                row = session.scalar(select(ComputerEnvironmentState).where(
                    ComputerEnvironmentState.mission_id == mission_id,
                    ComputerEnvironmentState.workspace_id == workspace_id,
                ).order_by(ComputerEnvironmentState.created_at.desc()))
                if row is None:
                    row = ComputerEnvironmentState(mission_id=mission_id, workspace_id=workspace_id)
                    session.add(row)
                row.application, row.page_state = application, page_state
                row.available_actions, row.current_goal = json.dumps(actions, ensure_ascii=False), str(goal)[:500]
                row.blocking_condition, row.verification_target, row.risk_level = blocked, target, risk
                session.commit(); session.refresh(row)
                summary["environment_state_id"] = row.id
            finally:
                session.close()
        return summary

    def get_state(self, mission_id: str, workspace_id: str) -> ComputerEnvironmentState | None:
        session: Session = self._sessions()
        try:
            return session.scalar(select(ComputerEnvironmentState).where(
                ComputerEnvironmentState.mission_id == mission_id,
                ComputerEnvironmentState.workspace_id == workspace_id,
            ).order_by(ComputerEnvironmentState.created_at.desc()))
        finally:
            session.close()
