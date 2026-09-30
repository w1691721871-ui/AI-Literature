"""Deterministic, user-readable research strategy planning for ResearchOS.

This planner creates bounded research work plans; it does not expose hidden
reasoning or call a model.  Retrieval, Evidence validation, and conflict
screening remain responsibilities of the existing finite loop.
"""

from __future__ import annotations

from typing import Any


class ResearchStrategyPlanner:
    """Choose a bounded strategy from the explicit research goal and intent."""

    MAX_INITIAL_SUBTASKS = 3

    def plan(
        self,
        research_goal: str,
        task_understanding: dict[str, object] | None = None,
        existing_evidence: list[dict[str, object]] | None = None,
        research_gap: list[str] | None = None,
    ) -> dict[str, object]:
        """Return a structured plan containing only user-readable summaries."""
        goal = research_goal.strip()
        if not goal:
            raise ValueError("请输入需要规划的科研目标。")
        strategy_type = self._strategy_type(goal, task_understanding or {})
        gap = [str(item).strip() for item in (research_gap or []) if str(item).strip()]
        evidence_count = len(existing_evidence or [])
        templates = self._templates(strategy_type, goal)
        subtasks = [
            {
                "title": title,
                "research_question": question,
                "expected_evidence": expected,
                "purpose": purpose,
            }
            for title, question, expected, purpose in templates[: self.MAX_INITIAL_SUBTASKS]
        ]
        basis = [f"已识别任务类型：{strategy_type}。"]
        if evidence_count:
            basis.append(f"当前已关联 {evidence_count} 条 Evidence，将优先检查其覆盖范围与条件边界。")
        else:
            basis.append("当前尚未使用 Evidence；执行阶段将先检索可追溯资料。")
        if gap:
            basis.append(f"已识别资料缺口：{'；'.join(gap[:3])}。")
        return {
            "strategy_type": strategy_type,
            "research_objective": goal,
            "subtasks": subtasks,
            "reasoning_basis": basis,
            "expected_evidence": self._expected_evidence(strategy_type),
            "stop_condition": "获得足够可追溯 Evidence 后完成；Evidence 不足、无新增 Evidence、预算达到或需要人工复核时停止。",
        }

    def replan(
        self,
        research_goal: str,
        prior_question: str,
        research_gap: list[str],
        task_understanding: dict[str, object] | None = None,
    ) -> dict[str, str]:
        """Create one evidence-gap subtask that the finite loop can execute."""
        strategy_type = self._strategy_type(research_goal, task_understanding or {})
        gap = "；".join(item.strip() for item in research_gap if item.strip())[:240]
        focus = {
            "comparison": "研究对象、评价指标、实验条件与相反结果",
            "summary": "研究方法、主要结果与适用边界",
            "gap_analysis": "未解决问题、局限与待验证证据",
            "direction_discovery": "已有基础、研究机会与验证条件",
        }[strategy_type]
        return {
            "title": "补充证据检索",
            "research_question": (
                f"围绕“{research_goal}”，补充检索{focus}。"
                f"当前资料缺口：{gap or '需要可追溯的研究条件或结果证据'}。"
                f"此前任务：{prior_question[:80]}。"
            ),
            "expected_evidence": "可追溯的章节级资料，能够说明当前缺口或明确资料不足。",
            "purpose": "补足 Evidence 缺口，不重复执行原有宽泛检索。",
        }

    @staticmethod
    def _strategy_type(goal: str, understanding: dict[str, object]) -> str:
        intents = {str(item) for item in understanding.get("detected_intents", [])}
        lowered = goal.lower()
        if "comparison" in intents or any(word in goal for word in ("比较", "对比", "差异", "区别")) or "compare" in lowered:
            return "comparison"
        if "gap" in intents or any(word in goal for word in ("空白", "不足", "局限", "未解决")) or "gap" in lowered:
            return "gap_analysis"
        if "direction" in intents or any(word in goal for word in ("方向", "趋势", "机会", "未来")) or any(word in lowered for word in ("direction", "trend", "opportunity")):
            return "direction_discovery"
        return "summary"

    @staticmethod
    def _templates(strategy_type: str, goal: str) -> list[tuple[str, str, str, str]]:
        templates: dict[str, list[tuple[str, str, str, str]]] = {
            "comparison": [
                ("方法机制比较", f"围绕“{goal}”，提取不同资料中的研究对象、方法机制与适用范围。", "方法或研究对象的章节级描述。", "建立可比较的研究对象与方法范围。"),
                ("性能与条件比较", f"围绕“{goal}”，比较评价指标、实验条件、数据集或任务设置下的结果差异。", "结果指标、实验条件或任务设置。", "识别条件差异，避免直接横向裁决。"),
                ("局限与验证边界", f"围绕“{goal}”，检索资料中报告的局限、失败条件与需要人工验证的边界。", "局限、异常结果或验证条件。", "形成审慎的比较结论与后续核验建议。"),
            ],
            "gap_analysis": [
                ("现有研究基础", f"围绕“{goal}”，总结已上传资料已解决的问题与已有方法基础。", "研究背景、方法与已验证结果。", "明确已有资料能够支持的范围。"),
                ("未解决问题", f"围绕“{goal}”，检索局限、不足、失败条件与未被充分验证的问题。", "局限或不足的直接章节证据。", "避免将资料外推为研究空白。"),
                ("验证路径", f"围绕“{goal}”，提取资料支持的后续验证条件与需要补充的 Evidence。", "实验条件、数据范围或作者明确的未来工作。", "形成可人工确认的验证方向。"),
            ],
            "direction_discovery": [
                ("研究现状", f"围绕“{goal}”，梳理团队资料中已有研究对象、技术路线与成果基础。", "研究主题、技术路线和已上传资料。", "定位团队现有知识基础。"),
                ("机会与条件", f"围绕“{goal}”，检索资料中的局限、条件差异与尚待验证的机会。", "局限、条件或未解决问题。", "把方向建议限定为资料支持的机会。"),
                ("可验证下一步", f"围绕“{goal}”，提取能支持下一步实验、资料补充或人工评审的依据。", "可追溯的实验条件、结果或资料缺口。", "生成需人工确认的下一步建议。"),
            ],
            "summary": [
                ("研究主题与背景", f"围绕“{goal}”，提取资料中的研究对象、背景与核心问题。", "摘要、引言或研究问题章节。", "建立知识总结范围。"),
                ("方法与主要结果", f"围绕“{goal}”，提取资料中的方法、结果与可复核 Evidence。", "方法、实验或结果章节。", "形成有依据的知识总结。"),
                ("适用边界", f"围绕“{goal}”，检索资料中说明的限制、条件与需补充信息。", "局限、条件或作者明确边界。", "避免把总结表述为超出资料范围的结论。"),
            ],
        }
        return templates[strategy_type]

    @staticmethod
    def _expected_evidence(strategy_type: str) -> list[str]:
        common = ["paper_id + chunk_id", "来源文件与章节", "检索相关度"]
        if strategy_type == "comparison":
            return common + ["可比较的评价指标与研究条件"]
        if strategy_type == "gap_analysis":
            return common + ["资料中明确的局限或未验证条件"]
        if strategy_type == "direction_discovery":
            return common + ["已有研究基础与待验证方向"]
        return common + ["研究对象、方法、结果与适用边界"]
