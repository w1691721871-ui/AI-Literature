"""Deterministic planning for one complementary Evidence retrieval.

The planner never decides that an opposing claim exists.  It only turns an
explicit claim already found in retrieved material into a narrowly scoped
search request for limitations or condition-qualified results.  Any returned
material still passes the normal Evidence validation and conflict checks.
"""

from __future__ import annotations

import re


def plan_complementary_retrieval(
    claims: list[dict[str, object]],
    seen_queries: set[str] | None = None,
) -> dict[str, str] | None:
    """Return one non-duplicate, evidence-driven complementary query.

    Claims without an explicit subject, property, and direction are ignored.
    The result is a retrieval plan, not a scientific assertion.
    """
    known = {_normalise_query(item) for item in (seen_queries or set())}
    for claim in claims:
        subject = _clean(claim.get("subject"))
        property_name = _clean(claim.get("property"))
        direction = _clean(claim.get("direction") or claim.get("claim_direction"))
        if not subject or not property_name or direction not in {"positive", "negative"}:
            continue

        opposite = "does not improve" if direction == "positive" else "improves"
        # These are condition categories to search, not claimed conditions.
        # For reasoning claims, retain a small task/benchmark vocabulary so
        # the retrieval query can discover heterogeneous task settings rather
        # than repeating the original positive-result wording.
        scope = {str(item).lower() for item in claim.get("scope", []) if str(item).strip()}
        condition_terms = "different task conditions datasets benchmarks limitations"
        if "llm reasoning" in scope or subject.endswith("prompting"):
            # This is a controlled *retrieval vocabulary*, not a claim that
            # these settings occur in a paper.  Prompting evaluations commonly
            # vary by reasoning task; adding task-type terms lets the retriever
            # seek condition-qualified counter-evidence instead of merely
            # returning the original positive-result paper again.
            condition_terms = "spatial multi-hop"
        query = f"{subject} {opposite} {property_name} {condition_terms}"
        normalized = _normalise_query(query)
        if not normalized or normalized in known:
            continue
        return {
            "query": query,
            "reason": "search_opposite_claim",
            "source_claim": f"{subject} {direction} {property_name}",
        }
    return None


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normalise_query(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())
