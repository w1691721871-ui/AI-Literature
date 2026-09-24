"""Small, explainable task planner for the independent ResearchAgent."""


class ResearchPlanner:
    """Classify common research tasks and choose a grounded answer instruction."""

    def plan(self, question: str) -> dict[str, str]:
        normalized = question.strip()
        lowered = normalized.lower()
        if any(marker in normalized for marker in ("比较", "对比", "差异", "区别")):
            return {"task_type": "comparison", "instruction": "比较不同论文的方法、实验结果、优势与限制；若证据不足，不要强行比较。"}
        if any(marker in normalized for marker in ("趋势", "发展", "综述", "领域")):
            return {"task_type": "research_summary", "instruction": "总结检索论文反映的研究背景、技术路线、共性和发展趋势，并说明证据范围。"}
        if any(marker in normalized for marker in ("建议", "下一步", "未来", "研究什么", "方向")):
            return {"task_type": "research_suggestion", "instruction": "基于证据中的不足和局限提出审慎的后续研究建议，并区分事实与建议。"}
        return {"task_type": "knowledge_query", "instruction": "直接回答问题，优先说明方法、结果和适用条件。"}
