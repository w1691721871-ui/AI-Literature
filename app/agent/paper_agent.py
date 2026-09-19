"""A small agent that chooses a paper-analysis template and runs it."""

from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

from app.services.llm_service import (
    PAPER_ANALYSIS_FIELDS,
    PAPER_ANALYSIS_LIST_FIELDS,
    analyze_paper_with_template,
    answer_question_about_paper,
)
from app.services.pdf_service import extract_pdf_text


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
    keywords: tuple[str, ...]
    instruction: str
    result_fields: tuple[str, ...]


TASK_TEMPLATES = (
    TaskTemplate(
        TaskType.SUMMARY,
        ("摘要", "概括", "总结", "简述"),
        "用简洁中文概括研究背景、目标、方法、结果和结论。",
        ("论文摘要",),
    ),
    TaskTemplate(
        TaskType.METHOD_ANALYSIS,
        ("研究方法", "方法", "实验设计", "技术路线"),
        "说明研究对象、数据或材料、实验或分析方法，以及方法是否足以回答研究问题。",
        ("研究方法",),
    ),
    TaskTemplate(
        TaskType.INNOVATION_ANALYSIS,
        ("创新", "贡献", "新颖"),
        "提炼论文明确提出的创新点；不要把常规工作误称为创新。",
        ("创新点",),
    ),
    TaskTemplate(
        TaskType.LIMITATION_ANALYSIS,
        ("局限", "不足", "缺陷"),
        "说明论文作者明确提到的局限性；若未说明，可基于研究设计谨慎指出合理限制，并标明是推断。",
        ("局限性",),
    ),
    TaskTemplate(
        TaskType.CONCLUSION_ANALYSIS,
        ("主要结论", "结论", "主要发现"),
        "说明研究得到的主要发现，以及这些发现支持的结论。",
        ("主要结论",),
    ),
    TaskTemplate(
        TaskType.PAPER_QA,
        ("请问", "为什么", "如何", "是否", "能否", "怎样"),
        "直接回答用户的问题，并用论文中的证据支撑回答。",
        ("论文问答",),
    ),
)

OVERALL_TEMPLATE = TaskTemplate(
    TaskType.OVERALL_ANALYSIS,
    (),
    "完整说明论文主题、研究问题、研究方法、主要结果、主要结论和局限性。",
    ("论文主题", "研究问题", "研究方法", "主要结果", "主要结论", "局限性"),
)


@dataclass
class AgentPlan:
    """A simple explanation of how the agent will handle a user task."""

    task: str
    task_type: str
    steps: list[str]


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

    def understand_task(self, task: str) -> tuple[AgentPlan, TaskTemplate]:
        """Recognize a task type and choose its prompt template."""
        normalized_task = task.strip()
        if not normalized_task:
            raise ValueError("请输入分析任务。")
        if not self._looks_like_analysis_task(normalized_task):
            raise TaskNotRecognizedError(
                "暂时无法识别该分析任务，请说明你希望了解论文的哪些内容。"
            )

        template = self._select_template(normalized_task)
        steps = [
            "理解用户任务",
            f"识别任务类型：{template.task_type.value}",
            "提取 PDF 文本",
            f"选择{template.task_type.value}提示词模板",
            "调用大模型生成结果",
            "检查并整理结构化结果",
        ]
        return (
            AgentPlan(
                task=normalized_task,
                task_type=template.task_type.value,
                steps=steps,
            ),
            template,
        )

    def analyze_pdf(self, file_content: bytes, task: str) -> dict[str, object]:
        """Run the full agent workflow for one uploaded PDF."""
        plan, template = self.understand_task(task)
        paper_text = extract_pdf_text(file_content)
        if len(paper_text) > MAX_STORED_PAPER_CHARS:
            raise PaperTextTooLongError(
                "论文文本过长，请上传篇幅更短的论文后重试。"
            )

        paper_id = str(uuid4())
        self._papers[paper_id] = paper_text
        self._conversations[paper_id] = []
        analysis = analyze_paper_with_template(
            paper_text=paper_text,
            task=plan.task,
            task_instruction=template.instruction,
            result_fields=PAPER_ANALYSIS_FIELDS,
            list_fields=PAPER_ANALYSIS_LIST_FIELDS,
            require_all_fields=True,
        )

        return {
            "paper_id": paper_id,
            "task": plan.task,
            "task_type": plan.task_type,
            "plan": plan.steps,
            "analysis": analysis,
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
    def _select_template(task: str) -> TaskTemplate:
        """Choose one focused task, or use overall analysis for combined requests."""
        question_template = next(
            template
            for template in TASK_TEMPLATES
            if template.task_type is TaskType.PAPER_QA
        )
        if any(keyword in task for keyword in question_template.keywords):
            return question_template

        focused_templates = [
            template
            for template in TASK_TEMPLATES
            if template.task_type is not TaskType.PAPER_QA
            and any(keyword in task for keyword in template.keywords)
        ]
        if len(focused_templates) == 1:
            return focused_templates[0]
        return OVERALL_TEMPLATE

    @staticmethod
    def _looks_like_analysis_task(task: str) -> bool:
        """Accept ordinary Chinese paper-analysis requests and reject meaningless input."""
        task_markers = (
            "论文", "分析", "摘要", "研究", "方法", "创新", "结论", "局限",
            "总结", "概括", "问题", "结果", "说明", "告诉", "请", "什么",
        )
        return any(marker in task for marker in task_markers)
