"""Read-only solution-delivery views for ResearchOS P5.

The service turns existing, observable workspace data into a presales and
delivery *proposal*.  It never runs an Agent, alters a customer workspace, or
turns potential value into an unverified performance claim.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Callable

from sqlalchemy import func, select

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.research_memory import ResearchMemory
from app.models.research_task import ResearchTask
from app.models.research_workspace import ResearchWorkspace
from app.services.database import SessionLocal, initialize_database


class ResearchSolutionDeliveryService:
    """Build safe P5 scenario, value, blueprint and delivery representations."""

    SCENARIOS = (
        {
            "scenario_id": "university_lab_management",
            "name": "高校实验室科研管理",
            "customer_type": "高校实验室",
            "pain_points": ["文献资料持续增长", "学生阅读与交接成本高", "研究方向与依据难以沉淀"],
            "workflow": ["资料上传", "AI 分析", "Evidence 整理", "研究空白辅助识别", "Research Brief"],
            "expected_value": ["集中管理已授权科研资料", "让研究讨论可追溯到 Evidence", "为负责人审核提供统一工作空间"],
        },
        {
            "scenario_id": "enterprise_rd_research",
            "name": "企业研发部门技术调研",
            "customer_type": "企业研发部门",
            "pain_points": ["技术资料分散", "调研结论缺少来源说明", "合作方向准备周期长"],
            "workflow": ["需求澄清", "知识检索", "Evidence 对比", "人工审核", "技术调研草案"],
            "expected_value": ["辅助建立技术调研资料边界", "让不同条件下的 Evidence 可复核", "支持后续技术方案沟通"],
        },
        {
            "scenario_id": "joint_research_proposal",
            "name": "横向科研项目申报",
            "customer_type": "产学研合作团队",
            "pain_points": ["企业需求与研究能力映射不清", "项目资料缺少共同审核路径", "成果规划难以衔接"],
            "workflow": ["客户需求整理", "Research Workspace", "Evidence Review", "项目方案草案", "负责人确认"],
            "expected_value": ["辅助对齐需求、资料与验收边界", "保留人工确认节点", "形成可沟通的项目交付草案"],
        },
    )

    def __init__(
        self,
        session_factory: Callable[[], Any] = SessionLocal,
        *,
        initialize: bool = True,
    ) -> None:
        self._sessions = session_factory
        if initialize:
            initialize_database()

    def list_scenarios(self) -> list[dict[str, object]]:
        return [dict(item) for item in self.SCENARIOS]

    def scenario(self, scenario_id: str) -> dict[str, object]:
        item = next((candidate for candidate in self.SCENARIOS if candidate["scenario_id"] == scenario_id), None)
        if item is None:
            raise ValueError("未找到该客户场景模板。")
        return dict(item)

    def admin_overview(self) -> dict[str, object]:
        """Use stored counts only; no demo records or synthetic metrics."""
        session = self._sessions()
        try:
            papers = int(session.scalar(select(func.count(Paper.paper_id))) or 0)
            evidence = int(session.scalar(select(func.count(PaperChunk.id))) or 0)
            workspaces = int(session.scalar(select(func.count(ResearchWorkspace.id))) or 0)
            tasks = int(session.scalar(select(func.count(ResearchTask.id))) or 0)
            snapshots = list(session.scalars(
                select(ResearchMemory.memory_json).where(ResearchMemory.scope.like("research_workspace:%"))
            ))
        finally:
            session.close()

        review_counts: Counter[str] = Counter()
        for raw in snapshots:
            try:
                payload = json.loads(raw or "{}")
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            for item in payload.get("review_items", []):
                if isinstance(item, dict):
                    review_counts[str(item.get("status", "pending"))] += 1
        return {
            "workspace_count": workspaces,
            "research_task_count": tasks,
            "paper_count": papers,
            "evidence_count": evidence,
            "review_status": {
                "pending": review_counts["pending"],
                "approved": review_counts["approved"],
                "rejected": review_counts["rejected"],
            },
            "boundary": "管理概览仅统计当前本地运行状态；不会创建 Demo 工作空间、任务或 Evidence。",
        }

    def roi_dashboard(self) -> dict[str, object]:
        """Return measurable assets plus deliberately non-numeric potential indicators."""
        overview = self.admin_overview()
        return {
            "research_assets": {
                "papers": overview["paper_count"],
                "evidence": overview["evidence_count"],
                "workspaces": overview["workspace_count"],
                "research_tasks": overview["research_task_count"],
            },
            "research_topic_coverage": {
                "status": "not_evaluated",
                "detail": "尚未对真实资料运行主题聚类；系统不以论文数量冒充研究主题覆盖。",
            },
            "potential_value_indicators": [
                {"name": "资料集中管理", "type": "potential", "detail": "可用于评估已授权资料是否在同一知识空间中可检索。"},
                {"name": "人工整理步骤", "type": "potential", "detail": "可用于评估资料入库、Evidence 复核与交付草案之间的人工交接步骤。"},
                {"name": "重复检索", "type": "potential", "detail": "可用于评估团队是否能复用同一 Evidence 与审核记录。"},
            ],
            "boundary": "Potential Value Indicators 不代表已实现的效率收益、ROI、准确率或客户成效。",
        }

    def blueprint(self, scenario_id: str) -> dict[str, object]:
        scenario = self.scenario(scenario_id)
        return {
            "scenario": scenario,
            "customer_problem": list(scenario["pain_points"]),
            "ai_solution": ["Research Workspace", "Evidence-driven Research Agent", "Human Review", "Research Brief"],
            "technical_architecture": ["Vue 3", "FastAPI", "RAG + FAISS", "Evidence Grounding", "Finite Research Loop"],
            "delivery_process": ["确认授权资料与目标", "资料导入并检查索引", "配置团队审核流程", "执行受控研究任务", "客户确认交付草案"],
            "expected_outcome": list(scenario["expected_value"]),
            "boundary": "这是可售卖解决方案的演示蓝图；不会自动配置客户系统、导入资料或生成未经 Evidence 支撑的科研结论。",
        }

    def demo_flow(self, scenario_id: str) -> dict[str, object]:
        """Return a presentation sequence with only live counters attached."""
        scenario = self.scenario(scenario_id)
        overview = self.admin_overview()
        review_status = "pending_review" if overview["review_status"]["pending"] else "no_pending_review"
        steps = [
            "客户提出：分析 RAG 技术发展方向",
            "创建 / 选择 Research Workspace",
            "AI 制定 Research Strategy",
            "Evidence 分析与条件差异检查",
            "Review 风险与人工确认",
            "生成 Research Brief 草案",
        ]
        return {
            "scenario_id": scenario["scenario_id"],
            "is_demo": True,
            "steps": [
                {
                    "step": index + 1,
                    "title": title,
                    "status": "planned",
                    "evidence_count": overview["evidence_count"],
                    "review_status": review_status,
                }
                for index, title in enumerate(steps)
            ],
            "boundary": "Demo Flow 仅说明交付路径；不会创建 Workspace、发起 Agent、生成科研结论或改变人工审核状态。",
        }

    def delivery_report(self, scenario_id: str) -> dict[str, object]:
        scenario = self.scenario(scenario_id)
        overview = self.admin_overview()
        evidence_status = (
            f"当前实例可见 {overview['paper_count']} 篇资料与 {overview['evidence_count']} 个知识片段；"
            "该状态只说明本地资料与索引数量，不替代客户验收。"
        )
        return {
            "title": f"{scenario['name']} · Customer Delivery Report",
            "scenario": scenario,
            "customer_background": f"面向{scenario['customer_type']}的 ResearchOS 方案演示。",
            "requirement_analysis": list(scenario["pain_points"]),
            "solution_design": self.blueprint(scenario_id)["ai_solution"],
            "implementation_process": self.blueprint(scenario_id)["delivery_process"],
            "validation_result": [
                evidence_status,
                "正式验收应检查：资料来源范围、索引状态、Evidence 可追溯性与人工审核记录。",
            ],
            "future_optimization": ["依据客户授权资料补充主题与覆盖评估", "接入真实身份、权限与协作审计", "以客户验收反馈迭代研究工作流"],
            "boundary": "AI辅助生成的客户交付方案，需客户确认；不是已完成客户实施或收益承诺。",
        }
