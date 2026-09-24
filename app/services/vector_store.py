"""Small persistent FAISS store for the local research knowledge base."""

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from app.services.database import WORK_DIRECTORY


VECTOR_INDEX_DIRECTORY = WORK_DIRECTORY / "vector_index"
INDEX_PATH = VECTOR_INDEX_DIRECTORY / "index.faiss"
MAPPING_PATH = VECTOR_INDEX_DIRECTORY / "mapping.json"


class VectorStore:
    """Persist a normalized IndexFlatIP and its FAISS-position mapping."""

    def build_index(self, entries: list[tuple[str, list[float]]]) -> None:
        """Rebuild the complete small-library index from database embeddings."""
        VECTOR_INDEX_DIRECTORY.mkdir(parents=True, exist_ok=True)
        if not entries:
            self._clear_files()
            return

        chunk_ids, embeddings = zip(*entries, strict=True)
        matrix = np.asarray(embeddings, dtype="float32")
        if matrix.ndim != 2 or matrix.shape[1] == 0:
            raise ValueError("向量索引输入格式不正确。")
        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(np.ascontiguousarray(matrix))
        faiss.write_index(index, str(INDEX_PATH))
        MAPPING_PATH.write_text(
            json.dumps({"chunk_ids": list(chunk_ids), "dimension": int(matrix.shape[1])}, ensure_ascii=False),
            encoding="utf-8",
        )

    def search_vectors(self, query_embedding: list[float], top_k: int) -> list[tuple[str, float]]:
        """Return chunk IDs and cosine similarity scores for the query vector."""
        if top_k <= 0 or not INDEX_PATH.exists() or not MAPPING_PATH.exists():
            return []
        index, mapping = self._load_index()
        if index.ntotal == 0:
            return []
        query = np.asarray([query_embedding], dtype="float32")
        if query.ndim != 2 or query.shape[1] != index.d:
            raise ValueError("查询向量维度与本地索引不一致。")
        faiss.normalize_L2(query)
        scores, positions = index.search(np.ascontiguousarray(query), min(top_k, index.ntotal))
        chunk_ids = mapping.get("chunk_ids", [])
        results: list[tuple[str, float]] = []
        for position, score in zip(positions[0], scores[0], strict=True):
            if position < 0 or position >= len(chunk_ids):
                continue
            results.append((str(chunk_ids[position]), float(score)))
        return results

    def remove_and_rebuild(self, entries: list[tuple[str, list[float]]]) -> None:
        """Keep deletion simple: rebuild every vector instead of deleting one ID."""
        self.build_index(entries)

    def _load_index(self) -> tuple[Any, dict[str, object]]:
        try:
            mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("本地向量索引映射文件异常，请重新构建索引。") from error
        index = faiss.read_index(str(INDEX_PATH))
        if not isinstance(mapping.get("chunk_ids"), list):
            raise ValueError("本地向量索引映射文件异常，请重新构建索引。")
        return index, mapping

    @staticmethod
    def _clear_files() -> None:
        for path in (INDEX_PATH, MAPPING_PATH):
            if path.exists():
                path.unlink()
