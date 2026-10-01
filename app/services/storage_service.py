"""Small storage abstraction for generated runtime artifacts only."""
from __future__ import annotations

from pathlib import Path

from app.services.config_service import ConfigService


class StorageProvider:
    """LOCAL is implemented; S3_COMPATIBLE remains explicitly configuration-only."""

    def __init__(self, config: ConfigService | None = None):
        self.config = (config or ConfigService()).load()
        self.root = Path(self.config.storage_root).resolve()

    def health(self) -> dict[str, str]:
        if self.config.storage_provider == "S3_COMPATIBLE":
            return {"status": "WARNING", "detail": "S3_COMPATIBLE requires an external provider adapter."}
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return {"status": "PASS", "detail": "Local runtime storage is writable."}
        except OSError:
            return {"status": "FAILED", "detail": "Local runtime storage is unavailable."}

    def store_generated(self, filename: str, content: bytes) -> str:
        if self.config.storage_provider != "LOCAL":
            raise RuntimeError("Configured storage provider is not available in this runtime.")
        safe_name = Path(filename).name
        if not safe_name:
            raise ValueError("A safe artifact filename is required.")
        self.root.mkdir(parents=True, exist_ok=True)
        path = (self.root / safe_name).resolve()
        if self.root not in path.parents:
            raise ValueError("Artifact path is outside configured storage.")
        path.write_bytes(content)
        return str(path)
