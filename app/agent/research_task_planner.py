"""Goal-aware, deterministic planning for autonomous ResearchOS runs."""

from __future__ import annotations


class ResearchTaskPlanner:
    """Build a transparent plan that maps each task to an allow-listed tool."""

    def build_plan(self, goal: str, *, has_ready_papers: bool, workspace_assets: list[dict[str, object]]) -> dict[str, object]:
        normalized = goal.strip()
        lowered = normalized.lower()
        selected_agents = ["knowledge", "literature"] if has_ready_papers else []
        if any(word in normalized for word in ("趋势", "热点", "发展", "演进")):
            selected_agents.append("trend")
        if any(word in normalized for word in ("创新", "空白", "机会", "突破", "不足")):
            selected_agents.append("innovation")
        if any(word in normalized for word in ("企业", "项目", "合作", "专利", "成果", "路线")):
            selected_agents.append("project")
        if has_ready_papers:
            selected_agents.append("report")
        selected_agents = list(dict.fromkeys(selected_agents))

        tasks: list[dict[str, object]] = []
        if workspace_assets:
            tasks.append(self._task("discover_workspace", "发现科研工作区资料", "Research Brain", "workspace_file", "需要先感知可读取的科研文件和实验资料范围。"))
        data_assets = [item for item in workspace_assets if item.get("type") in {"CSV", "Excel"}]
        if data_assets and any(marker in normalized for marker in ("数据", "实验", "表格", "csv", "excel")):
            tasks.append(self._task("summarize_data", "汇总实验数据结构", "Research Brain", "data_analysis", "目标涉及实验或数据，需要先确认表格结构和可分析范围。"))
        if has_ready_papers:
            tasks.append(self._task("retrieve_knowledge", "检索团队知识库证据", "Knowledge Agent", "knowledge_retrieval", "需要基于已上传论文验证研究目标，而非只依赖模型生成。"))
            tasks.append(self._task("analyze_research", "执行专项科研分析", "Research Master", "research_agents", "已有证据可支撑专项 Agent 进行受限的科研分析。"))
            if "project" in selected_agents:
                tasks.append(self._task("prepare_project", "形成待确认项目方案", "Project Agent", "project_planning", "目标包含合作、成果或项目路径，需要生成供负责人确认的方案。"))
            tasks.append(self._task("generate_deliverable", "生成可复核研究交付物", "Report Agent", "document_generation", "已完成的证据与专项分析需要整理成可复核交付物。"))
        else:
            tasks.append(self._task("request_evidence", "识别资料缺口并等待知识依据", "Research Brain", "knowledge_retrieval", "没有已索引资料时必须先补充证据，不能直接形成科研结论。"))
        return {
            "goal": normalized,
            "selected_agents": selected_agents,
            "tasks": tasks,
            "planning_note": "计划根据目标关键词、已索引论文和工作区资料动态生成；仅调用允许的科研工具。",
        }

    @staticmethod
    def _task(task_id: str, task: str, agent: str, tool: str, tool_selection_reason: str) -> dict[str, str]:
        return {"id": task_id, "task": task, "agent": agent, "tool": tool, "tool_selection_reason": tool_selection_reason, "status": "pending"}
