"""Deterministic planner for safe Research Worker tasks."""


class ResearchWorkerPlanner:
    """Turn a goal and selected tools into a transparent execution plan."""

    def build(self, goal: str, selected_tools: list[dict[str, str]]) -> list[dict[str, object]]:
        action_map = {
            "file_tool": ("检查科研资料", "确认文件类型、结构与可用信息"),
            "data_tool": ("分析数据结构", "检查字段、缺失值与基础数据规模"),
            "knowledge_tool": ("寻找相关科研资料", "基于已有论文获取可引用证据"),
            "project_tool": ("形成待确认项目建议", "将已有资料整理为需人工复核的下一步"),
            "document_tool": ("生成分析报告", "输出过程摘要、证据来源与人工确认建议"),
        }
        steps = []
        for index, item in enumerate(selected_tools):
            task_name, expected_output = action_map[item["name"]]
            steps.append({
                "step": index + 1,
                "task_name": task_name,
                "required_tool": item["name"],
                "reason": item["reason"],
                "expected_output": expected_output,
                # Keep legacy fields for the existing Worker UI and API clients.
                "action": task_name,
                "tool": item["name"],
                "status": "pending",
            })
        return steps
