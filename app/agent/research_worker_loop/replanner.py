"""Safe plan adjustments when observer/critic identify missing evidence."""


class ResearchWorkerReplanner:
    def adjust(self, plan: list[dict[str, object]], critic: dict[str, object], observation: dict[str, object]) -> list[dict[str, object]]:
        if not critic.get("needs_replan"):
            return []
        if observation.get("needs_adjustment"):
            return [{"action": "生成数据质量报告", "tool": "data_tool", "reason": "数据结构未满足分析前提，先确认字段、缺失项和采集条件。"}]
        return [{"action": "补充并索引科研资料", "tool": "file_tool / knowledge_tool", "reason": "当前没有可追溯资料依据，不能生成科研结论。"}]
