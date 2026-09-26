"""Lightweight multi-Agent orchestration for the ResearchOS workspace.

This module intentionally reuses the project's existing retrieval and Qwen
services.  It is an explainable orchestration layer, not a claim that several
independent foundation models are running in parallel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.llm_service import complete_research_prompt, decode_research_json
from app.services.retrieval_service import RetrievalService


@dataclass(frozen=True)
class AgentDefinition:
    """Product-facing description of one ResearchOS specialist."""

    identifier: str
    name: str
    name_cn: str
    description: str
    purpose: str


AGENTS: tuple[AgentDefinition, ...] = (
    AgentDefinition("literature", "Literature Agent", "文献分析 Agent", "提炼研究背景、技术路线、实验方法与局限。", "形成文献理解基础"),
    AgentDefinition("knowledge", "Knowledge Agent", "知识管理 Agent", "从团队已上传资料中检索已有知识与相关证据。", "复用团队知识资产"),
    AgentDefinition("trend", "Trend Agent", "趋势分析 Agent", "归纳当前资料体现的热点、演进与待验证方向。", "辅助判断研究趋势"),
    AgentDefinition("innovation", "Innovation Agent", "创新发现 Agent", "从资料的不足和空白中提出审慎的研究机会。", "辅助发现创新方向"),
    AgentDefinition("project", "Project Agent", "项目规划 Agent", "将需求转换为技术匹配、研究任务与成果路径建议。", "辅助横向项目规划"),
    AgentDefinition("report", "Report Agent", "报告生成 Agent", "整合证据与各专项结论，输出可沟通的科研决策报告。", "形成结构化交付物"),
)
AGENT_BY_ID = {agent.identifier: agent for agent in AGENTS}


class ResearchMasterAgent:
    """Plan and coordinate research-specialist outputs on retrieved evidence."""

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self._retrieval_service = retrieval_service or RetrievalService()

    @staticmethod
    def catalog() -> list[dict[str, str]]:
        """Return safe metadata for the Agent-center UI."""
        return [
            {
                "id": agent.identifier,
                "name": agent.name,
                "name_cn": agent.name_cn,
                "description": agent.description,
                "purpose": agent.purpose,
            }
            for agent in AGENTS
        ]

    def plan_task(
        self,
        user_goal: str,
        selected_agents: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a deterministic, user-readable execution plan.

        Agent selection is deliberately rule-based so the planning summary
        always matches real code paths and is easy to explain in an interview.
        """
        goal = user_goal.strip()
        if not goal:
            raise ValueError("请输入需要完成的科研任务。")
        normalized = goal.lower()
        requested = [item for item in (selected_agents or []) if item in AGENT_BY_ID]
        if requested:
            selected = list(dict.fromkeys(requested))
        else:
            selected = ["literature", "knowledge"]
            if any(word in normalized for word in ("趋势", "热点", "发展", "现状", "方向")):
                selected.append("trend")
            if any(word in normalized for word in ("创新", "空白", "机会", "不足", "突破")):
                selected.append("innovation")
            if any(word in normalized for word in ("项目", "企业", "需求", "成果", "专利", "路线")):
                selected.append("project")
            selected.append("report")

        if "report" not in selected:
            selected.append("report")
        selected = list(dict.fromkeys(selected))
        workflow = [
            {"step": 1, "agent": "Research Master", "action": "理解研究需求", "purpose": "明确目标、资料范围和需要调度的专项能力"},
            {"step": 2, "agent": "Knowledge Agent", "action": "检索团队知识库", "purpose": "获取可追溯的论文与资料证据"},
        ]
        for agent_id in selected:
            if agent_id in {"knowledge", "report"}:
                continue
            agent = AGENT_BY_ID[agent_id]
            workflow.append({
                "step": len(workflow) + 1,
                "agent": agent.name,
                "action": f"执行{agent.name_cn}分析",
                "purpose": agent.purpose,
            })
        workflow.append({
            "step": len(workflow) + 1,
            "agent": "Report Agent",
            "action": "生成科研决策报告",
            "purpose": "整合已检索证据和各专项分析，输出可复核建议",
        })
        return {
            "user_goal": goal,
            "selected_agents": selected,
            "planning_summary": "Research Master 已按任务关键词选择专项 Agent；所有结论将以团队已上传资料的检索证据为依据。",
            "workflow_steps": workflow,
        }

    def run_task(
        self,
        user_goal: str,
        selected_agents: list[str] | None = None,
        paper_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve evidence, run specialist analysis, and return one report."""
        plan = self.plan_task(user_goal, selected_agents)
        sources = self._retrieval_service.retrieve(plan["user_goal"], paper_ids, top_k=8)
        if not sources:
            raise ValueError("团队知识库中暂无足够的已索引资料，请先上传并完成论文解析。")

        evidence = self._build_evidence(sources)
        selected = set(plan["selected_agents"])
        prompt = f"""你是 ResearchOS 的科研组织智能体。请基于团队知识库的检索证据，为科研负责人生成审慎、可复核的科研决策辅助结果。

用户目标：{plan['user_goal']}
已选择专项 Agent：{', '.join(plan['selected_agents'])}

重要边界：
1. 只能依据给出的团队资料；不得把资料外的全球趋势、代表机构或研究结论当作事实。
2. 证据不足时必须写“现有团队资料不足以判断”。
3. 创新方向、项目路径均为辅助建议，需由科研人员进一步验证。
4. 不展示模型思维过程，只输出面向用户的结构化结果。

返回且只返回 JSON 对象，字段必须包括：
executive_summary（字符串）、literature_analysis（对象）、knowledge_insights（对象）、trend_insights（对象）、innovation_opportunities（对象）、project_plan（对象）、report（对象）。
对象中使用简洁中文字符串或字符串数组。未选择的专项字段填写 {{"status":"未执行"}}。
report 对象必须含：背景分析、技术趋势、创新机会、技术路线、成果规划、风险与验证建议。

团队知识库证据：
{evidence}
"""
        raw = complete_research_prompt(prompt, json_mode=True)
        payload = decode_research_json(raw)
        result = self._normalize_result(payload, selected)
        result.update({
            "master_plan": plan,
            "agent_runs": self._agent_runs(plan, len(sources)),
            "sources": [self._public_source(source) for source in sources],
            "boundary_note": "本报告基于当前团队知识库中的已上传资料生成；趋势、创新与成果规划属于科研决策辅助，不替代专家评审或外部文献调研。",
        })
        return result

    def match_enterprise_requirement(
        self,
        enterprise_requirement: str,
        paper_ids: list[str] | None = None,
    ) -> dict[str, object]:
        """Use lab evidence to support a horizontal-project requirement review."""
        requirement = enterprise_requirement.strip()
        if not requirement:
            raise ValueError("请输入企业需求。")
        sources = self._retrieval_service.retrieve(requirement, paper_ids, top_k=6)
        if not sources:
            raise ValueError("团队知识库中暂无足够的已索引资料，无法完成能力匹配。")
        prompt = f"""你是 ResearchOS 的 Project Agent。请基于给出的实验室资料，分析企业横向项目需求。
只能使用证据中的信息；缺少资料时明确写“现有团队资料不足以判断”。
不要声称已验证技术可行性、已有企业合作或必然取得成果。

企业需求：{requirement}

只返回 JSON 对象，必须有以下字段：
lab_capability_match（字符串数组）、technical_solution_suggestions（字符串数组）、expected_outcome_plan（对象）、risks_and_questions（字符串数组）。
expected_outcome_plan 必须包含：研究任务、论文方向、专利方向、阶段性交付。

证据：
{self._build_evidence(sources)}
"""
        payload = decode_research_json(complete_research_prompt(prompt, json_mode=True))
        return {
            "enterprise_requirement": requirement,
            "lab_capability_match": self._string_list(payload.get("lab_capability_match")),
            "technical_solution_suggestions": self._string_list(payload.get("technical_solution_suggestions")),
            "expected_outcome_plan": self._object(payload.get("expected_outcome_plan")),
            "risks_and_questions": self._string_list(payload.get("risks_and_questions")),
            "sources": [self._public_source(source) for source in sources],
            "agent_trace": [
                {"agent": "Research Master", "status": "completed", "message": "已理解企业需求并分配能力匹配任务。"},
                {"agent": "Knowledge Agent", "status": "completed", "message": f"已检索 {len(sources)} 条团队资料证据。"},
                {"agent": "Project Agent", "status": "completed", "message": "已生成技术建议、成果路径与待确认风险。"},
            ],
            "boundary_note": "匹配结果仅依据当前团队知识库资料，需由项目负责人结合人员、设备、预算和现场条件进一步评审。",
        }

    def assess_research_value(
        self,
        research_goal: str,
        paper_ids: list[str] | None = None,
    ) -> dict[str, object]:
        """Produce an evidence-grounded value assessment for a research direction."""
        goal = research_goal.strip()
        if not goal:
            raise ValueError("请输入需要评估的研究方向。")
        sources = self._retrieval_service.retrieve(goal, paper_ids, top_k=6)
        if not sources:
            raise ValueError("团队知识库中暂无足够资料，无法完成科研价值评估。")
        prompt = f"""你是 ResearchOS 的 Value Agent。请只依据团队资料，对研究方向进行审慎的科研价值评估。
研究方向：{goal}
不得使用资料外的市场规模、论文数量或机构排名；资料不足时必须明确说明。
只返回 JSON 对象，包含：research_heat、innovation_potential、outcome_potential、assessment_basis、recommended_validation。
前三项是对象，必须有 level（high/medium/low）和 explanation；后两项为字符串数组。
证据：
{self._build_evidence(sources)}
"""
        payload = decode_research_json(complete_research_prompt(prompt, json_mode=True))
        return {
            "research_goal": goal,
            "research_heat": self._object(payload.get("research_heat")),
            "innovation_potential": self._object(payload.get("innovation_potential")),
            "outcome_potential": self._object(payload.get("outcome_potential")),
            "assessment_basis": self._string_list(payload.get("assessment_basis")),
            "recommended_validation": self._string_list(payload.get("recommended_validation")),
            "sources": [self._public_source(source) for source in sources],
            "agent_trace": [
                {"agent": "Value Agent", "status": "completed", "message": "已从团队知识库检索与研究方向相关的证据。"},
                {"agent": "Value Agent", "status": "completed", "message": "已完成热度、创新与成果潜力的辅助评估。"},
            ],
            "boundary_note": "科研价值评估反映当前团队资料覆盖情况，不等同于外部领域热度、技术可行性或成果成功概率。",
        }

    def generate_lab_profile(self) -> dict[str, object]:
        """Summarize a lab profile from indexed local material only."""
        sources = self._retrieval_service.retrieve("实验室研究方向 核心能力 论文 专利 合作方向", None, top_k=8)
        if not sources:
            raise ValueError("团队知识库中暂无足够资料，无法生成实验室能力画像。")
        prompt = f"""你是 ResearchOS 的 Knowledge Agent。只依据团队知识库证据，生成实验室科研能力画像。
不能把未在资料中出现的论文、专利、合作方或能力写成事实；信息不足时写“现有团队资料不足以判断”。
只返回 JSON 对象，字段：research_directions、core_capabilities、research_outputs、collaboration_directions、profile_summary。
前四项为字符串数组，profile_summary 为字符串。
证据：
{self._build_evidence(sources)}
"""
        payload = decode_research_json(complete_research_prompt(prompt, json_mode=True))
        return {
            "research_directions": self._string_list(payload.get("research_directions")),
            "core_capabilities": self._string_list(payload.get("core_capabilities")),
            "research_outputs": self._string_list(payload.get("research_outputs")),
            "collaboration_directions": self._string_list(payload.get("collaboration_directions")),
            "profile_summary": self._string(payload.get("profile_summary"), "现有团队资料不足以判断。"),
            "sources": [self._public_source(source) for source in sources],
            "boundary_note": "能力画像仅依据当前已上传资料生成，需由实验室负责人核验后用于对外展示或项目申报。",
        }

    @staticmethod
    def _build_evidence(sources: list[dict[str, object]]) -> str:
        sections: list[str] = []
        used = 0
        for index, source in enumerate(sources, start=1):
            text = str(source.get("content", "")).strip()
            if not text:
                continue
            item = (
                f"[证据 {index}] 标题：{source.get('paper_title', '未命名资料')}\n"
                f"章节：{source.get('section', '正文')}\n{text[:1700]}"
            )
            if used + len(item) > 12_000:
                break
            sections.append(item)
            used += len(item)
        return "\n\n".join(sections)

    @staticmethod
    def _normalize_result(payload: dict[str, object], selected: set[str]) -> dict[str, object]:
        labels = {
            "literature_analysis": "literature",
            "knowledge_insights": "knowledge",
            "trend_insights": "trend",
            "innovation_opportunities": "innovation",
            "project_plan": "project",
        }
        result: dict[str, object] = {
            "executive_summary": ResearchMasterAgent._string(payload.get("executive_summary"), "现有团队资料已完成初步分析。"),
            "report": ResearchMasterAgent._object(payload.get("report")),
        }
        for field, agent_id in labels.items():
            value = ResearchMasterAgent._object(payload.get(field))
            result[field] = value if agent_id in selected else {"status": "未执行"}
        return result

    @staticmethod
    def _agent_runs(plan: dict[str, Any], source_count: int) -> list[dict[str, str]]:
        runs = [{"agent": "Research Master", "status": "completed", "message": "已理解科研目标并制定任务编排。"}]
        runs.append({"agent": "Knowledge Agent", "status": "completed", "message": f"已从团队知识库检索 {source_count} 条相关证据。"})
        for agent_id in plan["selected_agents"]:
            if agent_id in {"knowledge", "report"}:
                continue
            agent = AGENT_BY_ID[agent_id]
            runs.append({"agent": agent.name, "status": "completed", "message": f"已依据检索证据完成{agent.name_cn}输出。"})
        runs.append({"agent": "Report Agent", "status": "completed", "message": "已汇总专项结果并生成科研决策报告。"})
        return runs

    @staticmethod
    def _public_source(source: dict[str, object]) -> dict[str, object]:
        content = str(source.get("content", "")).strip()
        return {
            "paper_id": source.get("paper_id", ""),
            "paper_title": source.get("paper_title", "未命名资料"),
            "filename": source.get("filename", source.get("paper_title", "未命名资料")),
            "document_type": source.get("document_type", "paper"),
            "section": source.get("section", "正文"),
            "content": content[:500] + ("…" if len(content) > 500 else ""),
            "score": round(float(source.get("score", 0)), 4),
        }

    @staticmethod
    def _object(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {"status": "现有团队资料不足以判断"}

    @staticmethod
    def _string(value: object, fallback: str) -> str:
        return value.strip() if isinstance(value, str) and value.strip() else fallback

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if isinstance(value, list):
            return [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return ["现有团队资料不足以判断"]
