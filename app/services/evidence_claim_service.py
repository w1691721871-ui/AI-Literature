"""Deterministic, sentence-level claim extraction for retrieved Evidence.

The service deliberately extracts only explicit, reviewable statements.  It
does not verify scientific truth and never calls an LLM.  A claim always keeps
its stable ``paper_id:chunk_id`` reference so a reviewer can return to the
original PDF chunk.
"""

from __future__ import annotations

import re


_NEGATIVE_VERBS = (
    r"does not improve",
    r"do not improve",
    r"fails? to improve",
    r"does not increase",
    r"do not increase",
    r"fails? to increase",
    r"decreases?",
    r"degrades?",
    r"worsens?",
    r"limited improvement",
)
_POSITIVE_VERBS = (
    r"improves?",
    r"increases?",
    r"enhances?",
    r"boosts?",
    r"achieves? better",
)
_SUBJECT = (
    r"(?i:chain[-\s]*of[-\s]*thought\s*(?:\(\s*CoT\s*\))?\s*prompting)"
    r"|(?i:CoT\s*prompting)"
    r"|(?i:(?:Method|Model|Approach|System)\s+[A-Za-z0-9_-]+)"
    r"|[A-Z][A-Z0-9_-]{1,}"
)
_CLAIM_PATTERN = re.compile(
    rf"(?P<subject>{_SUBJECT})\s+(?P<verb>(?i:{'|'.join(_NEGATIVE_VERBS + _POSITIVE_VERBS)}))\s+(?P<tail>[^.!?;]{{1,240}})",
)
_CONDITION_SPLIT = re.compile(r"\b(?:on|under|for|in|during|at)\b", re.IGNORECASE)


def extract_evidence_claims(source: dict[str, object]) -> list[dict[str, object]]:
    """Return explicit sentence claims from one real Evidence source.

    Unknown or implicit assertions are ignored instead of guessed.  This keeps
    the downstream conflict screen conservative and explainable.
    """
    evidence_id = _evidence_id(source)
    text = _normalise_text(str(source.get("content", "")))
    claims: list[dict[str, object]] = []
    for sentence in _sentences(text):
        for match in _CLAIM_PATTERN.finditer(sentence):
            subject = _normalise_subject(match.group("subject"))
            direction = _direction(match.group("verb"))
            property_name, condition = _property_and_condition(match.group("tail"))
            if not subject or not property_name or direction == "unknown":
                continue
            claims.append({
                "evidence_id": evidence_id,
                "subject": subject,
                "property": property_name,
                "direction": direction,
                # Keep the existing conflict-service field for compatibility
                # while exposing the public Claim schema's ``direction``.
                "claim_direction": direction,
                "condition": [condition] if condition else [],
                # A named benchmark/dataset is both a condition for the
                # comparison and a useful display-level scope marker.
                "scope": _scope(sentence) + ([condition] if condition else []),
                "confidence": "explicit_sentence_rule",
                "sentence": sentence[:500],
            })
    return claims


def _normalise_text(text: str) -> str:
    # PDF extraction may hyphenate one word at a line break (for example
    # ``prompt-\ning``).  Repair only that presentation artifact in the local
    # parsing copy; the stored Evidence text is never changed.
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    # PDFs may also split the CoT term across a line.  Normalise only this
    # known spelling variant; source text itself remains untouched in storage.
    text = re.sub(r"chain[-\s]*of[-\s]*thought", "chain of thought", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]


def _direction(verb: str) -> str:
    lowered = verb.lower()
    if any(re.fullmatch(pattern, lowered, re.IGNORECASE) for pattern in _NEGATIVE_VERBS):
        return "negative"
    if any(re.fullmatch(pattern, lowered, re.IGNORECASE) for pattern in _POSITIVE_VERBS):
        return "positive"
    return "unknown"


def _property_and_condition(tail: str) -> tuple[str, str]:
    pieces = _CONDITION_SPLIT.split(tail, maxsplit=1)
    property_text = re.sub(r"\b(?:the|overall|model|reasoning)\b", "", pieces[0], flags=re.IGNORECASE)
    property_text = " ".join(property_text.strip(" ,:-").split())
    # Performance is the comparison property in the real CoT corpus; treating
    # "reasoning/model performance" as separate properties would hide the
    # condition-qualified difference while retaining the condition itself.
    property_name = "performance" if "performance" in property_text.lower() else property_text.lower()
    condition = ""
    if len(pieces) == 2:
        condition = " ".join(pieces[1].strip(" ,:-").lower().split())
    return property_name, condition


def _normalise_subject(value: str) -> str:
    lowered = " ".join(value.replace("-", " ").split()).lower()
    if "chain of thought" in lowered or "cot" in lowered:
        return "cot prompting"
    return lowered


def _scope(sentence: str) -> list[str]:
    lowered = sentence.lower()
    scope: list[str] = []
    if any(token in lowered for token in ("language model", "llm", "gsm8k", "arithmetic", "commonsense", "symbolic")):
        scope.append("llm reasoning")
    if any(token in lowered for token in ("multimodal", "spatial", "lmm", "multi-hop")):
        scope.append("multimodal reasoning")
    return scope


def _evidence_id(source: dict[str, object]) -> str:
    paper_id = str(source.get("paper_id", "")).strip()
    chunk_id = str(source.get("chunk_id", "")).strip()
    return f"{paper_id}:{chunk_id}" if paper_id and chunk_id else paper_id
