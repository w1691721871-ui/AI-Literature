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
MAX_RAG_CONTEXT_CHARS = 12_000
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
DECISION_REPORT_FIELDS = (
    "summary",
    "key_points",
    "risks",
    "recommendations",
    "business_value",
)
DECISION_REPORT_LIST_FIELDS = ("key_points", "risks", "recommendations")
BUSINESS_REPORT_FIELDS = (
    "decision_summary",
    "important_findings",
    "business_opportunities",
    "risks",
    "recommended_actions",
    "expected_value",
)
BUSINESS_REPORT_LIST_FIELDS = (
    "important_findings",
    "business_opportunities",
    "risks",
    "recommended_actions",
)
QUALITY_CHECK_SCENARIO_FIELDS = {
    "paper": (
        ("research_topic", "研究主题"),
        ("methodology", "研究方法"),
        ("innovation_points", "创新点"),
    ),
    "technical_document": (
        ("technical_solution", "技术方案"),
        ("core_modules", "核心模块"),
        ("implementation_recommendations", "实施建议"),
    ),
    "product_document": (
        ("product_positioning", "产品定位"),
        ("user_value", "用户价值"),
        ("application_scenarios", "应用场景"),
    ),
}


class LLMConfigurationError(Exception):
    """Raised when the API key has not been configured."""


class LLMRequestError(Exception):
    """Raised when the model provider cannot complete a request."""


def build_quality_check(
    scenario: str,
    analysis: dict[str, object],
    decision_report: dict[str, object],
) -> dict[str, object]:
    """Evaluate required result sections without making another model request."""
    checks = (
        ("summary", "决策摘要", decision_report.get("summary"), 20),
        ("key_points", "关键要点", decision_report.get("key_points"), 20),
        ("risks", "风险分析", decision_report.get("risks"), 15),
        ("recommendations", "行动建议", decision_report.get("recommendations"), 15),
        *(
            (field, label, analysis.get(field), 10)
            for field, label in QUALITY_CHECK_SCENARIO_FIELDS.get(scenario, ())
        ),
    )
    missing_information = [
        label for _, label, value, _ in checks if not _has_meaningful_value(value)
    ]
    score = sum(
        points for _, _, value, points in checks if _has_meaningful_value(value)
    )

    return {
        "completeness": not missing_information,
        "has_risk_analysis": _has_meaningful_value(decision_report.get("risks")),
        "has_recommendations": _has_meaningful_value(
            decision_report.get("recommendations")
        ),
        "missing_information": missing_information,
        "score": min(score, 100),
    }


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
    include_decision_report: bool = False,
    include_business_report: bool = False,
) -> dict[str, object]:
    """Run one task-specific prompt and return a structured analysis response."""
    field_names = "、".join(result_fields)
    field_type_note = ""
    if list_fields:
        list_field_names = "、".join(list_fields)
        field_type_note = (
            f"The fields {list_field_names} must be JSON arrays of strings; use [] when absent. "
            "All other fields must be strings."
        )
    if include_decision_report and include_business_report:
        output_instruction = f"""Return only a valid JSON object with exactly these top-level keys:
"analysis", "decision_report", and "business_report".
The "analysis" object must contain exactly these keys: {field_names}.
The "decision_report" object must contain exactly these keys: {"、".join(DECISION_REPORT_FIELDS)}.
The "business_report" object must contain exactly these keys: {"、".join(BUSINESS_REPORT_FIELDS)}.
The list fields in decision_report (key_points, risks, recommendations) and business_report (important_findings, business_opportunities, risks, recommended_actions) must be JSON arrays of strings. All remaining fields must be strings.
Use only information supported by the document. Do not make unsupported promises. If a detail is missing, use "文档未说明" for strings and [] for lists.
For business_report, describe decision support value for the selected user role, not generic text summarization.
Do not use Markdown code fences or any text outside the JSON object."""
    elif include_decision_report:
        output_instruction = f"""Return only a valid JSON object with exactly these top-level keys:
"analysis" and "decision_report".
The "analysis" object must contain exactly these keys: {field_names}.
The "decision_report" object must contain exactly these keys: {"、".join(DECISION_REPORT_FIELDS)}.
The decision_report fields key_points, risks, and recommendations must be JSON arrays of strings. Its summary and business_value must be strings.
Use only information supported by the document. Identify risks and recommendations carefully. Explain business_value as the decision support value derived from the document, not an unsupported promise.
If a string detail is missing, use "文档未说明"; use [] for a missing list.
Do not use Markdown code fences or any text outside the JSON object."""
    else:
        output_instruction = f"""Return only a valid JSON object with exactly these
keys: {field_names}.
{field_type_note}
Use only information supported by the paper. If a string detail is missing, use "论文未说明"."""

    prompt = f"""You are a document analysis assistant. The user task is:
{task}

Task-specific instructions:
{task_instruction}

Analyze the document text below.
{output_instruction}

Document text:
{paper_text[:MAX_MODEL_INPUT_CHARS]}
"""
    response_text = _request_model(prompt, json_mode=True)
    if include_decision_report and include_business_report:
        return _parse_analysis_with_reports(
            response_text,
            result_fields,
            list_fields=list_fields,
        )
    if include_decision_report:
        return _parse_analysis_with_decision_report(
            response_text,
            result_fields,
            list_fields=list_fields,
        )
    return _parse_structured_result(
        response_text,
        result_fields,
        list_fields=list_fields,
        require_all_fields=require_all_fields,
    )


def _parse_analysis_with_reports(
    response_text: str,
    analysis_fields: tuple[str, ...],
    list_fields: tuple[str, ...],
) -> dict[str, object]:
    """Parse the current nested response while accepting partial model output."""
    parsed = _parse_analysis_with_decision_report(
        response_text,
        analysis_fields,
        list_fields,
    )
    data = _decode_json_object(response_text)
    business_data = _as_json_object(data.get("business_report"))
    if business_data is None:
        business_data = {
            field: data[field] for field in BUSINESS_REPORT_FIELDS if field in data
        }
    parsed["business_report"] = _validate_structured_object(
        business_data,
        BUSINESS_REPORT_FIELDS,
        list_fields=BUSINESS_REPORT_LIST_FIELDS,
        require_all_fields=False,
        missing_string_value="文档未说明",
        coerce_types=True,
    )
    return parsed


def _parse_analysis_with_decision_report(
    response_text: str,
    analysis_fields: tuple[str, ...],
    list_fields: tuple[str, ...],
) -> dict[str, object]:
    """Validate a nested scenario analysis and the common decision report."""
    data = _decode_json_object(response_text)
    analysis_data = _as_json_object(data.get("analysis"))
    decision_report_data = _as_json_object(data.get("decision_report"))

    # Some compatible-model responses flatten the requested nested object. Keep
    # the existing scenario fields by accepting that form when they are present.
    if analysis_data is None:
        analysis_data = {
            field: data[field] for field in analysis_fields if field in data
        }
    if not analysis_data:
        raise LLMRequestError("模型返回结果不完整，请重新分析。")

    if decision_report_data is None:
        decision_report_data = {
            field: data[field] for field in DECISION_REPORT_FIELDS if field in data
        }

    return {
        "analysis": _validate_structured_object(
            analysis_data,
            analysis_fields,
            list_fields=list_fields,
            require_all_fields=False,
            missing_string_value="文档未说明",
            coerce_types=True,
        ),
        "decision_report": _validate_structured_object(
            decision_report_data,
            DECISION_REPORT_FIELDS,
            list_fields=DECISION_REPORT_LIST_FIELDS,
            require_all_fields=False,
            missing_string_value="文档未说明",
            coerce_types=True,
        ),
    }


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


def answer_question_with_retrieved_context(
    question: str,
    sources: list[dict[str, object]],
    task_instruction: str = "直接回答问题，清楚区分证据与推断。",
) -> str:
    """Answer a multi-paper question using only retriever-provided evidence."""
    context_parts: list[str] = []
    used_chars = 0
    for index, source in enumerate(sources, start=1):
        content = str(source.get("content", "")).strip()
        if not content:
            continue
        header = (
            f"[证据 {index}] 论文：{source.get('paper_title', '未命名论文')}\n"
            f"章节：{source.get('section', '正文')}\n"
        )
        remaining = MAX_RAG_CONTEXT_CHARS - used_chars - len(header)
        if remaining <= 0:
            break
        excerpt = content[:remaining]
        context_parts.append(f"{header}内容：{excerpt}")
        used_chars += len(header) + len(excerpt)

    if not context_parts:
        raise ValueError("没有可用于回答的论文证据。")
    prompt = f"""你是科研知识问答助手。请使用下方检索到的论文片段回答用户问题。
必须仅依据给出的证据回答；不要补充证据中没有的信息。若证据不足，请明确说明“现有论文片段不足以回答”。
请用中文作答，并在相关结论后以 [证据编号] 标注依据。

任务要求：{task_instruction}

用户问题：{question}

检索证据：
{chr(10).join(context_parts)}
"""
    return _request_model(prompt)


def complete_research_prompt(prompt: str, json_mode: bool = False) -> str:
    """Expose a small Qwen helper for independent RAG planning and reporting."""
    return _request_model(prompt, json_mode=json_mode)


def generate_research_report(
    report_type: str,
    sources: list[dict[str, object]],
) -> dict[str, object]:
    """Create a grounded structured research report from retrieved evidence."""
    report_fields = {
        "literature_review": (
            "研究背景", "核心问题", "技术路线", "方法比较", "创新点", "不足",
            "未来研究方向", "参考论文",
        ),
        "technology_roadmap": ("发展路线", "关键阶段", "技术演进", "当前挑战", "后续方向"),
        "research_gap": ("现有研究覆盖", "研究空白", "可能原因", "潜在方向", "验证建议"),
    }
    fields = report_fields.get(report_type)
    if fields is None:
        raise ValueError("不支持的研究报告类型。")
    evidence_text = "\n\n".join(
        f"[证据 {index}] 论文：{source.get('paper_title')}；章节：{source.get('section')}\n{str(source.get('content', ''))[:1800]}"
        for index, source in enumerate(sources, start=1)
    )[:MAX_RAG_CONTEXT_CHARS]
    prompt = f"""基于下列论文检索证据生成中文研究报告。
只能使用提供的证据；信息不足时填写“现有证据不足”。
返回且只返回 JSON 对象，字段必须是：{"、".join(fields)}。每个字段使用字符串或字符串数组。
在每项结论中保留 [证据编号] 标注。

证据：
{evidence_text}"""
    raw = _request_model(prompt, json_mode=True)
    data = _decode_json_object(raw)
    return {field: data.get(field, "现有证据不足") for field in fields}


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


def _request_model(prompt: str, json_mode: bool = False) -> str:
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
        request_options: dict[str, object] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            request_options["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(
            **request_options,
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
    data = _decode_json_object(response_text)

    return _validate_structured_object(
        data,
        expected_fields,
        list_fields=list_fields,
        require_all_fields=require_all_fields,
    )


def _validate_structured_object(
    data: dict[str, object],
    expected_fields: tuple[str, ...],
    list_fields: tuple[str, ...] = (),
    require_all_fields: bool = False,
    missing_string_value: str = "论文未说明",
    coerce_types: bool = False,
) -> dict[str, object]:
    """Validate one JSON object against a fixed string-and-list field schema."""
    missing_fields = [field for field in expected_fields if field not in data]
    if require_all_fields and missing_fields:
        raise LLMRequestError(
            "模型返回结果不完整，请重新分析。"
        )

    result: dict[str, object] = {}
    for field in expected_fields:
        value = data.get(field, [] if field in list_fields else missing_string_value)
        if field in list_fields:
            if coerce_types:
                value = _coerce_string_list(value)
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise LLMRequestError(
                    "模型返回结果格式异常，请重新分析。"
                )
            result[field] = value
        else:
            if coerce_types:
                value = _coerce_string_value(value, missing_string_value)
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


def _decode_json_object(response_text: str) -> dict[str, object]:
    """Decode JSON, including a valid JSON object surrounded by model prose."""
    cleaned_text = _clean_json_response(response_text)
    try:
        data = json.loads(cleaned_text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        data = None
        for match in re.finditer(r"\{", cleaned_text):
            try:
                candidate, _ = decoder.raw_decode(cleaned_text[match.start():])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                data = candidate
                break
        if data is None:
            logger.warning("LLM structured JSON parsing failed")
            raise LLMRequestError("模型返回结果格式异常，请重新分析。")

    if not isinstance(data, dict):
        logger.warning("LLM structured result was not a JSON object")
        raise LLMRequestError("模型返回结果格式异常，请重新分析。")
    return data


def _as_json_object(value: object) -> dict[str, object] | None:
    """Accept a nested object or a JSON string produced by a compatible model."""
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _coerce_string_list(value: object) -> list[str]:
    """Normalize a model's single string or null into a safe list of strings."""
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if not isinstance(value, str):
        return []
    lines = [line.strip(" -•\t") for line in value.splitlines()]
    return [line for line in lines if line] or ([value.strip()] if value.strip() else [])


def _coerce_string_value(value: object, missing_value: str) -> str:
    """Normalize simple compatible-model type drift for required string fields."""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "\n".join(value) or missing_value
    return missing_value


def _has_meaningful_value(value: object) -> bool:
    """Treat empty values and the model's explicit missing-value markers as absent."""
    missing_markers = {"", "文档未说明", "论文未说明"}
    if isinstance(value, str):
        return value.strip() not in missing_markers
    if isinstance(value, list):
        return any(_has_meaningful_value(item) for item in value)
    return False
