"""Small, declarative configurations for supported document-analysis scenarios."""

from dataclasses import dataclass

from app.services.llm_service import PAPER_ANALYSIS_FIELDS, PAPER_ANALYSIS_LIST_FIELDS


@dataclass(frozen=True)
class ScenarioTask:
    """One task that can be recognized within a document-analysis scenario."""

    agent_task: str
    display_name: str
    keywords: tuple[str, ...]
    instruction: str


@dataclass(frozen=True)
class ScenarioConfig:
    """Prompt and result-schema settings for one supported document scenario."""

    identifier: str
    name: str
    description: str
    document_type: str
    supported_tasks: tuple[ScenarioTask, ...]
    overall_task: ScenarioTask
    output_fields: tuple[str, ...]
    list_fields: tuple[str, ...]
    summary_fields: tuple[str, ...]
    prompt_context: str


TECHNICAL_DOCUMENT_CONFIG = ScenarioConfig(
    identifier="technical_document",
    name="企业技术文档分析",
    description="面向技术方案、架构说明和实施文档，提炼方案、模块、风险与建议。",
    document_type="企业技术文档",
    supported_tasks=(
        ScenarioTask(
            "technical_solution",
            "技术方案分析",
            ("技术方案", "架构", "方案设计", "技术路线"),
            "梳理文档中的技术方案、架构思路和关键技术选择。",
        ),
        ScenarioTask(
            "module_analysis",
            "核心模块分析",
            ("核心模块", "模块", "组件", "系统组成"),
            "识别核心模块、职责边界以及模块间的主要依赖关系。",
        ),
        ScenarioTask(
            "risk_analysis",
            "风险点分析",
            ("风险点", "风险", "隐患", "挑战"),
            "提炼文档明确说明的技术、实施或依赖风险；不要把缺少证据的推测写成事实。",
        ),
        ScenarioTask(
            "implementation_recommendation",
            "实施建议",
            ("实施建议", "实施", "落地", "建议", "下一步"),
            "基于文档内容给出可执行的实施建议，并说明建议对应的文档依据。",
        ),
    ),
    overall_task=ScenarioTask(
        "technical_document_analysis",
        "企业技术文档整体分析",
        (),
        "完整说明技术方案、核心模块、风险点和实施建议。",
    ),
    output_fields=(
        "title",
        "document_overview",
        "technical_solution",
        "core_modules",
        "risks",
        "implementation_recommendations",
        "keywords",
    ),
    list_fields=("core_modules", "risks", "implementation_recommendations", "keywords"),
    summary_fields=("title", "document_overview", "risks"),
    prompt_context=(
        "This is an enterprise technical document. Focus on the technical solution, "
        "core modules, risks, dependencies, and implementation recommendations."
    ),
)


PRODUCT_DOCUMENT_CONFIG = ScenarioConfig(
    identifier="product_document",
    name="产品资料分析",
    description="面向产品介绍、需求说明和解决方案资料，提炼定位、价值、功能与应用场景。",
    document_type="产品资料",
    supported_tasks=(
        ScenarioTask(
            "product_positioning",
            "产品定位分析",
            ("产品定位", "定位", "目标用户", "目标客户"),
            "说明产品面向的用户或客户、问题定位和差异化方向。",
        ),
        ScenarioTask(
            "user_value",
            "用户价值分析",
            ("用户价值", "用户需求", "客户价值", "痛点", "价值"),
            "提炼产品为用户或客户解决的问题和可带来的价值。",
        ),
        ScenarioTask(
            "feature_analysis",
            "功能特点分析",
            ("功能特点", "功能", "特性", "能力"),
            "梳理产品的主要功能特点，并避免补充文档中不存在的能力。",
        ),
        ScenarioTask(
            "application_scenarios",
            "应用场景分析",
            ("应用场景", "使用场景", "场景", "适用"),
            "说明产品适用的业务或使用场景，以及文档中提到的前提条件。",
        ),
    ),
    overall_task=ScenarioTask(
        "product_document_analysis",
        "产品资料整体分析",
        (),
        "完整说明产品定位、用户价值、功能特点和应用场景。",
    ),
    output_fields=(
        "title",
        "product_positioning",
        "user_value",
        "feature_highlights",
        "application_scenarios",
        "limitations",
        "keywords",
    ),
    list_fields=("feature_highlights", "application_scenarios", "limitations", "keywords"),
    summary_fields=("title", "product_positioning", "feature_highlights"),
    prompt_context=(
        "This is product material. Focus on product positioning, user value, feature "
        "highlights, application scenarios, and stated limitations."
    ),
)


PAPER_CONFIG = ScenarioConfig(
    identifier="paper",
    name="科研论文分析",
    description="面向科研论文，提炼研究主题、方法、发现、创新点与局限性。",
    document_type="科研论文",
    supported_tasks=(
        ScenarioTask("summary", "论文摘要", (), ""),
        ScenarioTask("experiment", "研究方法分析", (), ""),
        ScenarioTask("innovation", "创新点分析", (), ""),
        ScenarioTask("conclusion", "主要结论分析", (), ""),
        ScenarioTask("limitation", "局限性分析", (), ""),
        ScenarioTask("qa", "论文问答", (), ""),
    ),
    overall_task=ScenarioTask("overall_analysis", "论文整体分析", (), ""),
    output_fields=PAPER_ANALYSIS_FIELDS,
    list_fields=PAPER_ANALYSIS_LIST_FIELDS,
    summary_fields=("title", "research_topic", "key_findings"),
    prompt_context="This is a research paper. Keep the existing paper-analysis focus.",
)


SCENARIO_CONFIGS = {
    PAPER_CONFIG.identifier: PAPER_CONFIG,
    TECHNICAL_DOCUMENT_CONFIG.identifier: TECHNICAL_DOCUMENT_CONFIG,
    PRODUCT_DOCUMENT_CONFIG.identifier: PRODUCT_DOCUMENT_CONFIG,
}


def get_scenario_config(scenario: str) -> ScenarioConfig:
    """Return a supported scenario configuration or raise a user-safe error."""
    normalized_scenario = scenario.strip().lower()
    config = SCENARIO_CONFIGS.get(normalized_scenario)
    if config is None:
        supported = "、".join(SCENARIO_CONFIGS)
        raise ValueError(f"不支持的分析场景，请使用：{supported}。")
    return config
