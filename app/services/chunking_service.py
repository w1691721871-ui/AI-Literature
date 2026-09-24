"""Simple section-aware text chunking for the local research knowledge base."""

import re


CHUNK_TOKEN_TARGET = 700
CHUNK_TOKEN_OVERLAP = 120
DEFAULT_SECTION_TITLE = "正文"

_SECTION_KEYWORDS = (
    ("摘要", "摘要"),
    ("abstract", "摘要"),
    ("引言", "引言"),
    ("introduction", "引言"),
    ("相关工作", "相关工作"),
    ("related work", "相关工作"),
    ("方法", "研究方法"),
    ("method", "研究方法"),
    ("实验", "实验"),
    ("experiment", "实验"),
    ("结果", "研究结果"),
    ("result", "研究结果"),
    ("结论", "结论"),
    ("conclusion", "结论"),
)


def chunk_text(text: str) -> list[dict[str, object]]:
    """Split extracted paper text by likely sections and approximate token length.

    PDF extraction does not provide a reliable tokenizer or document outline. This
    lightweight heuristic keeps the implementation dependency-free while aiming
    for roughly 500–800 token chunks with overlap.
    """
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []

    sections = _split_sections(normalized)
    chunks: list[dict[str, object]] = []
    for section_title, section_content in sections:
        for content in _chunk_section(section_content):
            chunks.append(
                {
                    "content": content,
                    "section_title": section_title,
                    "chunk_index": len(chunks),
                }
            )
    return chunks


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = DEFAULT_SECTION_TITLE
    current_lines: list[str] = []

    for line in text.splitlines():
        title = _detect_section_title(line)
        if title:
            if current_lines:
                sections.append((current_title, "\n".join(current_lines)))
            current_title = title
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines)))
    return sections or [(DEFAULT_SECTION_TITLE, text)]


def _detect_section_title(line: str) -> str | None:
    compact = re.sub(r"^\s*(?:\d+(?:\.\d+)*[.)、:：\s]*)?", "", line).strip()
    if not compact or len(compact) > 80:
        return None
    lowered = compact.lower()
    for keyword, title in _SECTION_KEYWORDS:
        if lowered == keyword or lowered.startswith(f"{keyword} ") or lowered.startswith(f"{keyword}:"):
            return title
    return None


def _chunk_section(text: str) -> list[str]:
    units = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s+|\n+", text) if part.strip()]
    if not units:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for unit in units:
        for piece in _split_oversized_unit(unit):
            piece_size = _estimated_tokens(piece)
            if current and current_size + piece_size > CHUNK_TOKEN_TARGET:
                chunks.append("\n".join(current).strip())
                overlap = _tail_for_overlap("\n".join(current))
                current = [overlap] if overlap else []
                current_size = _estimated_tokens(overlap)
            current.append(piece)
            current_size += piece_size
    if current:
        chunks.append("\n".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def _split_oversized_unit(unit: str) -> list[str]:
    if _estimated_tokens(unit) <= CHUNK_TOKEN_TARGET:
        return [unit]
    # Character windows are only a fallback for an unusually long PDF line.
    window = 1_400
    overlap = 240
    return [unit[start:start + window] for start in range(0, len(unit), window - overlap)]


def _tail_for_overlap(text: str) -> str:
    words = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_'-]+", text)
    if not words:
        return text[-480:]
    selected = words[-CHUNK_TOKEN_OVERLAP:]
    return " ".join(selected)


def _estimated_tokens(text: str) -> int:
    chinese_characters = len(re.findall(r"[\u4e00-\u9fff]", text))
    non_chinese_words = len(re.findall(r"[A-Za-z0-9_'-]+", text))
    punctuation = len(re.findall(r"[^\w\s]", text))
    return chinese_characters + non_chinese_words + max(1, punctuation // 4)
