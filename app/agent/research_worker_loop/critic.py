"""User-facing result sufficiency check, not model chain-of-thought."""


class ResearchWorkerCritic:
    def evaluate(self, goal: str, observation: dict[str, object]) -> dict[str, object]:
        issues: list[str] = []
        has_material = bool(observation.get("workspace_file_count", 0) or observation.get("rag_evidence_count", 0))
        has_evidence = bool(observation.get("rag_evidence_count", 0))
        if not has_material:
            issues.append("当前没有可验证资料，请上传科研文件。")
        elif not has_evidence:
            issues.append("当前没有可引用的知识库 Evidence，只能生成资料不足或数据质量说明。")
        if observation.get("needs_adjustment"):
            issues.append("数据字段或结构不足，不能据此生成实验趋势结论。")
        if not issues:
            return {"score": "资料覆盖可用于生成待复核执行摘要", "issues": [], "suggestion": "生成交付物并由负责人确认资料、证据与后续行动。", "needs_replan": False, "has_verifiable_material": True, "has_evidence": True}
        return {"score": "资料不足，不能形成科研结论", "issues": issues, "suggestion": "补充可读取科研资料或先生成数据质量报告后再执行。", "needs_replan": True, "has_verifiable_material": has_material, "has_evidence": has_evidence}
