"""Rule-based reflection for evidence sufficiency, not a hidden model thought trace."""


class ResearchResultEvaluator:
    """Describe outcome quality and the next user-visible decision."""

    def evaluate(self, sources: list[dict[str, object]], workspace_assets: list[dict[str, object]], master_completed: bool, goal: str = "", master_failed: bool = False) -> dict[str, object]:
        evidence_count = len(sources)
        has_evidence = evidence_count > 0
        valid_sources = [item for item in sources if all(key in item for key in ("paper_id", "section"))]
        source_integrity = evidence_count == len(valid_sources)
        needs_more_retrieval = not has_evidence or not source_integrity
        goal_coverage = master_completed and has_evidence
        if master_failed:
            next_decision = "已有资料依据，但模型服务未完成交付；请稍后重试，不要把未完成结果作为科研结论。"
            next_plan = [{"action": "重新执行专项分析", "reason": "模型服务未完成本次受控执行。"}]
        elif has_evidence and master_completed:
            next_decision = "已形成基于知识库证据的研究交付物，建议科研负责人复核后再创建 Action 或 Project。"
            next_plan = [{"action": "人工复核交付物", "reason": "AI 建议需要由科研负责人确认后才进入项目执行。"}]
        elif workspace_assets:
            next_decision = "工作区发现资料但知识库证据不足；请将需要引用的资料上传并完成索引。"
            next_plan = [{"action": "补充知识库资料", "reason": "当前工作区文件尚未成为可检索的章节级证据。"}]
        else:
            next_decision = "暂无可验证资料；请上传科研论文或在 Research Workspace 放入允许的资料文件。"
            next_plan = [{"action": "上传或索引科研资料", "reason": "没有资料依据时 Agent 不会输出科研结论。"}]
        return {
            "has_evidence": has_evidence,
            "evidence_count": evidence_count,
            "source_integrity": source_integrity,
            "goal_coverage": goal_coverage,
            "needs_more_retrieval": needs_more_retrieval,
            "workspace_asset_count": len(workspace_assets),
            "master_completed": master_completed,
            "next_decision": next_decision,
            "next_plan": next_plan,
            "boundary_note": "这是资料覆盖检查，不代表科研事实准确率，也不展示模型内部思维过程。",
        }
