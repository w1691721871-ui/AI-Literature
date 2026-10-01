"""Environment-backed runtime configuration with safe, redacted summaries."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


@dataclass(frozen=True)
class RuntimeConfig:
    model: str
    database_url: str
    storage_provider: str
    storage_root: str
    max_retries: int
    worker_poll_seconds: int
    require_human_review: bool


class ConfigService:
    """Single source of runtime settings; secret values are never returned."""

    def load(self) -> RuntimeConfig:
        return RuntimeConfig(
            model=os.getenv("LLM_MODEL", "qwen-plus"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///work/research_library.db"),
            storage_provider=os.getenv("STORAGE_PROVIDER", "LOCAL").upper(),
            storage_root=os.getenv("STORAGE_ROOT", "work/runtime_storage"),
            max_retries=_int_env("RUNTIME_MAX_RETRIES", 3),
            worker_poll_seconds=max(1, _int_env("WORKER_POLL_SECONDS", 5)),
            require_human_review=os.getenv("REQUIRE_HUMAN_REVIEW", "true").lower() != "false",
        )

    def summary(self) -> dict[str, object]:
        config = self.load()
        return {
            "MODEL_CONFIG": {"model": config.model, "api_key_configured": bool(os.getenv("DASHSCOPE_API_KEY"))},
            "DATABASE_CONFIG": {"engine": "sqlite" if config.database_url.startswith("sqlite") else "external", "configured": bool(config.database_url)},
            "STORAGE_CONFIG": {"provider": config.storage_provider, "root": config.storage_root},
            "SECURITY_CONFIG": {"require_human_review": config.require_human_review, "secrets_redacted": True},
            "RUNTIME_CONFIG": {key: value for key, value in asdict(config).items() if key != "database_url"},
        }
