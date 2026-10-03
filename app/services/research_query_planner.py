"""Explainable query expansion for read-only research discovery."""
from __future__ import annotations


class ResearchQueryPlanner:
    _TOPICS = {
        "low carbon": ["recycled materials", "carbon capture concrete", "life cycle assessment", "durability"],
        "低碳": ["再生材料", "碳捕集混凝土", "生命周期评价", "耐久性"],
        "rag": ["retrieval augmented generation", "graph rag", "benchmark", "evaluation"],
    }

    def plan(self, goal: str) -> dict[str, object]:
        text = str(goal or "").strip()
        lowered = text.lower()
        related = next((terms for keyword, terms in self._TOPICS.items() if keyword in lowered), [])
        core = self._topic(text)
        queries = [core, *[f"{core} {term}" for term in related]][:5]
        return {"topic": core, "related_directions": related, "queries": queries, "strategy": "Search a core research topic, then diversify by adjacent methods and evaluation criteria.", "boundary": "Queries are a retrieval plan only; they contain no research conclusion or hidden model reasoning."}

    @staticmethod
    def _topic(goal: str) -> str:
        cleaned = " ".join(goal.replace("analyze", "").replace("分析", "").replace("future direction", "").replace("未来方向", "").split())
        return cleaned[:180] or "research topic"
