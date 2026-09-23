"""A small agent that chooses a paper-analysis template and runs it."""

from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

from app.services.llm_service import (
    analyze_paper_with_template,
    answer_question_about_paper,
    build_quality_check,
)
from app.services.pdf_service import extract_pdf_text
from app.agent.scenario_config import (
    RoleConfig,
    ScenarioConfig,
    ScenarioTask,
    get_role_config,
    get_scenario_config,
)


MAX_STORED_PAPER_CHARS = 120_000
MAX_CONVERSATION_TURNS = 3
MAX_FOLLOW_UP_QUESTION_CHARS = 2_000


class PaperNotFoundError(Exception):
    """Raised when a follow-up refers to an expired or unknown paper."""


class PaperTextTooLongError(Exception):
    """Raised when extracted text is too large for this simple in-memory MVP."""


class ConversationContextTooLongError(Exception):
    """Raised when one follow-up question is too large for the MVP context limit."""


class TaskNotRecognizedError(Exception):
    """Raised when the task does not look like a paper-analysis request."""


class TaskType(str, Enum):
    """The small set of analysis tasks supported by this MVP agent."""

    OVERALL_ANALYSIS = "论文整体分析"
    SUMMARY = "论文摘要"
    METHOD_ANALYSIS = "研究方法分析"
    INNOVATION_ANALYSIS = "创新点分析"
    CONCLUSION_ANALYSIS = "主要结论分析"
    LIMITATION_ANALYSIS = "局限性分析"
    PAPER_QA = "论文问答"


@dataclass(frozen=True)
class TaskTemplate:
    """Prompt instructions and output fields for one task type."""

    task_type: TaskType
    agent_task: str
    keywords: tuple[str, ...]
    instruction: str
    result_fields: tuple[str, ...]


TASK_TEMPLATES = (
    TaskTemplate(
        TaskType.SUMMARY,
        "summary",
        ("摘要", "概括", "总结", "简述"),
        "用简洁中文概括研究背景、目标、方法、结果和结论。",
        ("论文摘要",),
    ),
    TaskTemplate(
        TaskType.METHOD_ANALYSIS,
        "experiment",
        ("研究方法", "实验方法", "方法", "实验设计", "实验", "技术路线"),
        "说明研究对象、数据或材料、实验或分析方法，以及方法是否足以回答研究问题。",
        ("研究方法",),
    ),
    TaskTemplate(
        TaskType.INNOVATION_ANALYSIS,
        "innovation",
        ("创新", "贡献", "新颖"),
        "提炼论文明确提出的创新点；不要把常规工作误称为创新。",
        ("创新点",),
    ),
    TaskTemplate(
        TaskType.LIMITATION_ANALYSIS,
        "limitation",
        ("局限", "不足", "缺陷"),
        "说明论文作者明确提到的局限性；若未说明，可基于研究设计谨慎指出合理限制，并标明是推断。",
        ("局限性",),
    ),
    TaskTemplate(
        TaskType.CONCLUSION_ANALYSIS,
        "conclusion",
        ("主要结论", "结论", "主要发现"),
        "说明研究得到的主要发现，以及这些发现支持的结论。",
        ("主要结论",),
    ),
    TaskTemplate(
        TaskType.PAPER_QA,
        "qa",
        ("请问", "为什么", "如何", "是否", "能否", "怎样"),
        "直接回答用户的问题，并用论文中的证据支撑回答。",
        ("论文问答",),
    ),
)

OVERALL_TEMPLATE = TaskTemplate(
    TaskType.OVERALL_ANALYSIS,
    "overall_analysis",
    (),
    "完整说明论文主题、研究问题、研究方法、主要结果、主要结论和局限性。",
    ("论文主题", "研究问题", "研究方法", "主要结果", "主要结论", "局限性"),
)


@dataclass
class AgentPlan:
    """A simple explanation of how the agent will handle a user task."""

    user_task: str
    user_role: str
    role_name: str
    scenario: str
    document_type: str
    user_intent: str
    task_type: str
    detected_tasks: list[str]
    decision_reason: str
    execution_plan: list[str]


@dataclass
class ConversationTurn:
    """One completed user question and agent answer for a paper."""

    question: str
    answer: str


class PaperAnalysisAgent:
    """Coordinates the existing PDF and LLM services for one paper at a time."""

    def __init__(self) -> None:
        # This is deliberately in-memory for the MVP. Restarting the server clears it.
        self._papers: dict[str, str] = {}
        self._conversations: dict[str, list[ConversationTurn]] = {}

    def understand_task(
        self, task: str, scenario: str = "paper", role: str = "researcher"
    ) -> tuple[
        AgentPlan,
        tuple[TaskTemplate | ScenarioTask, ...],
        ScenarioConfig,
        RoleConfig,
    ]:
        """Recognize tasks and choose templates for one supported document scenario."""
        normalized_task = task.strip()
        if not normalized_task:
            raise ValueError("请输入分析任务。")
        scenario_config = get_scenario_config(scenario)
        role_config = get_role_config(role)
        if not self._looks_like_analysis_task(normalized_task, scenario_config):
            raise TaskNotRecognizedError(
                "暂时无法识别该分析任务，请说明你希望了解文档的哪些内容。"
            )

        if scenario_config.identifier == "paper":
            templates = self._select_templates(normalized_task)
        else:
            templates = self._select_scenario_templates(normalized_task, scenario_config)
        detected_tasks = [template.agent_task for template in templates]
        task_names = "、".join(self._template_display_name(template) for template in templates)
        if len(templates) > 1:
            decision_reason = (
                f"用户需求包含{task_names}，因此 Agent 在{scenario_config.name}场景选择多个分析任务组合执行。"
            )
            task_type = f"组合分析（{task_names}）"
        elif templates[0] is OVERALL_TEMPLATE or templates[0] is scenario_config.overall_task:
            decision_reason = (
                f"用户未指定单一分析重点，因此 Agent 选择{scenario_config.name}整体分析。"
            )
            task_type = self._template_display_name(templates[0])
        else:
            decision_reason = (
                f"用户需求聚焦{task_names}，因此 Agent 选择对应的分析模板。"
            )
            task_type = self._template_display_name(templates[0])

        document_label = "论文" if scenario_config.identifier == "paper" else "文档"
        execution_plan = [
            f"识别{role_config.name}的目标并选择：{task_names}",
            "解析 PDF 文本",
            f"保存当前{document_label}文本以支持后续追问",
            f"使用{task_names}与{role_config.name}视角调用大模型生成结构化结果",
            "校验并整理分析结果、决策报告与业务价值报告",
        ]
        return (
            AgentPlan(
                user_task=normalized_task,
                user_role=role_config.identifier,
                role_name=role_config.name,
                scenario=scenario_config.identifier,
                document_type=scenario_config.document_type,
                user_intent=normalized_task,
                task_type=task_type,
                detected_tasks=detected_tasks,
                decision_reason=decision_reason,
                execution_plan=execution_plan,
            ),
            templates,
            scenario_config,
            role_config,
        )

    def analyze_pdf(
        self,
        file_content: bytes,
        task: str,
        scenario: str = "paper",
        role: str = "researcher",
    ) -> dict[str, object]:
        """Run the full agent workflow for one uploaded PDF and scenario."""
        plan, templates, scenario_config, role_config = self.understand_task(
            task, scenario, role
        )
        paper_text = extract_pdf_text(file_content)
        if len(paper_text) > MAX_STORED_PAPER_CHARS:
            raise PaperTextTooLongError(
                "论文文本过长，请上传篇幅更短的论文后重试。"
            )

        paper_id = str(uuid4())
        self._papers[paper_id] = paper_text
        self._conversations[paper_id] = []
        task_instruction = "\n".join(
            instruction
            for instruction in (
                scenario_config.prompt_context,
                role_config.prompt_context,
                *(template.instruction for template in templates),
            )
            if instruction
        )
        model_result = analyze_paper_with_template(
            paper_text=paper_text,
            task=plan.user_task,
            task_instruction=task_instruction,
            result_fields=scenario_config.output_fields,
            list_fields=scenario_config.list_fields,
            require_all_fields=True,
            include_decision_report=True,
            include_business_report=True,
        )
        analysis = model_result["analysis"]
        decision_report = model_result["decision_report"]
        business_report = model_result["business_report"]
        quality_check = build_quality_check(
            scenario_config.identifier,
            analysis,
            decision_report,
        )
        evidence_cards = self._build_evidence_cards(
            scenario_config.identifier, analysis
        )

        return {
            "paper_id": paper_id,
            "task": plan.user_task,
            "scenario": plan.scenario,
            "user_role": plan.user_role,
            "role_name": plan.role_name,
            "document_type": plan.document_type,
            "user_intent": plan.user_intent,
            "task_type": plan.task_type,
            "user_task": plan.user_task,
            "detected_tasks": plan.detected_tasks,
            "decision_reason": plan.decision_reason,
            "execution_plan": plan.execution_plan,
            "plan": plan.execution_plan,
            "agent_trace": self._build_agent_trace(plan, role_config),
            "analysis": analysis,
            "result": analysis,
            "decision_report": decision_report,
            "business_report": business_report,
            "evidence_sources": self._build_evidence_sources(
                scenario_config.identifier, analysis
            ),
            "evidence_cards": evidence_cards,
            "trust_report": self._build_trust_report(
                quality_check, evidence_cards, role_config
            ),
            "value_estimation": self._build_value_estimation(
                scenario_config.identifier, role_config
            ),
            "quality_check": quality_check,
            "summary": {
                field: analysis[field] for field in scenario_config.summary_fields
            },
        }

    @staticmethod
    def _build_agent_trace(
        plan: AgentPlan, role_config: RoleConfig
    ) -> dict[str, object]:
        """Return an execution summary, not hidden model reasoning."""
        strategy = {
            "researcher": "从技术路线、核心创新、技术风险与后续研究维度分析。",
            "product_manager": "从用户价值、功能机会、商业价值与竞争差异维度分析。",
            "pre_sales_consultant": "从客户需求、方案匹配、实施风险与沟通建议维度分析。",
        }[role_config.identifier]
        return {
            "user_goal": plan.user_task,
            "user_role": plan.role_name,
            "analysis_strategy": strategy,
            "selected_tools": [
                "PDF 文本解析",
                "DashScope qwen-plus",
                "JSON 结构化校验",
                "规则质量检查",
            ],
            "execution_steps": plan.execution_plan,
        }

    @classmethod
    def _build_evidence_sources(
        cls, scenario: str, analysis: dict[str, object]
    ) -> list[dict[str, str]]:
        """Expose honest section-level evidence hints without claiming page precision."""
        section_hints = {
            "paper": {
                "research_topic": "摘要、引言相关内容",
                "methodology": "方法与实验相关内容",
                "innovation_points": "引言、方法与结论相关内容",
            },
            "technical_document": {
                "technical_solution": "技术方案与架构相关内容",
                "core_modules": "系统组成与模块说明相关内容",
                "implementation_recommendations": "实施说明与风险相关内容",
            },
            "product_document": {
                "product_positioning": "产品介绍与目标用户相关内容",
                "user_value": "用户需求与价值说明相关内容",
                "application_scenarios": "应用场景与业务说明相关内容",
            },
        }
        return [
            {"field": field, "source_section": source_section}
            for field, source_section in section_hints.get(scenario, {}).items()
            if cls._evidence_finding(analysis.get(field))
        ]

    @classmethod
    def _build_evidence_cards(
        cls, scenario: str, analysis: dict[str, object]
    ) -> list[dict[str, str]]:
        """Create traceable section-level cards without claiming page precision."""
        cards: list[dict[str, str]] = []
        for source in cls._build_evidence_sources(scenario, analysis):
            value = analysis.get(source["field"])
            finding = cls._evidence_finding(value)
            if not finding:
                continue
            cards.append(
                {
                    "finding": finding,
                    "source_type": "文档章节",
                    "source": source["source_section"],
                    "support_level": "medium",
                }
            )
        return cards

    @staticmethod
    def _evidence_finding(value: object) -> str:
        """Keep an evidence card concise and omit explicit missing-value markers."""
        if isinstance(value, list):
            value = next((item for item in value if isinstance(item, str)), "")
        if not isinstance(value, str) or value.strip() in {"", "文档未说明", "论文未说明"}:
            return ""
        return value.strip()[:120]

    @staticmethod
    def _build_trust_report(
        quality_check: dict[str, object],
        evidence_cards: list[dict[str, str]],
        role_config: RoleConfig,
    ) -> dict[str, object]:
        """Expose rule-based coverage and uncertainty instead of claiming accuracy."""
        missing = quality_check.get("missing_information", [])
        uncertainties = [
            f"缺少{item}，相关判断需要结合原始资料复核。"
            for item in missing
            if isinstance(item, str)
        ]
        uncertainties.append("当前仅提供章节级证据提示，未进行精确页码或段落定位。")
        suggestions = {
            "researcher": "建议结合原始实验数据、评审意见或技术验证进一步确认。",
            "product_manager": "建议结合用户反馈、市场数据和竞品调研进一步验证。",
            "pre_sales_consultant": "建议结合客户访谈、现网环境与实施边界进一步确认。",
        }
        return {
            "confidence_score": int(quality_check.get("score", 0)),
            "information_basis": [
                f"依据：{card['source']}" for card in evidence_cards
            ] or ["依据：文档可提取文本"],
            "uncertainties": uncertainties,
            "verification_suggestions": [suggestions[role_config.identifier]],
        }

    @staticmethod
    def _build_value_estimation(
        scenario: str, role_config: RoleConfig
    ) -> dict[str, str]:
        """Describe qualitative value only; this MVP never invents metrics."""
        applications = {
            "paper": "研发评审、技术路线研究与专利资料初步研读",
            "technical_document": "技术方案评审、售前方案准备与实施风险沟通",
            "product_document": "产品规划、竞品资料研读与需求讨论",
        }
        return {
            "time_saved": "减少人工阅读、整理和首次归纳资料的重复工作。",
            "decision_support": f"帮助{role_config.name}快速聚焦关键机会、风险与待验证信息。",
            "application_scene": applications[scenario],
        }

    def answer_follow_up(self, paper_id: str, question: str) -> dict[str, object]:
        """Answer a new question using the paper and its recent conversation turns."""
        paper_text = self._papers.get(paper_id)
        if paper_text is None:
            raise PaperNotFoundError("当前论文不存在或已失效，请重新上传并分析论文。")

        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("请输入追问内容。")
        if len(normalized_question) > MAX_FOLLOW_UP_QUESTION_CHARS:
            raise ConversationContextTooLongError(
                "追问内容过长，请缩短问题后重试。"
            )

        conversation = self._conversations.setdefault(paper_id, [])
        recent_turns = conversation[-MAX_CONVERSATION_TURNS:]
        answer = answer_question_about_paper(
            paper_text,
            normalized_question,
            conversation_history=[
                {"question": turn.question, "answer": turn.answer}
                for turn in recent_turns
            ],
        )
        conversation.append(ConversationTurn(normalized_question, answer))
        self._conversations[paper_id] = conversation[-MAX_CONVERSATION_TURNS:]
        return {
            "paper_id": paper_id,
            "question": normalized_question,
            "answer": answer,
            "history_turns": len(self._conversations[paper_id]),
        }

    @staticmethod
    def _select_templates(task: str) -> tuple[TaskTemplate, ...]:
        """Choose focused templates in user mention order, or overall analysis."""
        question_template = next(
            template
            for template in TASK_TEMPLATES
            if template.task_type is TaskType.PAPER_QA
        )
        if any(keyword in task for keyword in question_template.keywords):
            return (question_template,)

        matched_templates: list[tuple[int, TaskTemplate]] = []
        for template in TASK_TEMPLATES:
            if template.task_type is TaskType.PAPER_QA:
                continue
            positions = [task.find(keyword) for keyword in template.keywords if keyword in task]
            if positions:
                matched_templates.append((min(positions), template))

        focused_templates = [
            template
            for _, template in sorted(matched_templates, key=lambda item: item[0])
        ]
        if focused_templates:
            return tuple(focused_templates)
        return (OVERALL_TEMPLATE,)

    @staticmethod
    def _select_template(task: str) -> TaskTemplate:
        """Keep the original helper available for code using a single template."""
        return PaperAnalysisAgent._select_templates(task)[0]

    @staticmethod
    def _select_scenario_templates(
        task: str, scenario_config: ScenarioConfig
    ) -> tuple[ScenarioTask, ...]:
        """Choose non-paper scenario tasks in user mention order, or use the overall task."""
        matched_tasks: list[tuple[int, ScenarioTask]] = []
        for scenario_task in scenario_config.supported_tasks:
            positions = [
                task.find(keyword)
                for keyword in scenario_task.keywords
                if keyword in task
            ]
            if positions:
                matched_tasks.append((min(positions), scenario_task))
        if not matched_tasks:
            return (scenario_config.overall_task,)
        return tuple(
            task_template
            for _, task_template in sorted(matched_tasks, key=lambda item: item[0])
        )

    @staticmethod
    def _template_display_name(template: TaskTemplate | ScenarioTask) -> str:
        """Return a display name for either the existing or scenario-specific template."""
        if isinstance(template, TaskTemplate):
            return template.task_type.value
        return template.display_name

    @staticmethod
    def _looks_like_analysis_task(task: str, scenario_config: ScenarioConfig) -> bool:
        """Accept ordinary document-analysis tasks for the chosen scenario."""
        task_markers = (
            "论文", "分析", "摘要", "研究", "方法", "创新", "结论", "局限",
            "总结", "概括", "问题", "结果", "说明", "告诉", "请", "什么", "文档",
        )
        scenario_keywords = (
            keyword
            for scenario_task in scenario_config.supported_tasks
            for keyword in scenario_task.keywords
        )
        return any(marker in task for marker in (*task_markers, *scenario_keywords))
