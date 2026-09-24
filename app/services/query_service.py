"""Qwen-powered query rewrite with a safe fallback for RAG retrieval."""

import logging

from app.services.llm_service import complete_research_prompt


logger = logging.getLogger(__name__)


def rewrite_query(question: str) -> str:
    """Turn a short conversational question into a retrieval-oriented query."""
    normalized = question.strip()
    if not normalized:
        raise ValueError("请输入科研知识问题。")
    prompt = f"""将下面的科研问题改写为适合文献向量检索的一句中文查询。
保留原意，并补足可能需要检索的研究对象、方法、实验效果或比较维度。
只输出改写后的查询，不要解释，不要使用 Markdown。

原问题：{normalized}"""
    try:
        rewritten = complete_research_prompt(prompt).strip().replace("\n", " ")
        return rewritten[:300] or normalized
    except Exception as error:
        # Retrieval can still proceed with the user's original wording.
        logger.warning("Query rewrite fallback used | type=%s", type(error).__name__)
        return normalized
