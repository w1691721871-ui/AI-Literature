"""Evidence-bounded research deliverable drafts for a saved workspace."""

from __future__ import annotations

from typing import Any


class ResearchDeliverableService:
    """Generate structured drafts only from workspace evidence and decisions."""

    SUPPORTED = {"literature_review", "project_proposal", "experiment_plan", "research_brief"}

    def generate(self, snapshot: dict[str, object], decision: dict[str, object], deliverable_type: str) -> dict[str, object]:
        if deliverable_type not in self.SUPPORTED:
            raise ValueError("不支持的科研交付物类型。")
        evidence = list(snapshot.get("evidence_summary", []))
        boundary = "AI 辅助生成的研究交付草案，需由科研负责人审核；不构成科研事实或自动执行指令。"
        if not evidence:
            return {
                "type": deliverable_type, "status": "insufficient_evidence", "title": "资料不足报告",
                "sections": {"资料状态": "当前没有可验证资料，不能生成科研结论或方案。", "下一步": decision.get("next_action", "请先补充并索引科研资料。")},
                "evidence_refs": [], "boundary": boundary,
            }
        refs = [self._reference(item) for item in evidence]
        goal = str(snapshot.get("research_goal", ""))
        conflict = dict(snapshot.get("conflict_report", {}))
        common = {
            "Research Background": f"本草案围绕研究目标“{goal}”整理，具体事实应以列出的 Evidence 为准。",
            "Evidence Comparison": f"已关联 {len(refs)} 条可追溯 Evidence；冲突状态：{conflict.get('status', 'not_observed')}。",
            "Research Gap": "；".join(snapshot.get("unresolved_questions", [])) or "当前未记录额外资料缺口，仍需人工复核。",
        }
        if deliverable_type == "research_brief":
            sections = {
                "Research Objective": goal or "当前未记录研究目标。",
                "Current Evidence": common["Evidence Comparison"],
                "Key Findings": "当前仅汇总已引用 Evidence 支撑的待确认信息；不得视为确定科研结论。",
                "Conflict / Risk": self._conflict_note(conflict),
                "Recommended Validation": decision.get("next_action", "请由科研负责人制定验证安排。"),
                "Next Research Action": decision.get("next_action", "请补充或审核现有 Evidence。"),
            }
            title = "Executive Research Brief"
        elif deliverable_type == "literature_review":
            sections = {**common, "Existing Methods": "请根据引用资料中的方法章节进行人工比对。", "Conflict Analysis": self._conflict_note(conflict), "Future Validation Direction": decision.get("next_action", "请结合实验条件制定后续验证。")}
            title = "Literature Review Report 草案"
        elif deliverable_type == "project_proposal":
            sections = {"Research Problem": common["Research Background"], "Existing Evidence": common["Evidence Comparison"], "Innovation Opportunity": "仅作为待确认的研究机会，不能替代专家判断。", "Validation Plan": decision.get("next_action", "请先补充可验证资料。")}
            title = "Project Proposal Draft"
        else:
            sections = {"任务目标": goal, "使用资料": f"已引用 {len(refs)} 条 Evidence。", "实验/验证前检查": self._conflict_note(conflict), "建议下一步": decision.get("next_action", "由科研负责人制定具体验证计划。")}
            title = "Experiment Planning Draft"
        return {"type": deliverable_type, "status": "draft", "title": title, "sections": sections, "evidence_refs": refs, "decision": decision, "boundary": boundary}

    @staticmethod
    def _reference(item: dict[str, object]) -> dict[str, object]:
        return {key: item.get(key, "") for key in ("evidence_id", "paper_id", "source", "chapter", "agent", "score")}

    @staticmethod
    def _conflict_note(conflict: dict[str, object]) -> str:
        if conflict.get("requires_human_review"):
            return "当前 Evidence 存在条件差异或潜在冲突，必须先人工核对研究对象、评价指标与实验条件。"
        return "当前未观察到需要自动裁决的冲突；仍应由科研负责人核对资料适用条件。"
