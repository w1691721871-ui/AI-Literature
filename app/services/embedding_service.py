"""DashScope Embedding client kept separate from Qwen generation calls."""

import logging
import os
from collections.abc import Iterable

from dotenv import load_dotenv
from openai import OpenAI


logger = logging.getLogger(__name__)
MAX_EMBEDDING_BATCH_SIZE = 10


class EmbeddingConfigurationError(Exception):
    """Raised when the DashScope key or embedding configuration is missing."""


class EmbeddingRequestError(Exception):
    """Raised when DashScope cannot return a valid vector response."""


def generate_embedding(text: str) -> list[float]:
    """Generate one text-embedding-v4 vector."""
    vectors = generate_embeddings([text])
    return vectors[0]


def generate_embeddings(texts: Iterable[str]) -> list[list[float]]:
    """Generate vectors in compatible-API batches of no more than ten texts."""
    items = [text.strip() for text in texts if isinstance(text, str) and text.strip()]
    if not items:
        raise ValueError("没有可用于向量化的文本内容。")

    client, model, dimensions = _create_embedding_client()
    vectors: list[list[float]] = []
    try:
        for start in range(0, len(items), MAX_EMBEDDING_BATCH_SIZE):
            batch = items[start:start + MAX_EMBEDDING_BATCH_SIZE]
            response = client.embeddings.create(
                model=model,
                input=batch,
                dimensions=dimensions,
                encoding_format="float",
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            if len(ordered) != len(batch):
                raise EmbeddingRequestError("向量服务返回数量异常，请稍后重试。")
            for item in ordered:
                vector = item.embedding
                if not isinstance(vector, list) or not vector:
                    raise EmbeddingRequestError("向量服务未返回有效向量，请稍后重试。")
                vectors.append([float(value) for value in vector])
    except EmbeddingRequestError:
        raise
    except Exception as error:
        logger.error(
            "Embedding API request failed | type=%s | status_code=%s | error_code=%s",
            type(error).__name__,
            getattr(error, "status_code", None),
            getattr(error, "code", None),
        )
        raise EmbeddingRequestError(_friendly_embedding_error(error)) from error
    return vectors


def _create_embedding_client() -> tuple[OpenAI, str, int]:
    load_dotenv()
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise EmbeddingConfigurationError("向量服务尚未配置，请联系管理员。")
    base_url = os.getenv(
        "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    try:
        dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
    except ValueError as error:
        raise EmbeddingConfigurationError("向量维度配置不正确。") from error
    if dimensions <= 0:
        raise EmbeddingConfigurationError("向量维度配置不正确。")
    return OpenAI(api_key=api_key, base_url=base_url), model, dimensions


def _friendly_embedding_error(error: Exception) -> str:
    status_code = getattr(error, "status_code", None)
    error_text = str(error).lower()
    if status_code in (401, 403):
        return "向量服务鉴权或模型权限异常，请检查百炼配置。"
    if status_code == 429:
        return "向量服务请求过于频繁，请稍后再试。"
    if "credit_balance_exhausted" in error_text or "quota" in error_text:
        return "向量服务额度不足，请在百炼控制台检查模型额度。"
    if isinstance(status_code, int) and status_code >= 500:
        return "向量服务暂时不可用，请稍后重试。"
    if "connection" in type(error).__name__.lower() or "connect" in error_text:
        return "无法连接向量服务，请检查网络后重试。"
    return "向量服务调用失败，请稍后重试。"
