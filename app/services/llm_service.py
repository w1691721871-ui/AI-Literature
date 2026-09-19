"""A small, isolated client for paper-analysis LLM requests."""

import json
import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI


logger = logging.getLogger(__name__)


# This prevents very large papers from being sent to the model in one request.
MAX_MODEL_INPUT_CHARS = 20_000
MAX_CONVERSATION_HISTORY_CHARS = 6_000
ANALYSIS_FIELDS = (
    "论文主题",
    "研究问题",
    "研究方法",
    "主要结果",
    "主要结论",
    "局限性",
)
PAPER_ANALYSIS_FIELDS = (
    "title",
    "research_topic",
    "research_question",
    "methodology",
    "key_findings",
    "innovation_points",
    "limitations",
    "keywords",
)
PAPER_ANALYSIS_LIST_FIELDS = (
    "key_findings",
    "innovation_points",
    "limitations",
    "keywords",
)


class LLMConfigurationError(Exception):
    """Raised when the API key has not been configured."""


class LLMRequestError(Exception):
    """Raised when the model provider cannot complete a request."""


def analyze_paper(paper_text: str) -> str:
    """Keep the original plain-text analysis function for the existing endpoint."""
    analysis = analyze_paper_for_task(paper_text, "请完成论文的整体分析。")
    return "\n".join(f"{field}：{analysis[field]}" for field in ANALYSIS_FIELDS)


def analyze_paper_for_task(paper_text: str, task: str) -> dict[str, object]:
    """Return the existing six-field overall analysis for the legacy endpoint."""
    return analyze_paper_with_template(
        paper_text=paper_text,
        task=task,
        task_instruction="完整说明论文的核心内容。",
        result_fields=ANALYSIS_FIELDS,
    )


def analyze_paper_with_template(
    paper_text: str,
    task: str,
    task_instruction: str,
    result_fields: tuple[str, ...],
    list_fields: tuple[str, ...] = (),
    require_all_fields: bool = False,
) -> dict[str, object]:
    """Run one task-specific prompt and return the requested JSON fields."""
    field_names = "、".join(result_fields)
    field_type_note = ""
    if list_fields:
        list_field_names = "、".join(list_fields)
        field_type_note = (
            f"The fields {list_field_names} must be JSON arrays of strings; use [] when absent. "
            "All other fields must be strings."
        )
    prompt = f"""You are a research-paper analysis assistant. The user task is:
{task}

Task-specific instructions:
{task_instruction}

Analyze the paper text below. Return only a valid JSON object with exactly these
keys: {field_names}.
{field_type_note}
Use only information supported by the paper. If a string detail is missing, use "论文未说明".

Paper text:
{paper_text[:MAX_MODEL_INPUT_CHARS]}
"""
    response_text = _request_model(prompt)
    return _parse_structured_result(
        response_text,
        result_fields,
        list_fields=list_fields,
        require_all_fields=require_all_fields,
    )


def answer_question_about_paper(
    paper_text: str,
    question: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    """Answer a follow-up using the current paper and a small recent history."""
    history_text = _format_conversation_history(conversation_history or [])
    prompt = f"""Answer the user's question about the research paper below in Chinese.
Use only information in the paper. If the paper does not provide the answer, say "论文未说明".

Recent conversation:
{history_text or "No previous questions."}

Question: {question}

Paper text:
{paper_text[:MAX_MODEL_INPUT_CHARS]}
"""
    return _request_model(prompt)


def _format_conversation_history(history: list[dict[str, str]]) -> str:
    """Keep the newest complete conversation turns within a small character limit."""
    selected_turns: list[str] = []
    used_chars = 0
    for turn in reversed(history):
        text = f"User: {turn['question']}\nAssistant: {turn['answer']}"
        if used_chars + len(text) > MAX_CONVERSATION_HISTORY_CHARS:
            break
        selected_turns.append(text)
        used_chars += len(text)
    return "\n\n".join(reversed(selected_turns))


def _request_model(prompt: str) -> str:
    """Send one safely-sized prompt to DashScope and return its text."""
    load_dotenv()
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise LLMConfigurationError("模型服务尚未配置，请联系管理员。")

    base_url = os.getenv(
        "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model = os.getenv("LLM_MODEL", "qwen-plus")
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.choices[0].message.content
        if not response_text:
            logger.warning("LLM returned an empty response")
            raise LLMRequestError("模型未返回有效内容，请稍后重试。")
        return response_text
    except LLMRequestError:
        raise
    except Exception as error:
        _log_llm_error(error)
        raise LLMRequestError(_friendly_llm_error(error)) from error


def _friendly_llm_error(error: Exception) -> str:
    """Convert provider errors into safe Chinese messages for API users."""
    status_code = getattr(error, "status_code", None)
    error_code = str(getattr(error, "code", "")).lower()
    error_text = str(error).lower()
    error_type = type(error).__name__.lower()

    if any(
        marker in f"{error_code} {error_text}"
        for marker in (
            "credit_balance_exhausted",
            "insufficient_quota",
            "allocationquota.freetieronly",
            "quota_exhausted",
        )
    ):
        return "模型服务额度不足，请在百炼控制台检查免费额度或模型权限。"
    if status_code in (401, 403):
        return "模型服务鉴权或权限配置异常，请检查百炼配置。"
    if status_code == 429:
        return "请求过于频繁，请稍后再试。"
    if status_code in (408, 504) or "timeout" in error_type:
        return "模型服务响应超时，请稍后重试。"
    if "connection" in error_type or "connect" in error_text:
        return "无法连接模型服务，请检查网络后重试。"
    if isinstance(status_code, int) and status_code >= 500:
        return "模型服务暂时不可用，请稍后重试。"
    return "模型请求失败，请稍后重试。"


def _log_llm_error(error: Exception) -> None:
    """Log safe API error details for local debugging without exposing credentials."""
    message = _redact_sensitive_text(str(error))
    logger.error(
        "LLM API request failed | type=%s | status_code=%s | error_code=%s | message=%s",
        type(error).__name__,
        getattr(error, "status_code", None),
        getattr(error, "code", None),
        message,
    )


def _redact_sensitive_text(value: str) -> str:
    """Remove API keys and Authorization values before writing a log message."""
    value = re.sub(r"sk-[A-Za-z0-9._-]+", "[REDACTED]", value)
    value = re.sub(
        r"(?i)(openai_|dashscope_)?api[_-]?key\s*[=:]\s*\S+",
        "api_key=[REDACTED]",
        value,
    )
    return re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", value)


def _parse_analysis(response_text: str) -> dict[str, object]:
    """Keep the existing parser name for the legacy six-field response."""
    return _parse_structured_result(response_text, ANALYSIS_FIELDS)


def _parse_structured_result(
    response_text: str,
    expected_fields: tuple[str, ...],
    list_fields: tuple[str, ...] = (),
    require_all_fields: bool = False,
) -> dict[str, object]:
    """Check that the model returned a JSON object for the selected task."""
    cleaned_text = _clean_json_response(response_text)
    try:
        data = json.loads(cleaned_text)
    except json.JSONDecodeError as error:
        logger.warning("LLM structured JSON parsing failed | type=%s", type(error).__name__)
        raise LLMRequestError("模型返回结果格式异常，请重新分析。") from error

    if not isinstance(data, dict):
        logger.warning("LLM structured result was not a JSON object")
        raise LLMRequestError("模型返回结果格式异常，请重新分析。")

    missing_fields = [field for field in expected_fields if field not in data]
    if require_all_fields and missing_fields:
        raise LLMRequestError(
            "模型返回结果不完整，请重新分析。"
        )

    result: dict[str, object] = {}
    for field in expected_fields:
        value = data.get(field, [] if field in list_fields else "论文未说明")
        if field in list_fields:
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise LLMRequestError(
                    "模型返回结果格式异常，请重新分析。"
                )
            result[field] = value
        else:
            if not isinstance(value, str):
                raise LLMRequestError(
                    "模型返回结果格式异常，请重新分析。"
                )
            result[field] = value
    return result


def _clean_json_response(response_text: str) -> str:
    """Remove an optional Markdown JSON code fence before parsing the response."""
    cleaned_text = response_text.strip()
    code_block = re.fullmatch(
        r"```(?:json)?\s*\n?(.*?)\n?```", cleaned_text, flags=re.IGNORECASE | re.DOTALL
    )
    return code_block.group(1).strip() if code_block else cleaned_text
