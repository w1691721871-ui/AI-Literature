"""P21 deterministic orchestration for review-first FDE solution drafts.

This layer deliberately describes the installed ResearchOS architecture and
observable local data. It does not call an LLM, invent customer confirmation,
or create research evidence.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.solution_deliverable import SolutionDeliverable
from app.models.solution_computer_mission import SolutionComputerMission
from app.models.solution_version import SolutionVersion
from app.models.solution_project import SolutionProject
from app.models.solution_requirement import SolutionRequirement
from app.services.database import SessionLocal, initialize_database


class SolutionNotFoundError(Exception):
    pass


class FDESolutionService:
    requirement_types = ("BUSINESS", "DATA", "AI", "SYSTEM", "DELIVERY", "SECURITY")
    delivery_types = ("SOLUTION_BLUEPRINT", "TECHNICAL_ARCHITECTURE", "IMPLEMENTATION_PLAN", "DATA_PLAN", "AI_WORKFLOW", "DELIVERY_REPORT")

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal, *, initialize: bool = True) -> None:
        if initialize:
            initialize_database()
        self._sessions = session_factory

    def create(self, payload: dict[str, str]) -> dict[str, object]:
        session = self._sessions()
        try:
            row = SolutionProject(
                title=payload["title"].strip(), customer_need=payload["customer_need"].strip(),
                industry=payload.get("industry", "Research").strip(), objective=payload.get("objective", "").strip(),
            )
            session.add(row); session.commit(); session.refresh(row)
            return self._project(row)
        finally:
            session.close()

    def list(self) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            return [self._project(row) for row in session.scalars(select(SolutionProject).order_by(SolutionProject.updated_at.desc())).all()]
        finally:
            session.close()

    def detail(self, project_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            project = self._project_row(session, project_id)
            return {
                **self._project(project),
                "requirements": [self._requirement(row) for row in session.scalars(select(SolutionRequirement).where(SolutionRequirement.solution_project_id == project.id)).all()],
                "deliverables": [self._deliverable(row) for row in session.scalars(select(SolutionDeliverable).where(SolutionDeliverable.solution_project_id == project.id).order_by(SolutionDeliverable.created_at.asc())).all()],
                "computer_missions": [self._mission(row) for row in session.scalars(select(SolutionComputerMission).where(SolutionComputerMission.solution_project_id == project.id).order_by(SolutionComputerMission.created_at.asc())).all()],
                "versions": [self._version(row) for row in session.scalars(select(SolutionVersion).where(SolutionVersion.solution_project_id == project.id).order_by(SolutionVersion.version.asc())).all()],
                "metrics": self._metrics(session, project.id),
                "boundary": "Solution Project 是 AI 辅助方案草稿；需求、范围、风险与正式交付均需人工确认。",
            }
        finally:
            session.close()

    def analyze(self, project_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            project = self._project_row(session, project_id)
            existing = list(session.scalars(select(SolutionRequirement).where(SolutionRequirement.solution_project_id == project.id)).all())
            if not existing:
                for item in self._requirements_for(project.customer_need):
                    session.add(SolutionRequirement(solution_project_id=project.id, **item))
            project.status = "REQUIREMENT_ANALYSIS"
            session.commit(); session.refresh(project)
            requirements = [self._requirement(row) for row in session.scalars(select(SolutionRequirement).where(SolutionRequirement.solution_project_id == project.id)).all()]
            gap = self._gap(session)
            project.status = "REQUIREMENT_ANALYSIS"
            session.commit(); session.refresh(project)
            return {"project": self._project(project), "requirements": requirements, "gap_analysis": gap, "label": "AI Generated Draft · NEEDS_CONFIRMATION"}
        finally:
            session.close()

    def blueprint(self, project_id: str, evidence_refs: list[dict[str, object]] | None = None, version_summary: str = "Generated Solution Blueprint draft") -> dict[str, object]:
        session = self._sessions()
        try:
            project = self._project_row(session, project_id)
            requirements = [self._requirement(row) for row in session.scalars(select(SolutionRequirement).where(SolutionRequirement.solution_project_id == project.id)).all()]
            if not requirements:
                raise ValueError("请先执行需求分析，再生成解决方案蓝图。")
            gap = self._gap(session)
            # None uses the legacy library view. An explicit empty list means
            # retrieval found no Evidence and must remain empty.
            evidence = self._evidence_refs(session) if evidence_refs is None else self._normalize_evidence_refs(evidence_refs)
            architecture = self._architecture()
            risks = self._risks(gap)
            blueprint = {
                "label": "AI Generated Draft · NEEDS_CONFIRMATION",
                "customer_problem": project.customer_need,
                "business_objective": project.objective or "待客户确认的业务目标。",
                "user_roles": ["Researcher", "Reviewer", "Leader", "Admin"],
                "core_workflow": ["Customer Need", "Requirement Understanding", "Knowledge Assessment", "Research / Computer Workflow", "Evidence & Validation", "Human Review", "Delivery Package"],
                "ai_capability": ["Research Master", "RAG Knowledge System", "Evidence Center", "Research Copilot", "Computer Lab（受控、审批前只分析）"],
                "data_architecture": {"available": gap["knowledge_base"], "needs_confirmation": "客户资料范围、授权和保留策略需确认。"},
                "system_architecture": architecture,
                "security_boundary": ["不读取 .env、token 或密码", "不自动上传客户资料", "不执行危险命令", "所有源码修改必须 Diff + Human Approval"],
                "human_review": "Requirements、Risk、Blueprint 和 Delivery Package 均为人工确认节点。",
                "implementation_roadmap": self._roadmap(),
                "acceptance_criteria": ["客户授权资料可追溯地完成导入与索引", "Evidence 可关联 paper_id / chunk_id / source", "高风险项已记录且由 Reviewer 决定", "交付内容带 AI Generated Draft 或 Human Reviewed 标记"],
                "evidence_refs": evidence,
                "risks": risks,
            }
            self._upsert_deliverable(session, project.id, "SOLUTION_BLUEPRINT", "Solution Blueprint", blueprint)
            self._upsert_deliverable(session, project.id, "TECHNICAL_ARCHITECTURE", "ResearchOS Technical Architecture", architecture)
            self._upsert_deliverable(session, project.id, "IMPLEMENTATION_PLAN", "Implementation Roadmap", self._roadmap())
            self._upsert_deliverable(session, project.id, "DATA_PLAN", "Data & Knowledge Assessment", gap)
            self._upsert_deliverable(session, project.id, "AI_WORKFLOW", "AI Workflow", blueprint["core_workflow"])
            self._upsert_computer_mission(session, project.id)
            self._version_snapshot(session, project.id, "DRAFT", version_summary, blueprint)
            project.status = "WAITING_REVIEW"; session.commit(); session.refresh(project)
            return {"project": self._project(project), "blueprint": blueprint, "metrics": self._metrics(session, project.id)}
        finally:
            session.close()

    def architecture(self, project_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            self._project_row(session, project_id)
            return {"label": "Installed ResearchOS architecture", **self._architecture()}
        finally:
            session.close()

    def risks(self, project_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            self._project_row(session, project_id)
            return {"label": "AI Generated Draft · NEEDS_CONFIRMATION", "risks": self._risks(self._gap(session))}
        finally:
            session.close()

    def review(self, project_id: str, status: str, note: str) -> dict[str, object]:
        session = self._sessions()
        try:
            project = self._project_row(session, project_id)
            project.review_status = status; project.review_note = note.strip()
            project.status = "APPROVED" if status == "APPROVED" else ("COMPLETED" if status == "REJECTED" else "WAITING_REVIEW")
            if status == "APPROVED":
                for row in session.scalars(select(SolutionDeliverable).where(SolutionDeliverable.solution_project_id == project.id)).all():
                    row.status = "HUMAN_REVIEWED"
            self._version_snapshot(session, project.id, "APPROVED" if status == "APPROVED" else "REVISED", f"Human Review: {status}", {"review_status": status, "reviewer_note": note.strip()}, created_by="Reviewer")
            session.commit(); session.refresh(project)
            return self._project(project)
        finally:
            session.close()

    def delivery_package(self, project_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            project = self._project_row(session, project_id)
            if project.review_status != "APPROVED":
                raise ValueError("Solution Review 尚未批准，不能生成 Delivery Package。")
            deliverables = [self._deliverable(row) for row in session.scalars(select(SolutionDeliverable).where(SolutionDeliverable.solution_project_id == project.id)).all()]
            if not deliverables:
                raise ValueError("请先生成 Solution Blueprint，再查看 Delivery Package。")
            blueprint = self._find(deliverables, "SOLUTION_BLUEPRINT")
            # Delivery packages inherit references from the persisted blueprint.
            # They are references only: never copied text and never fabricated.
            evidence_refs = []
            if blueprint and isinstance(blueprint.get("content"), dict):
                raw_refs = blueprint["content"].get("evidence_refs", [])
                if isinstance(raw_refs, list):
                    evidence_refs = self._normalize_evidence_refs(raw_refs)
            status = "Human Reviewed · AI Generated Draft · NEEDS_CONFIRMATION"
            package = {"label": status, "executive_summary": f"{project.title} 的解决方案交付草稿。", "customer_problem": project.customer_need,
                       "solution_blueprint": blueprint, "architecture": self._find(deliverables, "TECHNICAL_ARCHITECTURE"),
                       "implementation_roadmap": self._find(deliverables, "IMPLEMENTATION_PLAN"), "data_plan": self._find(deliverables, "DATA_PLAN"),
                       "ai_workflow": self._find(deliverables, "AI_WORKFLOW"), "risk_and_security": self._risks(self._gap(session)),
                       "evidence_references": evidence_refs,
                       "acceptance_criteria": ["客户确认需求范围", "资料授权与索引状态经检查", "高风险项完成人工审核", "交付内容明确草稿/审核状态"],
                       "next_steps": ["确认需求优先级与客户资料授权", "选择或创建组织与 Research Workspace", "运行受控验证并进行 Human Review"]}
            self._upsert_deliverable(session, project.id, "DELIVERY_REPORT", "FDE Delivery Package", package, status)
            project.status = "DELIVERY_READY"
            session.commit()
            return package
        finally:
            session.close()

    def computer_actions(self, project_id: str) -> dict[str, object]:
        """Return proposal-only Computer Lab actions; this route cannot execute them."""
        session = self._sessions()
        try:
            project = self._project_row(session, project_id)
            has_blueprint = session.scalar(
                select(SolutionDeliverable.id).where(
                    SolutionDeliverable.solution_project_id == project.id,
                    SolutionDeliverable.deliverable_type == "SOLUTION_BLUEPRINT",
                )
            )
            if has_blueprint:
                self._upsert_computer_mission(session, project.id)
                session.commit()
            rows = session.scalars(
                select(SolutionComputerMission)
                .where(SolutionComputerMission.solution_project_id == project_id)
                .order_by(SolutionComputerMission.created_at.asc())
            ).all()
            return {"label": "Computer Action Plan · WAITING_APPROVAL", "actions": [self._mission(row) for row in rows],
                    "boundary": "仅生成受控能力评估提案；不会执行文件、代码、终端或浏览器操作。"}
        finally:
            session.close()

    def versions(self, project_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            self._project_row(session, project_id)
            rows = session.scalars(select(SolutionVersion).where(SolutionVersion.solution_project_id == project_id).order_by(SolutionVersion.version.asc())).all()
            return {"label": "Solution Version Control", "versions": [self._version(row) for row in rows],
                    "boundary": "每个版本是 AI 草稿或人工审核记录，不等同于客户验收。"}
        finally:
            session.close()

    def _requirements_for(self, need: str) -> list[dict[str, str]]:
        # Labels describe an interpretation, never a confirmed customer fact.
        return [
            {"requirement_type": "BUSINESS", "description": "集中管理已授权科研资料，并让研究方向与交付物可追溯。", "priority": "HIGH", "source": "AI_GENERATED_DRAFT", "status": "NEEDS_CONFIRMATION"},
            {"requirement_type": "DATA", "description": "确认 PDF、论文、项目资料的授权范围、格式、保留与索引策略。", "priority": "HIGH", "source": "AI_GENERATED_DRAFT", "status": "NEEDS_CONFIRMATION"},
            {"requirement_type": "AI", "description": "使用现有 RAG、Research Master、Evidence Retrieval 与受控 Computer Lab 能力。", "priority": "MEDIUM", "source": "RESEARCHOS_CAPABILITY", "status": "NEEDS_CONFIRMATION"},
            {"requirement_type": "SYSTEM", "description": "提供 Workspace、知识空间、审阅队列和可追溯交付视图。", "priority": "MEDIUM", "source": "AI_GENERATED_DRAFT", "status": "NEEDS_CONFIRMATION"},
            {"requirement_type": "DELIVERY", "description": "输出可审阅的 Solution Blueprint、实施路线和交付包草稿。", "priority": "MEDIUM", "source": "AI_GENERATED_DRAFT", "status": "NEEDS_CONFIRMATION"},
            {"requirement_type": "SECURITY", "description": "客户资料授权、身份认证和权限边界需在实施前由客户确认。", "priority": "HIGH", "source": "AI_GENERATED_DRAFT", "status": "NEEDS_CONFIRMATION"},
        ]

    def _gap(self, session: Session) -> dict[str, object]:
        papers = int(session.scalar(select(func.count(Paper.paper_id))) or 0)
        chunks = int(session.scalar(select(func.count(PaperChunk.id))) or 0)
        return {
            "knowledge_base": {"status": "AVAILABLE" if papers and chunks else "MISSING", "detail": f"当前本地实例：{papers} papers / {chunks} chunks。"},
            "evidence": {"status": "AVAILABLE" if chunks else "MISSING", "detail": "Evidence 仅来自已上传资料的 paper / chunk 引用。"},
            "customer_data_scope": {"status": "NEEDS_CONFIRMATION", "detail": "客户资料范围、授权、保留周期与敏感信息边界尚未确认。"},
            "authentication": {"status": "MISSING", "detail": "当前版本是组织/角色产品模型，不是生产身份提供商集成。"},
            "requirement_readiness": "NEEDS_CONFIRMATION",
        }

    @staticmethod
    def _architecture() -> dict[str, object]:
        return {"flow": ["User", "Workspace", "Knowledge Layer", "RAG + FAISS", "Research / Computer Agent", "Evidence Center", "Human Review", "Delivery Package"],
                "components": {"frontend": "Vue 3 CDN", "backend": "FastAPI", "database": "SQLite", "vector_store": "FAISS", "llm": "Qwen / DashScope", "agent_runtime": "Research Master + Finite Loop", "computer_agent": "Controlled Computer Use + Diff Approval"}}

    @staticmethod
    def _roadmap() -> list[dict[str, object]]:
        phases = [("Foundation", "确认目标、组织与授权边界"), ("Knowledge", "导入授权资料并检查解析、Chunk、Embedding 与索引"), ("AI Agent", "配置 Research / Evidence / Computer 受控任务"), ("Workflow", "执行可审阅工作流和 Human Review"), ("Delivery", "生成草稿、验证验收标准并由客户确认")]
        return [{"phase": index + 1, "name": name, "goal": goal, "tasks": [goal], "dependencies": "上一阶段已确认", "expected_output": f"{name} draft", "risk": "NEEDS_CONFIRMATION", "acceptance_criteria": "负责人确认范围与产物状态"} for index, (name, goal) in enumerate(phases)]

    @staticmethod
    def _risks(gap: dict[str, object]) -> list[dict[str, str]]:
        return [
            {"type": "DATA_MISSING", "level": "HIGH" if gap["knowledge_base"]["status"] == "MISSING" else "MEDIUM", "reason": gap["customer_data_scope"]["detail"], "recommendation": "在导入前确认授权资料范围并检查索引状态。", "requires_human_review": "true"},
            {"type": "EVIDENCE_INSUFFICIENT", "level": "HIGH" if gap["evidence"]["status"] == "MISSING" else "LOW", "reason": gap["evidence"]["detail"], "recommendation": "资料不足时停止生成科研结论，补充真实资料后再验证。", "requires_human_review": "true"},
            {"type": "SECURITY", "level": "HIGH", "reason": gap["authentication"]["detail"], "recommendation": "生产部署前完成身份、权限与客户数据治理评审。", "requires_human_review": "true"},
            {"type": "DELIVERY", "level": "MEDIUM", "reason": "AI 输出为交付草稿，不构成客户验收。", "recommendation": "使用 Solution Review Center 进行客户与负责人确认。", "requires_human_review": "true"},
        ]

    def _evidence_refs(self, session: Session) -> list[dict[str, str]]:
        rows = session.execute(select(PaperChunk.id, PaperChunk.paper_id, Paper.title, Paper.filename, PaperChunk.section_title).join(Paper, PaperChunk.paper_id == Paper.paper_id).limit(5)).all()
        return [{"paper_id": paper_id, "chunk_id": chunk_id, "source": filename or title, "section": section or "正文"} for chunk_id, paper_id, title, filename, section in rows]

    def _upsert_deliverable(self, session: Session, project_id: str, kind: str, title: str, content: object, status: str = "AI_GENERATED_DRAFT") -> None:
        row = session.scalar(select(SolutionDeliverable).where(SolutionDeliverable.solution_project_id == project_id, SolutionDeliverable.deliverable_type == kind))
        encoded = json.dumps(content, ensure_ascii=False, default=str)
        if row is None:
            session.add(SolutionDeliverable(solution_project_id=project_id, deliverable_type=kind, title=title, content=encoded, status=status))
        else:
            row.title = title; row.content = encoded; row.status = status

    @staticmethod
    def _upsert_computer_mission(session: Session, project_id: str) -> None:
        row = session.scalar(select(SolutionComputerMission).where(SolutionComputerMission.solution_project_id == project_id))
        values = {
            "task": "检查 ResearchOS 已有能力与已确认需求的覆盖情况",
            "change_summary": "只生成 Capability Assessment 与 Implementation Proposal；不修改源码、不执行电脑操作。",
            "risk_level": "MEDIUM",
            "status": "WAITING_APPROVAL",
        }
        if row is None:
            session.add(SolutionComputerMission(solution_project_id=project_id, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)

    @staticmethod
    def _version_snapshot(session: Session, project_id: str, status: str, summary: str, snapshot: object, created_by: str = "AI") -> None:
        maximum = session.scalar(select(func.max(SolutionVersion.version)).where(SolutionVersion.solution_project_id == project_id)) or 0
        session.add(SolutionVersion(solution_project_id=project_id, version=int(maximum) + 1, status=status,
                                    change_summary=summary, snapshot_json=json.dumps(snapshot, ensure_ascii=False, default=str), created_by=created_by))

    @staticmethod
    def _normalize_evidence_refs(rows: list[dict[str, object]]) -> list[dict[str, str]]:
        refs: list[dict[str, str]] = []
        for item in rows:
            paper_id, chunk_id = str(item.get("paper_id", "")), str(item.get("chunk_id", ""))
            if not paper_id or not chunk_id:
                continue
            refs.append({"paper_id": paper_id, "chunk_id": chunk_id, "source": str(item.get("source") or item.get("filename") or item.get("paper_title") or "未命名资料"), "section": str(item.get("section") or "正文")})
        return refs

    @staticmethod
    def _find(deliverables: list[dict[str, object]], kind: str) -> dict[str, object] | None:
        return next((item for item in deliverables if item["deliverable_type"] == kind), None)

    def _metrics(self, session: Session, project_id: str) -> dict[str, int]:
        return {"requirements_parsed": int(session.scalar(select(func.count(SolutionRequirement.id)).where(SolutionRequirement.solution_project_id == project_id)) or 0),
                "evidence_linked": len(self._evidence_refs(session)),
                "risks_identified": len(self._risks(self._gap(session))),
                "review_items": 1,
                "deliverables_generated": int(session.scalar(select(func.count(SolutionDeliverable.id)).where(SolutionDeliverable.solution_project_id == project_id)) or 0),
                "implementation_steps": len(self._roadmap())}

    @staticmethod
    def _project_row(session: Session, project_id: str) -> SolutionProject:
        row = session.get(SolutionProject, project_id)
        if row is None:
            raise SolutionNotFoundError("Solution Project 不存在。")
        return row

    @staticmethod
    def _project(row: SolutionProject) -> dict[str, object]:
        return {"id": row.id, "title": row.title, "customer_need": row.customer_need, "industry": row.industry, "objective": row.objective, "status": row.status, "review_status": row.review_status, "review_note": row.review_note, "created_at": row.created_at, "updated_at": row.updated_at}

    @staticmethod
    def _requirement(row: SolutionRequirement) -> dict[str, object]:
        return {"id": row.id, "requirement_type": row.requirement_type, "description": row.description, "priority": row.priority, "source": row.source, "status": row.status}

    @staticmethod
    def _deliverable(row: SolutionDeliverable) -> dict[str, object]:
        try: content = json.loads(row.content)
        except json.JSONDecodeError: content = {}
        return {"id": row.id, "deliverable_type": row.deliverable_type, "title": row.title, "content": content, "status": row.status, "created_at": row.created_at}

    @staticmethod
    def _mission(row: SolutionComputerMission) -> dict[str, object]:
        return {"id": row.id, "task": row.task, "change_summary": row.change_summary, "risk_level": row.risk_level,
                "status": row.status, "created_at": row.created_at, "execution_allowed": False}

    @staticmethod
    def _version(row: SolutionVersion) -> dict[str, object]:
        return {"id": row.id, "version": row.version, "status": row.status, "change_summary": row.change_summary, "created_by": row.created_by, "created_at": row.created_at}
