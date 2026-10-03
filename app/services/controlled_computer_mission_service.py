"""P24 approval-gated Computer Mission orchestration.

This service deliberately does not expose arbitrary shell, system paths, or
automatic recovery writes. A failed verification produces a new human-review
decision point rather than another automatic patch.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.controlled_computer_agent import ControlledComputerAgent
from app.agent.verification_agent import VerificationAgent
from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.agent_trace import AgentTrace
from app.models.computer_mission import ComputerMission
from app.services.computer_use_service import ComputerUseService
from app.services.computer_action_planner import ComputerActionPlanner
from app.services.computer_environment_service import ComputerEnvironmentService
from app.services.computer_feedback_service import ComputerFeedbackService
from app.services.computer_observation_service import ComputerObservationService
from app.services.computer_recovery_service import ComputerRecoveryService
from app.services.computer_verification_service import ComputerVerificationService
from app.services.computer_task_understanding_service import ComputerTaskUnderstandingService
from app.services.database import SessionLocal, initialize_database
from app.services.diff_generator_service import DiffGeneratorService
from app.services.workspace_service import WorkspaceManager


class ControlledComputerMissionNotFoundError(ValueError):
    pass


class ControlledComputerMissionService:
    MAX_RETRIES = 3

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal, *, initialize: bool = True,
                 workspace: WorkspaceManager | None = None, agent: ControlledComputerAgent | None = None,
                 diffs: DiffGeneratorService | None = None, changes: ComputerUseService | None = None,
                 verifier: VerificationAgent | None = None, observer: ComputerObservationService | None = None,
                 action_planner: ComputerActionPlanner | None = None, verification: ComputerVerificationService | None = None,
                 environment: ComputerEnvironmentService | None = None, feedback: ComputerFeedbackService | None = None,
                 recovery: ComputerRecoveryService | None = None, understanding: ComputerTaskUnderstandingService | None = None) -> None:
        if initialize:
            initialize_database()
        self._sessions = session_factory
        self.workspace = workspace or WorkspaceManager()
        self.agent = agent or ControlledComputerAgent()
        self.diffs = diffs or DiffGeneratorService(self.workspace._actions)
        self.changes = changes or ComputerUseService(session_factory, initialize=False)
        self.verifier = verifier or VerificationAgent()
        self.observer = observer or ComputerObservationService()
        self.action_planner = action_planner or ComputerActionPlanner()
        self.verification = verification or ComputerVerificationService()
        self.environment = environment or ComputerEnvironmentService(session_factory)
        self.feedback = feedback or ComputerFeedbackService(self.observer)
        self.recovery = recovery or ComputerRecoveryService()
        self.understanding = understanding or ComputerTaskUnderstandingService()

    def create(self, payload: dict[str, object]) -> dict[str, object]:
        task = str(payload["task"]).strip()
        mission_id = str(payload.get("mission_id") or "") or None
        identifier = str(uuid4())
        session = self._sessions()
        try:
            row = ComputerMission(id=identifier, task_id=f"controlled-{identifier}", mission_name=task[:240],
                                  mission_id=mission_id, task=task, reason=str(payload.get("reason") or ""),
                                  risk_level="LOW", status="CREATED", approval_status="PENDING",
                                  execution_allowed=False, progress=0, current_stage="CREATED")
            self._log(row, "Computer Mission Created", "CREATED", "已创建受控 Computer Mission；尚未读取或修改文件。")
            session.add(row); session.flush(); self._sync_mission_timeline(session, row); session.commit(); session.refresh(row)
            return self._payload(row)
        finally:
            session.close()

    def analyze(self, computer_mission_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            row = self._row(session, computer_mission_id)
            if row.status not in {"CREATED", "NEEDS_REVISION"}:
                raise ValueError("当前 Computer Mission 不能再次分析。")
            row.status, row.current_stage, row.progress = "ANALYZING", "ANALYZING", 20
            self._log(row, "Computer Analysis Started", "ANALYZING", "开始检查受控 Workspace 的结构与安全边界。")
            profile = self.workspace.scan()
            row.workspace_profile_json = self._encode(profile)
            self._log(row, "Workspace Scanned", "COMPLETED", "已读取项目结构元数据；未读取 .env、密钥、数据库或 FAISS 文件。")
            observation = self.observer.observe_environment({"mission_id": row.id, "goal": row.task, "workspace_profile": profile})
            observation["normalized_observation"] = self.observer.normalize_observation(observation)
            self._log(row, "Environment Observed", "OBSERVED", "已完成只读环境观察；当前没有真实视觉输入。")
            parent = session.get(AIMission, row.mission_id) if row.mission_id else None
            workspace_id = str(parent.workspace_id) if parent and parent.workspace_id else None
            environment = self.environment.analyze_environment(
                observation, mission_id=row.id, workspace_id=workspace_id, goal=row.task,
            )
            self._log(row, "Environment Analyzed", "COMPLETED", "已生成用户可理解的环境状态与验证目标；真实视觉仍为 demo_only。")
            controlled_action = self.action_planner.plan_next_action(observation, row.task)
            plan = dict(self.agent.plan(row.task, profile))
            plan["task_understanding"] = self.understanding.understand(row.task)
            plan["computer_observation"] = observation
            plan["environment_understanding"] = environment
            plan["controlled_action"] = controlled_action
            row.action_plan_json = self._encode(plan)
            row.risk_level = "HIGH" if controlled_action["requires_approval"] else str(plan["risk_level"])
            self._log(row, "Action Planned", "PLAN_READY", f"已规划受控 {controlled_action['action_type']} 动作；风险等级为 {row.risk_level}。")
            target = next(iter(plan["affected_files"]), "")
            proposal: dict[str, object] = {"status": "NO_SAFE_DIFF", "diff": "", "reason": "未选择安全目标文件。"}
            if target:
                inspected = self.workspace.inspect_file(target)
                self._log(row, "FILE_INSPECTED", "COMPLETED", f"已在白名单内检查 {inspected['file_path']}。")
                proposal = self.diffs.generate(row.task, target)
            row.diff_content = str(proposal.get("diff") or "")
            if proposal.get("status") == "PROPOSED":
                change = self.changes.propose(row.id, proposal)
                self._log(row, "Diff Generated", "PLAN_READY", f"已生成 {change['file_path']} 的可审阅 Diff；尚未写入。")
                row.status, row.current_stage, row.progress = "WAITING_APPROVAL", "WAITING_APPROVAL", 60
                self._log(row, "Waiting Approval", "WAITING_APPROVAL", "所有文件修改均需人工批准后才能执行。")
            else:
                row.status, row.current_stage, row.progress = "PLAN_READY", "PLAN_READY", 45
                self._log(row, "Plan Ready", "PLAN_READY", str(proposal.get("reason") or "未生成可安全执行的 Diff。"))
            self._sync_mission_timeline(session, row); session.commit(); session.refresh(row)
            return self._payload(row)
        finally:
            session.close()

    def approve(self, computer_mission_id: str, decision: str, note: str = "") -> dict[str, object]:
        if decision not in {"APPROVED", "REJECTED", "NEEDS_REVISION"}:
            raise ValueError("不支持的审批状态。")
        session = self._sessions()
        try:
            row = self._row(session, computer_mission_id)
            if row.status != "WAITING_APPROVAL":
                raise ValueError("当前 Computer Mission 不在待审批状态。")
            row.approval_status = decision
            if decision == "APPROVED":
                row.execution_allowed, row.status, row.current_stage, row.progress = True, "APPROVED", "APPROVED", 70
                for change in self.changes.changes(row.id):
                    if change["status"] == "PROPOSED":
                        self.changes.update_status(str(change["id"]), "APPROVED")
                self._log(row, "Human Approval Granted", "APPROVED", note or "已批准受控 Diff 执行。")
            elif decision == "REJECTED":
                row.execution_allowed, row.status, row.current_stage, row.progress = False, "FAILED", "REJECTED", 100
                self._log(row, "Human Approval Rejected", "REJECTED", note or "人工拒绝执行；未修改任何文件。")
            else:
                row.execution_allowed, row.status, row.current_stage, row.progress = False, "NEEDS_REVISION", "NEEDS_REVISION", 45
                self._log(row, "Revision Requested", "NEEDS_REVISION", note or "需修改计划或 Diff 后重新审批。")
            self._sync_mission_timeline(session, row); session.commit(); session.refresh(row)
            return self._payload(row)
        finally:
            session.close()

    def execute(self, computer_mission_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            row = self._row(session, computer_mission_id)
            if not row.execution_allowed or row.status != "APPROVED":
                raise ValueError("Computer Mission 未获人工批准，禁止执行。")
            if row.retry_count >= self.MAX_RETRIES:
                raise ValueError("已达到最多 3 次受控验证尝试，必须由人工创建新的修订任务。")
            changes = self.changes.changes(row.id)
            pending = next((item for item in changes if item["status"] == "APPROVED"), None)
            if pending is None:
                raise ValueError("没有已批准的文件修改提案。")
            snapshot = self.changes.get(str(pending["id"]))
            path = self.workspace._actions._safe(snapshot.file_path)
            if self.changes._hash(path.read_text(encoding="utf-8")) != snapshot.before_hash:
                raise ValueError("源文件已变化，拒绝应用过期 Diff。")
            row.status, row.current_stage, row.progress = "EXECUTING", "EXECUTING", 80
            self._log(row, "Execution Started", "EXECUTING", f"开始应用已批准的 {snapshot.file_path} 修改。")
            path.write_text(snapshot.after_content, encoding="utf-8")
            self.changes.update_status(snapshot.id, "APPLIED")
            self._log(row, "File Modified", "COMPLETED", f"已按批准 Diff 写入 {snapshot.file_path}。")
            row.status, row.current_stage, row.progress = "VERIFYING", "VERIFYING", 90
            report = self.verifier.verify(snapshot.file_path)
            report["controlled_verification"] = self.verification.verify_action_result(
                {"status": "APPROVED", "file": snapshot.file_path}, report, row.task
            )
            action_plan = self._decode(row.action_plan_json, {})
            if not isinstance(action_plan, dict):
                action_plan = {}
            before = action_plan.get("environment_understanding", {})
            if not isinstance(before, dict):
                before = {}
            after = {
                "page_state": "verification_passed" if report["status"] == "PASS" else "verification_failed",
                "risk_level": row.risk_level,
                "verification_status": report["status"],
            }
            controlled_action = action_plan.get("controlled_action", {})
            if not isinstance(controlled_action, dict):
                controlled_action = {}
            feedback = self.feedback.evaluate_action_result(controlled_action, before, after)
            report["environment_feedback"] = feedback
            if feedback["status"] != "SUCCESS":
                recovery = self.recovery.recover_failed_action(feedback, controlled_action, row.retry_count)
                report["recovery"] = recovery
                self._log(row, "Recovery Evaluated", str(recovery["action"]), str(recovery["summary"]))
            row.verification_json = self._encode(report)
            if report["status"] == "PASS":
                self.changes.update_status(snapshot.id, "VERIFIED")
                row.status, row.current_stage, row.progress = "COMPLETED", "COMPLETED", 100
                self._log(row, "Verification Completed", "PASS", "白名单验证通过；仍建议人工复核最终变更。")
            else:
                row.retry_count += 1
                row.execution_allowed, row.status, row.current_stage = False, "NEEDS_REVISION", "NEEDS_REVISION"
                self._log(row, "Verification Failed", "FAIL", "验证未通过，已停止自动执行并等待人工修订。")
            self._sync_mission_timeline(session, row); session.commit(); session.refresh(row)
            return self._payload(row)
        finally:
            session.close()

    def get(self, computer_mission_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            return self._payload(self._row(session, computer_mission_id))
        finally:
            session.close()

    def verification(self, computer_mission_id: str) -> dict[str, object]:
        return dict(self.get(computer_mission_id)["verification"])

    def by_mission(self, mission_id: str) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            rows = session.scalars(select(ComputerMission).where(ComputerMission.mission_id == mission_id).order_by(ComputerMission.created_at.asc())).all()
            return [self._payload(row) for row in rows]
        finally:
            session.close()

    @staticmethod
    def _encode(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _decode(value: str, default: object) -> object:
        try:
            return json.loads(value or "")
        except (json.JSONDecodeError, TypeError):
            return default

    def _row(self, session: Session, identifier: str) -> ComputerMission:
        row = session.get(ComputerMission, identifier)
        if row is None:
            raise ControlledComputerMissionNotFoundError("Computer Mission 不存在。")
        return row

    def _payload(self, row: ComputerMission) -> dict[str, object]:
        return {"id": row.id, "mission_id": row.mission_id, "task": row.task or row.mission_name,
                "reason": row.reason, "risk_level": row.risk_level, "status": row.status,
                "action_plan": self._decode(row.action_plan_json, {}), "diff_content": row.diff_content,
                "approval_status": row.approval_status, "execution_allowed": row.execution_allowed,
                "workspace": self._decode(row.workspace_profile_json, {}),
                "execution_log": self._decode(row.execution_log_json, []),
                "verification": self._decode(row.verification_json, {}), "retry_count": row.retry_count,
                "created_at": row.created_at}

    def _log(self, row: ComputerMission, action: str, status: str, result: str) -> None:
        rows = self._decode(row.execution_log_json, [])
        if not isinstance(rows, list):
            rows = []
        rows.append({"action": action, "status": status, "result": result,
                     "timestamp": datetime.now(timezone.utc).isoformat()})
        row.execution_log_json = self._encode(rows)

    def _sync_mission_timeline(self, session: Session, row: ComputerMission) -> None:
        """Mirror user-readable Computer events into an existing parent Mission.

        This is intentionally one-way: Computer Use never changes the parent
        Mission's approval or delivery state. It only contributes auditable
        timeline entries when a real P23 Mission was explicitly selected.
        """
        if not row.mission_id or session.get(AIMission, row.mission_id) is None:
            return
        existing = {
            (event.action, event.status, event.result_summary)
            for event in session.scalars(
                select(AIMissionEvent).where(
                    AIMissionEvent.mission_id == row.mission_id,
                    AIMissionEvent.stage == "Computer Agent",
                )
            ).all()
        }
        for entry in self._decode(row.execution_log_json, []):
            key = (str(entry.get("action", "")), str(entry.get("status", "")), str(entry.get("result", "")))
            if key in existing:
                continue
            session.add(AIMissionEvent(
                mission_id=row.mission_id,
                stage="Computer Agent",
                action=key[0],
                status=key[1],
                evidence_count=0,
                result_summary=key[2],
            ))
            session.add(AgentTrace(trace_id=row.mission_id, mission_id=row.mission_id, step="Computer Agent", message=key[2], agent_name="Computer Agent", action=key[0], status=key[1], output_summary=key[2], tool_used="Workspace Sandbox", evidence_count=0))
            existing.add(key)
