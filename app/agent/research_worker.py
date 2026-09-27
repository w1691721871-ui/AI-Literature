"""Controlled Research Worker: factual tools, short task context and human review."""

from __future__ import annotations

from datetime import datetime, timezone

from app.agent.research_worker_loop.critic import ResearchWorkerCritic
from app.agent.research_worker_loop.executor import ResearchWorkerExecutor
from app.agent.research_worker_loop.observer import ResearchWorkerObserver
from app.agent.research_worker_loop.planner import ResearchWorkerPlanner
from app.agent.research_worker_loop.replanner import ResearchWorkerReplanner
from app.services.research_worker_context_service import ResearchWorkerContextService
from app.services.research_worker_run_service import ResearchWorkerRunService
from app.tools.research_worker.tool_router import ResearchWorkerToolRouter


class ResearchWorker:
    """Run a bounded Goal → Plan → Execute → Observe → Evaluate → Deliver loop."""

    def __init__(self, *, router: ResearchWorkerToolRouter | None = None, run_service: ResearchWorkerRunService | None = None, context_service: ResearchWorkerContextService | None = None) -> None:
        self._router = router or ResearchWorkerToolRouter()
        self._runs = run_service or ResearchWorkerRunService()
        self._contexts = context_service or ResearchWorkerContextService()
        self._planner, self._executor = ResearchWorkerPlanner(), ResearchWorkerExecutor(self._router)
        self._observer, self._critic, self._replanner = ResearchWorkerObserver(), ResearchWorkerCritic(), ResearchWorkerReplanner()

    def tool_catalog(self) -> list[dict[str, str]]:
        return self._router.catalog()

    def get_run(self, run_id: str) -> dict[str, object]:
        payload = self._runs.get(run_id)
        payload["context"] = self._contexts.get(run_id)
        return payload

    def context(self, run_id: str) -> dict[str, object]:
        self._runs.get(run_id)  # preserve not-found behavior
        return self._contexts.get(run_id)

    def timeline(self, run_id: str) -> list[dict[str, object]]:
        return list(self.get_run(run_id).get("execution_history", []))

    def run(self, goal: str) -> dict[str, object]:
        goal = goal.strip()
        if not goal:
            raise ValueError("请输入需要执行的科研任务。")
        record = self._runs.create(goal)
        history: list[dict[str, object]] = []
        selected = self._router.select(goal)
        plan = self._planner.build(goal, selected)
        self._event(history, "planning", "任务规划", f"已生成 {len(plan)} 个可复核任务。", input_summary=goal, tool="Planner")
        self._save(record["run_id"], "running", "executing", "正在按计划读取真实科研资料", plan, selected, {}, {}, history)
        results: dict[str, object] = {}
        try:
            file_result = self._executor.execute_file()
            results["file_tool"] = file_result
            self._mark(plan, "file_tool", "completed")
            self._event(history, "executing", "File Tool", f"已完成 {len(file_result.get('file_reports', []))} 份文件结构报告。", input_summary="Research Workspace 允许文件", tool="File Tool")

            try:
                knowledge_result = self._executor.execute_knowledge(goal)
            except Exception as error:
                knowledge_result = {"source_count": 0, "sources": [], "status": "unavailable", "message": f"知识检索暂不可用（{type(error).__name__}）。"}
            results["knowledge_tool"] = knowledge_result
            self._mark(plan, "knowledge_tool", "completed" if knowledge_result.get("source_count", 0) else "needs_evidence")
            evidence_count = int(knowledge_result.get("source_count", 0))
            self._event(history, "executing", "Knowledge Tool", f"获得 {evidence_count} 条可追溯论文证据。", input_summary=goal, tool="Knowledge Tool", evidence_count=evidence_count)

            data_result: dict[str, object] | None = None
            if self._has_tool(selected, "data_tool"):
                data_result = self._executor.execute_data()
                results["data_tool"] = data_result
                self._mark(plan, "data_tool", "completed")
                self._event(history, "executing", "Data Tool", f"发现 {data_result.get('dataset_count', 0)} 个实验数据文件。", input_summary="工作区 CSV/XLSX", tool="Data Tool")

            observation = self._observer.inspect(file_result, data_result, knowledge_result)
            results["observation"] = observation
            self._event(history, "observing", "结果观察", str(observation["summary"]), input_summary="工具结果摘要", tool="Observer", evidence_count=evidence_count)
            self._save(record["run_id"], "running", "evaluating", "正在检查资料覆盖与结果可用性", plan, selected, results, {}, history)
            critic = self._critic.evaluate(goal, observation)
            reflection = {**critic, "observation": observation, "human_review": "所有报告、技术路线与后续项目均需负责人确认；Research Worker 不会自动创建 Action、Decision 或 Project。"}
            self._event(history, "evaluating", "结果评价", str(critic["score"]), input_summary="资料覆盖、Evidence 与任务目标", tool="Critic", evidence_count=evidence_count)

            if critic["needs_replan"]:
                next_plan = self._replanner.adjust(plan, critic, observation)
                reflection["next_plan"] = next_plan
                self._event(history, "replanning", "计划调整", next_plan[0]["reason"] if next_plan else "等待人工确认。", input_summary="评价问题", tool="Replanner", evidence_count=evidence_count)
                content = self._insufficient_report_content(goal, file_result, observation, critic)
                document = self._executor.execute_document(record["run_id"], content)
                results["document_tool"] = document
                self._mark(plan, "document_tool", "completed")
                self._event(history, "delivery", "Document Tool", "已生成资料不足/数据质量说明，未生成科研结论。", input_summary="已验证资料与问题", tool="Document Tool", evidence_count=evidence_count)
                return self._save(record["run_id"], "need_confirmation", "replanning", "已生成待确认的资料不足报告", plan, selected, results, reflection, history, self._output_path(document))

            if self._has_tool(selected, "project_tool"):
                results["project_tool"] = self._executor.execute_project(goal, evidence_count)
                self._mark(plan, "project_tool", "completed")
                self._event(history, "executing", "Project Tool", "已形成待负责人确认的项目辅助建议。", input_summary=goal, tool="Project Tool", evidence_count=evidence_count)
            document = self._executor.execute_document(record["run_id"], self._delivery_content(goal, file_result, knowledge_result, data_result))
            results["document_tool"] = document
            self._mark(plan, "document_tool", "completed")
            self._event(history, "delivery", "Document Tool", "已生成含 Evidence 来源的待人工复核交付物。", input_summary="已验证资料", tool="Document Tool", evidence_count=evidence_count)
            reflection["next_plan"] = [{"action": "人工复核交付物", "reason": "确认资料范围、引用证据和后续科研行动。"}]
            return self._save(record["run_id"], "completed", "completed", "已生成待人工复核的科研执行交付物", plan, selected, results, reflection, history, self._output_path(document))
        except Exception as error:
            reflection = {"score": "执行未完成", "issues": ["受控工具未完成本次任务。"], "suggestion": "检查允许的科研资料后重试。", "failure_type": type(error).__name__, "human_review": "未生成可作为科研结论的交付物。"}
            self._event(history, "evaluating", "执行异常", "工具执行未完成，未输出科研结论。", tool="Worker")
            return self._save(record["run_id"], "failed", "failed", "科研执行工具未完成", plan, selected, results, reflection, history)

    def _save(self, run_id: str, status: str, phase: str, current_step: str, plan: list[dict[str, object]], selected: list[dict[str, str]], results: dict[str, object], reflection: dict[str, object], history: list[dict[str, object]], output_file: str = "") -> dict[str, object]:
        payload = self._runs.update(run_id, status=status, current_phase=phase, current_step=current_step, plan=plan, selected_tools=selected, tool_results=results, reflection=reflection, execution_history=history, output_file=output_file)
        context = self._build_context(payload)
        self._contexts.save(run_id, context)
        payload["context"] = context
        return payload

    @staticmethod
    def _build_context(payload: dict[str, object]) -> dict[str, object]:
        result = payload.get("result", {}) if isinstance(payload.get("result"), dict) else {}
        reflection = payload.get("reflection", {}) if isinstance(payload.get("reflection"), dict) else {}
        tool_summaries = []
        for name, value in result.items():
            if isinstance(value, dict):
                summary = value.get("summary") or value.get("message") or value.get("source_count") or value.get("asset_count")
                tool_summaries.append({"tool": name, "summary": str(summary or "已完成受控工具调用")})
        return {"user_goal": payload.get("user_goal", ""), "history_steps": payload.get("execution_history", []), "used_tools": [item.get("name", "") for item in payload.get("tools", []) if isinstance(item, dict)], "tool_result_summaries": tool_summaries, "discovered_issues": reflection.get("issues", []), "current_status": payload.get("status", ""), "next_suggestions": reflection.get("next_plan", []), "context_boundary": "仅保存当前任务的用户可读执行摘要；不保存原始文件内容、隐私数据或模型内部思维。"}

    @staticmethod
    def _event(history: list[dict[str, object]], phase: str, action: str, result_summary: str, *, input_summary: str = "", tool: str = "", evidence_count: int = 0) -> None:
        history.append({"phase": phase, "module": tool or action, "action": action, "input_summary": input_summary, "result_summary": result_summary, "tool": tool, "evidence_count": evidence_count, "timestamp": datetime.now(timezone.utc).isoformat()})

    @staticmethod
    def _has_tool(selected: list[dict[str, str]], name: str) -> bool:
        return any(item["name"] == name for item in selected)

    @staticmethod
    def _mark(plan: list[dict[str, object]], tool_name: str, status: str) -> None:
        for item in plan:
            if item.get("tool") == tool_name:
                item["status"] = status

    @staticmethod
    def _output_path(document: dict[str, object]) -> str:
        return str(document.get("markdown", {}).get("path", ""))

    @staticmethod
    def _evidence_lines(knowledge_result: dict[str, object]) -> list[str]:
        sources = knowledge_result.get("sources", [])
        lines = []
        for index, source in enumerate(sources[:10], start=1):
            if not isinstance(source, dict):
                continue
            title = source.get("paper_title") or source.get("source") or "未命名资料"
            section = source.get("section") or source.get("chapter") or "未标注章节"
            score = source.get("score", "未提供")
            lines.append(f"{index}. {title}｜{section}｜匹配度：{score}")
        return lines

    def _delivery_content(self, goal: str, file_result: dict[str, object], knowledge_result: dict[str, object], data_result: dict[str, object] | None) -> str:
        reports = file_result.get("file_reports", [])
        names = [str(item.get("filename", "")) for item in reports[:10] if isinstance(item, dict)]
        lines = [f"## 任务目标\n{goal}", "## 使用资料", *(f"- {name}" for name in names), "", "## 分析过程摘要", "- 已读取允许的工作区文件结构。", "- 已查询当前知识库并仅使用返回的 Evidence 形成报告。"]
        if data_result:
            lines.extend(["", "## 数据观察结果", f"- 发现数据集：{data_result.get('dataset_count', 0)} 个。", "- 仅包含字段、缺失值和基础规模统计，不包含自动因果结论。"])
        lines.extend(["", "## Evidence 来源", *[f"- {line}" for line in self._evidence_lines(knowledge_result)], "", "## 发现的问题", "- 本报告是受控辅助交付物，仍需负责人核验资料范围与实验设计。", "", "## 建议下一步", "- 人工确认 Evidence 是否覆盖任务目标后，再决定是否创建 Action、Decision 或 Project。"])
        return "\n".join(lines)

    @staticmethod
    def _insufficient_report_content(goal: str, file_result: dict[str, object], observation: dict[str, object], critic: dict[str, object]) -> str:
        names = [str(item.get("filename", "")) for item in file_result.get("file_reports", []) if isinstance(item, dict)]
        material_lines = [f"- {name}" for name in names] or ["- 暂无可读取科研资料"]
        issue_lines = [f"- {item}" for item in critic.get("issues", [])]
        return "\n".join([
            "## 资料不足报告", f"\n## 任务目标\n{goal}", "\n## 已发现资料", *material_lines,
            "\n## 数据观察结果", str(observation.get("summary", "暂无可验证资料。")),
            "\n## Evidence 来源", "- 暂无可验证资料", "\n## 发现的问题", *issue_lines,
            "\n## 建议下一步", "- 补充可索引论文、实验数据或项目资料后重新执行。", "- 本报告不包含科研结论或技术路线建议。",
        ])
