"""Evidence-bounded orchestration for Research Workflow Studio.

The agent plans and coordinates existing ResearchOS capabilities.  It does not
reimplement retrieval, embeddings, claims, conflicts, or final synthesis.
"""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.research_computer_agent import ResearchComputerAgent
from app.agent.research_master_agent import ResearchMasterAgent
from app.models.research_workflow import ResearchWorkflow, WorkflowEvent, WorkflowStep
from app.services.database import SessionLocal, initialize_database
from app.services.research_copilot_service import ResearchCopilotService
from app.services.research_workspace_intelligence_service import ResearchWorkspaceIntelligenceService
from app.services.researchos_diagnostic_service import ResearchOSDiagnosticService


class WorkflowNotFoundError(Exception):
    """Raised when a workflow id cannot be resolved."""


class ResearchWorkflowAgent:
    """Create a dynamic workflow, then run existing agents inside clear bounds."""

    templates: dict[str, list[dict[str, str]]] = {
        "literature_review": [
            {"agent": "Literature Discovery Agent", "name": "发现研究资料", "expected": "论文、摘要、方法"},
            {"agent": "Research Analysis Agent", "name": "分析技术路线", "expected": "方法比较、实验结果"},
            {"agent": "Review Agent", "name": "审核关键结论", "expected": "Human Approval"},
            {"agent": "Proposal Agent", "name": "生成文献综述草案", "expected": "Literature Review"},
        ],
        "research_gap": [
            {"agent": "Literature Discovery Agent", "name": "梳理研究现状", "expected": "论文、方法、结果"},
            {"agent": "Research Gap Agent", "name": "识别资料覆盖边界", "expected": "不足、未来方向"},
            {"agent": "Review Agent", "name": "审核研究空白", "expected": "Human Approval"},
            {"agent": "Proposal Agent", "name": "形成验证方向草案", "expected": "Research Proposal"},
        ],
        "experiment_design": [
            {"agent": "Research Analysis Agent", "name": "分析已有研究条件", "expected": "方法、实验结果"},
            {"agent": "Computer Agent", "name": "准备受控执行计划", "expected": "Controlled task plan"},
            {"agent": "Review Agent", "name": "审核实验边界", "expected": "Human Approval"},
            {"agent": "Proposal Agent", "name": "生成实验计划草案", "expected": "Experiment Plan"},
        ],
        "proposal_generation": [
            {"agent": "Literature Discovery Agent", "name": "检索已有依据", "expected": "论文、章节、Evidence"},
            {"agent": "Research Gap Agent", "name": "整理可验证机会", "expected": "限制、待验证问题"},
            {"agent": "Proposal Agent", "name": "生成研究方案草案", "expected": "Research Proposal"},
            {"agent": "Review Agent", "name": "人工审核方案", "expected": "Human Approval"},
        ],
        "project_delivery": [
            {"agent": "Research Analysis Agent", "name": "理解项目目标", "expected": "研究问题、资料范围"},
            {"agent": "Computer Agent", "name": "准备受控资料工作计划", "expected": "Controlled task plan"},
            {"agent": "Proposal Agent", "name": "组织交付草案", "expected": "Project Delivery"},
            {"agent": "Review Agent", "name": "人工审核交付", "expected": "Human Approval"},
        ],
    }
    team_definitions = (
        ("Planner Agent", "任务规划", "将研究目标转为可审阅的工作流"),
        ("Researcher Agent", "Evidence 检索", "通过已有 Research Master 查询可追溯资料"),
        ("Reviewer Agent", "冲突与审核", "保留证据差异并标记人工审核要求"),
        ("Writer Agent", "交付草案", "仅基于已有 Evidence 整合研究输出"),
        ("Operator Agent", "受控执行", "仅准备 Computer Agent 计划，不执行未批准操作"),
    )

    def __init__(self, master_agent: ResearchMasterAgent | None = None,
                 workspace_service: ResearchWorkspaceIntelligenceService | None = None,
                 diagnostic_service: ResearchOSDiagnosticService | None = None,
                 copilot_service: ResearchCopilotService | None = None,
                 computer_agent: ResearchComputerAgent | None = None,
                 session_factory: Callable[[], Session] = SessionLocal, *, initialize: bool = True) -> None:
        if initialize:
            initialize_database()
        self._master = master_agent or ResearchMasterAgent()
        self._workspaces = workspace_service or ResearchWorkspaceIntelligenceService()
        self._diagnostics = diagnostic_service or ResearchOSDiagnosticService()
        self._copilot = copilot_service or ResearchCopilotService(self._workspaces)
        self._computer = computer_agent or ResearchComputerAgent()
        self._sessions = session_factory

    def create(self, goal: str, workspace_id: str | None = None, workflow_type: str | None = None) -> dict[str, object]:
        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("请输入研究目标。")
        workflow_type = workflow_type or self._workflow_type(normalized_goal)
        if workflow_type not in self.templates:
            raise ValueError("不支持的工作流类型。")
        workspace = self._workspaces.resolve_or_create(normalized_goal, workspace_id)
        session = self._sessions()
        try:
            workflow = ResearchWorkflow(workspace_id=str(workspace["workspace_id"]), goal=normalized_goal,
                                        workflow_type=workflow_type, status="PLANNING")
            session.add(workflow)
            session.flush()
            for sequence, item in enumerate(self.templates[workflow_type], start=1):
                session.add(WorkflowStep(workflow_id=workflow.id, sequence=sequence, agent_type=item["agent"],
                                         step_name=item["name"], status="PENDING", output_reference=item["expected"]))
            self._event(session, workflow.id, "Planner Agent", "planning", "COMPLETED", "已根据研究目标生成工作流预览。")
            workflow.status = "CREATED"
            session.commit()
            return self._payload(session, workflow)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, workflow_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            return self._payload(session, self._require(session, workflow_id))
        finally:
            session.close()

    def list(self, workspace_id: str | None = None) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            query = select(ResearchWorkflow).order_by(ResearchWorkflow.updated_at.desc())
            if workspace_id:
                query = query.where(ResearchWorkflow.workspace_id == workspace_id)
            return [self._payload(session, item) for item in session.scalars(query)]
        finally:
            session.close()

    def events(self, workflow_id: str) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            self._require(session, workflow_id)
            return [self._event_payload(item) for item in session.scalars(select(WorkflowEvent).where(
                WorkflowEvent.workflow_id == workflow_id
            ).order_by(WorkflowEvent.sequence, WorkflowEvent.created_at))]
        finally:
            session.close()

    def execute(self, workflow_id: str, paper_ids: list[str] | None = None) -> dict[str, object]:
        """Run one bounded Master execution only after a real-data readiness check."""
        session = self._sessions()
        try:
            workflow = self._require(session, workflow_id)
            steps = self._steps(session, workflow.id)
            counts = dict(self._diagnostics.run().get("counts", {}))
            self._event(session, workflow.id, "Planner Agent", "planning", "COMPLETED", "已确认工作流执行范围并开始资料就绪检查。")
            if not all(int(counts.get(key, 0)) > 0 for key in ("papers", "chunks", "embedded_chunks")):
                workflow.status, workflow.result_status = "WAITING_EVIDENCE", "INSUFFICIENT_EVIDENCE"
                workflow.execution_summary = "当前资料不足，工作流未进入 Research Master 或模型生成链路。"
                self._block_steps(steps, "INSUFFICIENT_EVIDENCE：请先上传并索引授权科研资料。")
                self._event(session, workflow.id, "Researcher Agent", "evidence_check", "WAITING_EVIDENCE", "当前没有足够的已索引资料，等待补充真实 Evidence。")
                session.commit()
                return self._payload(session, workflow)
            workflow.status, workflow.result_status = "RUNNING", "RUNNING"
            for step in steps:
                if step.agent_type != "Review Agent":
                    step.status = "RUNNING"
            self._event(session, workflow.id, "Researcher Agent", "execution", "RUNNING", "正在委托已有 Research Master 进行有证据边界的研究。")
            session.commit()
            goal, workflow_type, workspace_id = workflow.goal, workflow.workflow_type, workflow.workspace_id
        finally:
            session.close()

        # The Master keeps ownership of RAG / finite loop / final synthesis.
        selected_agents = self._selected_agents(workflow_type)
        result = self._master.run_task(goal, selected_agents, paper_ids or [])
        workspace_snapshot = self._workspaces.save_run(workspace_id, result)
        sources = list(result.get("sources", []))
        review_required = bool(result.get("finite_loop", {}).get("requires_human_review", False))

        computer_preview: dict[str, object] | None = None
        if workflow_type in {"experiment_design", "project_delivery"}:
            computer_preview = self._computer.preview_task(goal)
        copilot = self._copilot.intelligence(workspace_id)

        session = self._sessions()
        try:
            workflow = self._require(session, workflow_id)
            steps = self._steps(session, workflow.id)
            for step in steps:
                step.evidence_count = len(sources)
                if step.agent_type == "Review Agent":
                    step.status = "REVIEW_REQUIRED" if review_required else "COMPLETED"
                    step.output_reference = "HUMAN_REVIEW_REQUIRED" if review_required else "Review not required by current evidence state"
                elif step.agent_type == "Computer Agent" and computer_preview is not None:
                    step.status, step.output_reference = "COMPLETED", "Controlled plan preview prepared; no tool action executed."
                else:
                    step.status = "COMPLETED"
            workflow.status = "WAITING_REVIEW" if review_required else "COMPLETED"
            workflow.result_status = "NEEDS_HUMAN_REVIEW" if review_required else str(result.get("finite_loop", {}).get("stop_reason", "COMPLETED"))
            workflow.execution_summary = "Research Master 已完成有证据边界的执行；后续建议由 Copilot 提供，需人工选择。"
            self._event(session, workflow.id, "Researcher Agent", "evidence_retrieval", "COMPLETED", "已完成已有 Research Master 的证据检索与研究综合。", len(sources), f"已返回 {len(sources)} 条引用。")
            self._event(session, workflow.id, "Reviewer Agent", "review", "WAITING_REVIEW" if review_required else "COMPLETED", "当前 Evidence 存在待人工审核事项。" if review_required else "当前执行未标记额外人工审核要求。", len(sources))
            self._event(session, workflow.id, "Writer Agent", "delivery", "COMPLETED", "已形成基于 Evidence 的研究输出。", len(sources), "研究输出已保存到 Research Workspace。")
            if computer_preview is not None:
                self._event(session, workflow.id, "Operator Agent", "controlled_plan", "COMPLETED", "已准备受控 Computer Agent 计划预览，未执行任何未批准操作。")
            session.commit()
            payload = self._payload(session, workflow)
            payload.update({"research_workspace": workspace_snapshot, "sources": self._source_refs(sources),
                            "copilot": copilot, "computer_plan_preview": computer_preview,
                            "human_review_required": review_required})
            return payload
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _workflow_type(goal: str) -> str:
        value = goal.lower()
        if any(word in value for word in ("实验", "数据", "experiment")):
            return "experiment_design"
        if any(word in value for word in ("项目", "交付", "企业", "proposal")):
            return "project_delivery"
        if any(word in value for word in ("空白", "机会", "不足", "gap")):
            return "research_gap"
        if any(word in value for word in ("方案", "申请", "计划")):
            return "proposal_generation"
        return "literature_review"

    @staticmethod
    def _selected_agents(workflow_type: str) -> list[str]:
        return {
            "literature_review": ["literature", "knowledge", "trend", "report"],
            "research_gap": ["literature", "knowledge", "innovation", "report"],
            "experiment_design": ["literature", "knowledge", "innovation", "report"],
            "proposal_generation": ["literature", "knowledge", "project", "report"],
            "project_delivery": ["knowledge", "project", "report"],
        }[workflow_type]

    def _payload(self, session: Session, workflow: ResearchWorkflow) -> dict[str, object]:
        return {"id": workflow.id, "workspace_id": workflow.workspace_id, "goal": workflow.goal,
                "workflow_type": workflow.workflow_type, "status": workflow.status, "result_status": workflow.result_status,
                "execution_summary": workflow.execution_summary, "created_at": workflow.created_at, "updated_at": workflow.updated_at,
                "steps": [{"id": step.id, "sequence": step.sequence, "agent_type": step.agent_type,
                           "step_name": step.step_name, "status": step.status, "evidence_count": step.evidence_count,
                           "output_reference": step.output_reference} for step in self._steps(session, workflow.id)],
                "agent_team": self._team(session, workflow), "events": [self._event_payload(item) for item in session.scalars(select(WorkflowEvent).where(WorkflowEvent.workflow_id == workflow.id).order_by(WorkflowEvent.sequence, WorkflowEvent.created_at))],
                "timeline_boundary": "时间线记录 Agent 名称、状态、Evidence 数量与输出摘要；不保存 Prompt、Token 或内部推理。"}

    def _team(self, session: Session, workflow: ResearchWorkflow) -> list[dict[str, object]]:
        events = list(session.scalars(select(WorkflowEvent).where(WorkflowEvent.workflow_id == workflow.id).order_by(WorkflowEvent.sequence)))
        latest = {item.agent_name: item for item in events}
        uses_operator = workflow.workflow_type in {"experiment_design", "project_delivery"}
        result = []
        for name, role, task in self.team_definitions:
            event = latest.get(name)
            status = event.status if event else ("PENDING" if name != "Operator Agent" or uses_operator else "NOT_REQUIRED")
            result.append({"name": name, "role": role, "task": task, "status": status,
                           "output": event.output_summary if event else ""})
        return result

    @staticmethod
    def _event(session: Session, workflow_id: str, agent_name: str, phase: str, status: str, message: str,
               evidence_count: int = 0, output_summary: str = "") -> None:
        sequence = int(session.scalar(select(WorkflowEvent.sequence).where(WorkflowEvent.workflow_id == workflow_id).order_by(WorkflowEvent.sequence.desc()).limit(1)) or 0) + 1
        session.add(WorkflowEvent(workflow_id=workflow_id, sequence=sequence, agent_name=agent_name, phase=phase,
                                  status=status, message=message, evidence_count=evidence_count, output_summary=output_summary))

    @staticmethod
    def _event_payload(event: WorkflowEvent) -> dict[str, object]:
        return {"sequence": event.sequence, "agent_name": event.agent_name, "phase": event.phase,
                "status": event.status, "message": event.message, "evidence_count": event.evidence_count,
                "output_summary": event.output_summary, "created_at": event.created_at}

    @staticmethod
    def _source_refs(sources: list[dict[str, Any]]) -> list[dict[str, object]]:
        return [{"paper_id": item.get("paper_id"), "chunk_id": item.get("chunk_id") or item.get("id"),
                 "paper_title": item.get("paper_title") or item.get("title"), "section": item.get("section") or item.get("chapter"),
                 "score": item.get("score")} for item in sources if isinstance(item, dict)]

    @staticmethod
    def _block_steps(steps: list[WorkflowStep], output: str) -> None:
        for step in steps:
            step.status, step.output_reference, step.evidence_count = "BLOCKED", output, 0

    @staticmethod
    def _steps(session: Session, workflow_id: str) -> list[WorkflowStep]:
        return list(session.scalars(select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.sequence)))

    @staticmethod
    def _require(session: Session, workflow_id: str) -> ResearchWorkflow:
        workflow = session.get(ResearchWorkflow, workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError("Research Workflow 不存在。")
        return workflow
