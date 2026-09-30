"""Conservative, rule-based conflict screening for retrieved Evidence.

This module does not verify scientific facts and does not call an LLM.  It
only highlights *potential* disagreement in the small set of sources returned
for one request, so a researcher can decide whether deeper review is needed.
"""

from __future__ import annotations

import re
from itertools import combinations

from app.services.evidence_claim_service import extract_evidence_claims


_POSITIVE_PATTERNS = (
    r"显著提高", r"明显提高", r"显著改善", r"明显改善", r"显著提升",
    r"明显提升", r"有效提升", r"增强", r"优于",
)
_NEGATIVE_PATTERNS = (
    r"未显著提高", r"未明显提高", r"未观察到.*?(?:提高|提升|改善)",
    r"无明显(?:提高|提升|改善)", r"效果有限", r"提升有限", r"改善有限",
    r"无显著(?:差异|效果)", r"不明显", r"未见.*?(?:提高|提升|改善)",
)
_ENGLISH_POSITIVE_PATTERNS = (
    r"\bimproves?\b", r"\bincreases?\b", r"\benhances?\b", r"\boutperforms?\b",
    r"\bachieves? better\b", r"\bbeneficial\b", r"\beffective\b",
)
_ENGLISH_NEGATIVE_PATTERNS = (
    r"\bdoes not (?:improve|increase|enhance|outperform|reduce)\b",
    r"\bdo not (?:improve|increase|enhance|outperform|reduce)\b",
    r"\bfails? to (?:improve|increase|enhance|outperform|reduce)\b",
    r"\bno significant (?:improvement|increase|effect|difference)\b",
    r"\bnot significant(?:ly)?\b", r"\bdecreases?\b", r"\breduces?\b",
    r"\bdegrades?\b", r"\bworsens?\b", r"\binferior\b", r"\bineffective\b",
)
_CONDITION_PATTERNS = (
    r"低温", r"高温", r"常温", r"室温", r"冻融", r"湿热", r"干湿循环",
    r"\d+(?:\.\d+)?\s*(?:℃|°C)", r"(?:水胶比|掺量|龄期|应力|湿度|样本|试件)[^，。；;]{0,18}",
)
_ENGLISH_CONDITION_PATTERNS = (
    r"\b(?:under|at|during)\s+[^.，。;]{2,80}",
    r"\bon\s+(?:the\s+)?(?:[A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,2})",
    r"\b(?:dataset|benchmark|model|sample|temperature|time|condition)\s*[:=]?\s*[^.，。;]{1,50}",
)
_ENGLISH_CLAIM = re.compile(
    r"\b(?P<subject>(?:method|model|approach|system)\s+[A-Za-z0-9_-]+|[A-Z][A-Za-z0-9_-]*)\s+"
    r"(?P<verb>does not (?:improve|increase|enhance|outperform|reduce)|"
    r"fails? to (?:improve|increase|enhance|outperform|reduce)|"
    r"(?:improves?|increases?|enhances?|outperforms?|decreases?|reduces?|degrades?|worsens?))\s+"
    r"(?P<property>[A-Za-z][A-Za-z0-9 _-]{1,80})",
    re.IGNORECASE,
)
_CHINESE_CLAIM = re.compile(
    r"(?P<subject>(?:方法|模型|系统|方案)\s*[A-Za-z0-9甲乙丙丁]+)(?:在[^，。；;]{0,24}?)?\s*"
    r"(?P<verb>未观察到[^，。；;]{0,16}(?:提高|提升|改善)|未显著提高|无明显(?:提高|提升|改善)|"
    r"显著提高|明显提高|显著改善|明显改善|显著提升|明显提升|有效提升|增强|优于)\s*"
    r"(?P<property>[\u4e00-\u9fffA-Za-z0-9]{2,30})"
)
_STOP_WORDS = {
    "研究", "方法", "结果", "实验", "材料", "性能", "证明", "表明", "通过",
    "可以", "进行", "对于", "以及", "不同", "条件", "影响", "分析", "相关",
}


def detect_evidence_conflicts(sources: list[dict[str, object]]) -> dict[str, object]:
    """Screen retrieved sources for obvious, reviewable conclusion differences.

    ``no_conflict`` means the deterministic initial rules found no obvious
    conflict.  It never proves that the underlying research is consistent.
    """
    valid_sources = [source for source in sources if _is_traceable(source)]
    base = {
        "detection_method": "rule_based_initial_detection",
        "evidence_count": len(valid_sources),
        "conflicts": [],
    }
    if len(valid_sources) < 2:
        return {
            **base,
            "status": "insufficient_evidence",
            "reason": "可追溯 Evidence 少于两条，无法比较资料之间是否存在结论差异。",
            "context_difference": "",
            "requires_human_review": True,
        }

    potential_conflicts: list[dict[str, object]] = []
    context_differences: list[dict[str, object]] = []
    source_claims = [
        (source, claim)
        for source in valid_sources
        for claim in (_claims_or_legacy(source))
    ]
    for (left, left_claim), (right, right_claim) in combinations(source_claims, 2):
        # A source cannot serve as both sides of a scientific comparison.
        # Keeping the existing same-paper/section guard also avoids treating
        # neighbouring claims from one local context as independent studies.
        left_evidence_id = left_claim.get("evidence_id")
        if (
            (left_evidence_id and left_evidence_id == right_claim.get("evidence_id"))
            or _same_source_section(left, right)
        ):
            continue
        left_direction = str(left_claim["claim_direction"])
        right_direction = str(right_claim["claim_direction"])
        if (
            left_direction == "unknown"
            or right_direction == "unknown"
            or left_direction == right_direction
            or not _same_subject_and_property(left_claim, right_claim)
        ):
            continue

        # Conditions and explicit study scope both qualify a comparison.  They
        # are kept separate in normalized claims, then combined only for the
        # narrow context-difference decision.
        left_context = set(left_claim["condition"]) | set(left_claim["scope"])
        right_context = set(right_claim["condition"]) | set(right_claim["scope"])
        item = {
            "evidence_refs": [_reference(left), _reference(right)],
            "topic": str(left_claim["property"]),
            "position_a": _position_summary(left, left_direction),
            "position_b": _position_summary(right, right_direction),
            "context_difference": _context_difference(left_context, right_context),
            "normalized_claims": [left_claim, right_claim],
            "reason": "不同来源对相近主题呈现相反的明确结论方向。",
            "requires_human_review": True,
        }
        if _contexts_are_different(left_context, right_context):
            item["reason"] = "结论方向不同，但可识别的研究条件也不同，不能直接横向比较。"
            context_differences.append(item)
        else:
            potential_conflicts.append(item)

    if potential_conflicts:
        return {
            **base,
            "status": "potential_conflict",
            "conflicts": potential_conflicts,
            "reason": "当前检索资料存在潜在结论差异，不能将其综合为确定科研结论。",
            "context_difference": "部分资料的研究条件可能仍未完整披露。",
            "requires_human_review": True,
        }
    if context_differences:
        return {
            **base,
            "status": "context_difference",
            "conflicts": context_differences,
            "reason": "检测到不同研究条件下的结论差异；这些结果可能同时成立，不能直接视为冲突。",
            "context_difference": "建议核验实验条件、研究对象与样本定义。",
            "requires_human_review": True,
        }
    return {
        **base,
        "status": "no_conflict",
        "reason": "当前规则未在本次检索资料中发现明显的可比较结论冲突；这不代表所有研究结论已经一致。",
        "context_difference": "",
        "requires_human_review": False,
    }


def conflict_prompt_instruction(report: dict[str, object]) -> str:
    """Return a user-safe synthesis constraint from a conflict report."""
    status = str(report.get("status", "insufficient_evidence"))
    if status == "potential_conflict":
        return (
            "检测到不同来源对相近主题存在潜在结论差异。不得输出确定性的统一结论；"
            "请明确说明资料存在差异，引用相关[证据编号]，并建议核验研究对象、实验条件和样本定义。"
        )
    if status == "context_difference":
        return (
            "检测到资料可能对应不同研究条件。不得直接横向比较或归纳为统一结论；"
            "请说明条件差异可能影响结果，并建议核验实验条件、研究对象和样本定义。"
        )
    if status == "insufficient_evidence":
        return "可比较 Evidence 不足；不得把输出表述为已验证的科研结论，应明确说明资料不足。"
    return "当前规则未发现明显冲突，但这不证明资料结论一致；仍须保留证据引用与人工复核说明。"


def _is_traceable(source: dict[str, object]) -> bool:
    return bool(
        str(source.get("paper_id", "")).strip()
        and str(source.get("section", "")).strip()
        and str(source.get("content", "")).strip()
    )


def _same_source_section(left: dict[str, object], right: dict[str, object]) -> bool:
    return (
        str(left.get("paper_id", "")) == str(right.get("paper_id", ""))
        and str(left.get("section", "")) == str(right.get("section", ""))
    )


def normalize_evidence(source: dict[str, object]) -> dict[str, object]:
    """Extract a conservative, language-neutral comparison record.

    This is deterministic text parsing, not a claim verifier.  Missing fields
    deliberately remain ``unknown``/empty so unrelated evidence cannot become
    a conflict merely because both chunks contain evaluative words.
    """
    claims = extract_evidence_claims(source)
    if claims:
        return claims[0]
    text = " ".join(str(source.get("content", "")).split())
    match = _ENGLISH_CLAIM.search(text) or _CHINESE_CLAIM.search(text)
    subject = _normalize_term(match.group("subject")) if match else ""
    property_name = _normalize_property(match.group("property")) if match else ""
    if not match:
        # Chinese scientific prose commonly inserts a condition between the
        # subject and predicate ("方法 X 在低温条件下...").  Keep this
        # intentionally small fallback rather than guessing a claim from
        # unrelated words elsewhere in the chunk.
        chinese_subject = re.search(r"(?:方法|模型|系统|方案)\s*[A-Za-z0-9甲乙丙丁]+", text)
        chinese_verb = re.search(
            r"未观察到[^，。；;]{0,16}(?:提高|提升|改善)|未显著提高|无明显(?:提高|提升|改善)|"
            r"显著提高|明显提高|显著改善|明显改善|显著提升|明显提升|有效提升|增强|优于",
            text,
        )
        if chinese_subject and chinese_verb:
            subject = _normalize_term(chinese_subject.group(0))
            property_match = re.match(r"\s*([\u4e00-\u9fffA-Za-z0-9]{2,30})", text[chinese_verb.end():])
            property_name = _normalize_property(property_match.group(1)) if property_match else ""
    return {
        "evidence_ref": _reference(source)["evidence_id"],
        "subject": subject or "unknown",
        "property": property_name or "unknown",
        "claim_direction": _direction_from_text(text),
        "condition": sorted(_conditions(source)),
        "scope": sorted(_scope(source)),
    }


def _claims_or_legacy(source: dict[str, object]) -> list[dict[str, object]]:
    """Use sentence claims when explicit; retain legacy Chinese support."""
    claims = extract_evidence_claims(source)
    return claims or [normalize_evidence(source)]


def _same_subject_and_property(left: dict[str, object], right: dict[str, object]) -> bool:
    return (
        str(left.get("subject", "unknown")) != "unknown"
        and str(left.get("property", "unknown")) != "unknown"
        and left.get("subject") == right.get("subject")
        and left.get("property") == right.get("property")
    )


def _normalize_term(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower()).removeprefix("the ")


def _normalize_property(value: str) -> str:
    cleaned = re.split(r"\b(?:on|under|at|during|with|in)\b|[，。.;]", value, maxsplit=1, flags=re.IGNORECASE)[0]
    return _normalize_term(cleaned)


def _direction(source: dict[str, object]) -> str:
    return _direction_from_text(str(source.get("content", "")))


def _direction_from_text(text: str) -> str:
    patterns = (*_NEGATIVE_PATTERNS, *_ENGLISH_NEGATIVE_PATTERNS)
    negative = any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    # Remove matched negated phrases before looking for a positive direction:
    # "does not improve" and "未显著提高" must never be reclassified as
    # positive simply because they contain "improve" / "提高".
    remaining = text
    for pattern in patterns:
        remaining = re.sub(pattern, "", remaining, flags=re.IGNORECASE)
    positive = any(
        re.search(pattern, remaining, re.IGNORECASE)
        for pattern in (*_POSITIVE_PATTERNS, *_ENGLISH_POSITIVE_PATTERNS)
    )
    if positive and not negative:
        return "positive"
    if negative and not positive:
        return "negative"
    return "unknown"


def _conditions(source: dict[str, object]) -> set[str]:
    text = str(source.get("content", ""))
    values: set[str] = set()
    for pattern in (*_CONDITION_PATTERNS, *_ENGLISH_CONDITION_PATTERNS):
        values.update(match.strip().lower() for match in re.findall(pattern, text, re.IGNORECASE))
    return values


def _scope(source: dict[str, object]) -> set[str]:
    """Keep explicit dataset/benchmark-like scope markers for explanation."""
    text = str(source.get("content", ""))
    values: set[str] = set()
    for match in re.findall(
        r"\b(?:on|using)\s+(?:the\s+)?([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,2})",
        text,
    ):
        values.add(match.lower())
    return values


def _contexts_are_different(left: set[str], right: set[str]) -> bool:
    temperatures = {"低温", "高温", "常温", "室温"}
    left_temp, right_temp = left & temperatures, right & temperatures
    if left_temp and right_temp and left_temp != right_temp:
        return True
    return bool(left and right and left.isdisjoint(right))


def _context_difference(left: set[str], right: set[str]) -> str:
    if not left and not right:
        return "未从片段中识别到足够的条件信息。"
    return f"Evidence A 条件：{'、'.join(sorted(left)) or '未识别'}；Evidence B 条件：{'、'.join(sorted(right)) or '未识别'}。"


def _topic_tokens(source: dict[str, object]) -> set[str]:
    text = str(source.get("content", ""))
    tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{0,30}|[\u4e00-\u9fff]{2,8}", text))
    return {token.lower() for token in tokens if token not in _STOP_WORDS}


def _topics_overlap(left: dict[str, object], right: dict[str, object]) -> bool:
    common = _topic_tokens(left) & _topic_tokens(right)
    return bool(common)


def _topic_label(left: dict[str, object], right: dict[str, object]) -> str:
    common = sorted(_topic_tokens(left) & _topic_tokens(right), key=lambda value: (-len(value), value))
    return common[0] if common else "相近研究主题"


def _position_summary(source: dict[str, object], direction: str) -> str:
    label = "支持/提升" if direction == "positive" else "未支持/效果有限"
    text = " ".join(str(source.get("content", "")).split())
    return f"{label}：{text[:180]}"


def _reference(source: dict[str, object]) -> dict[str, object]:
    chunk_id = str(source.get("chunk_id", "")).strip()
    paper_id = str(source.get("paper_id", "")).strip()
    return {
        "evidence_id": f"{paper_id}:{chunk_id}" if chunk_id else paper_id,
        "paper_id": paper_id,
        "chunk_id": chunk_id,
        "source": str(source.get("filename") or source.get("paper_title") or "未命名资料"),
        "section": str(source.get("section") or "正文"),
        "score": round(float(source.get("score", 0.0)), 4),
    }
