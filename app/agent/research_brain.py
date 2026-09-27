"""Autonomous-but-bounded orchestrator for ResearchOS v2."""

from __future__ import annotations

from typing import Any

from app.agent.research_master_agent import ResearchMasterAgent
from app.agent.research_result_evaluator import ResearchResultEvaluator
from app.agent.research_task_planner import ResearchTaskPlanner
from app.services.paper_library_service import PaperLibraryService
from app.services.query_service import rewrite_query
from app.services.autonomous_research_run_service import AutonomousResearchRunService
from app.memory.research_memory_service import ResearchMemoryService
from app.tools.tool_router import ResearchToolRouter
from app.workspace.workspace_profile_service import WorkspaceProfileService


class ResearchBrain:
    """Plan, call controlled tools, reflect on evidence, and persist safe results."""

    def __init__(self, *, master_agent: ResearchMasterAgent | None = None, planner: ResearchTaskPlanner | None = None, evaluator: ResearchResultEvaluator | None = None, tool_router: ResearchToolRouter | None = None, run_service: AutonomousResearchRunService | None = None, paper_service: PaperLibraryService | None = None, memory_service: ResearchMemoryService | None = None, workspace_profile_service: WorkspaceProfileService | None = None) -> None:
        self._master_agent = master_agent or ResearchMasterAgent()
        self._planner = planner or ResearchTaskPlanner()
        self._evaluator = evaluator or ResearchResultEvaluator()
        self._tools = tool_router or ResearchToolRouter()
        self._runs = run_service or AutonomousResearchRunService()
        self._papers = paper_service or PaperLibraryService()
        self._memory = memory_service or ResearchMemoryService()
        self._workspace_profile = workspace_profile_service or WorkspaceProfileService(self._tools.file_tool)

    def tool_catalog(self) -> list[dict[str, str]]:
        return self._tools.catalog()

    def list_runs(self) -> list[dict[str, object]]:
        return self._runs.list_recent()

    def get_run(self, run_id: str) -> dict[str, object]:
        return self._runs.get(run_id)

    def run(self, goal: str, paper_ids: list[str] | None = None, generate_docx: bool = False) -> dict[str, object]:
        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("请输入科研目标。")
        record = self._runs.create(normalized_goal)
        timeline: list[dict[str, object]] = []
        tool_results: dict[str, object] = {}
        environment_profile = self._workspace_profile.build_profile()
        memory_snapshot = self._memory.refresh_lab_profile()
        workspace_assets = list(environment_profile["assets"])
        ready_papers = [paper for paper in self._papers.list_papers() if paper.quality_status == "ready" and (not paper_ids or paper.paper_id in paper_ids)]
        plan = self._planner.build_plan(normalized_goal, has_ready_papers=bool(ready_papers), workspace_assets=workspace_assets)
        self._mark(timeline, "Research Brain", "已理解科研目标，并完成环境感知和执行计划制定。", "completed")
        self._persist(record["id"], "running", plan, timeline, tool_results, environment_profile, memory_snapshot, {}, {}, "环境感知与任务规划", "workspace_file")
        workspace_reads: list[dict[str, object]] = []
        for asset in workspace_assets[:5]:
            if asset.get("type") not in {"PDF", "DOCX", "TXT"}:
                continue
            try:
                content = self._tools.file_tool.read_text(str(asset["path"]), max_chars=1_000)
                workspace_reads.append({"path": asset["path"], "text_length": len(content), "excerpt": content[:400]})
            except ValueError as error:
                workspace_reads.append({"path": asset["path"], "error": str(error)})
        tool_results["workspace_file"] = {"assets": workspace_assets, "read_items": workspace_reads, "status": "completed"}
        self._set_task_status(plan, "discover_workspace", "completed" if workspace_assets else "skipped")
        if workspace_assets:
            self._mark(timeline, "File Tool", f"发现 {len(workspace_assets)} 个受限科研工作区资料，并读取 {len(workspace_reads)} 个可读文件摘要。", "completed")
        self._persist(record["id"], "running", plan, timeline, tool_results, environment_profile, memory_snapshot, {}, {}, "已完成工作区资料读取", "workspace_file")

        for asset in workspace_assets:
            if asset.get("type") in {"CSV", "Excel"} and any(word in normalized_goal for word in ("数据", "实验", "表格", "Excel", "excel", "CSV", "csv")):
                try:
                    tool_results.setdefault("data_analysis", {"items": []})["items"].append(self._tools.data_tool.summarize(str(asset["path"])))
                    self._mark(timeline, "Data Analysis Tool", f"已汇总 {asset['path']} 的表格结构。", "completed")
                except ValueError as error:
                    self._mark(timeline, "Data Analysis Tool", f"无法读取 {asset['path']}：{error}", "skipped")
        if any(task["id"] == "summarize_data" for task in plan["tasks"]):
            self._set_task_status(plan, "summarize_data", "completed" if tool_results.get("data_analysis", {}).get("items") else "skipped")

        sources: list[dict[str, object]] = []
        retrieval_query = normalized_goal
        if ready_papers:
            self._mark(timeline, "Knowledge Agent", "调用 Knowledge Tool 检索团队知识库。", "running")
            retrieval_query = rewrite_query(normalized_goal)
            sources = self._tools.knowledge_tool.search(retrieval_query, [paper.paper_id for paper in ready_papers], top_k=8)
            # Reflection-driven adjustment: retry with the original goal when
            # an optimized query did not retrieve usable evidence.
            if not sources and retrieval_query != normalized_goal:
                self._mark(timeline, "Research Brain", "检索证据不足，改用原始目标再次检索。", "running")
                sources = self._tools.knowledge_tool.search(normalized_goal, [paper.paper_id for paper in ready_papers], top_k=8)
            tool_results["knowledge_retrieval"] = {"query": retrieval_query, "source_count": len(sources), "sources": [self._source_pointer(item) for item in sources]}
            self._mark(timeline, "Knowledge Agent", f"已筛选 {len(sources)} 条可追溯知识库证据。", "completed" if sources else "needs_input")
            self._set_task_status(plan, "retrieve_knowledge", "completed" if sources else "needs_input")
        else:
            self._set_task_status(plan, "request_evidence", "completed")
        self._persist(record["id"], "running", plan, timeline, tool_results, environment_profile, memory_snapshot, {}, {}, "已完成知识检索与结果观察", "knowledge_retrieval")

        master_result: dict[str, object] = {}
        master_failed = False
        if sources:
            self._mark(timeline, "Research Master", "根据任务计划调度专项 Agent 并生成研究交付物。", "running")
            try:
                master_result = self._master_agent.run_task(normalized_goal, list(plan["selected_agents"]), [paper.paper_id for paper in ready_papers])
                self._mark(timeline, "Research Master", "已完成专项分析和研究报告整合。", "completed")
                tool_results["research_agents"] = {"status": "completed", "selected_agents": plan["selected_agents"], "source_count": len(master_result.get("sources", []))}
                self._set_task_status(plan, "analyze_research", "completed")
            except Exception as error:
                # Do not expose provider-specific details or hidden reasoning.
                self._mark(timeline, "Research Master", f"科研报告未完成：{type(error).__name__}。", "failed")
                tool_results["research_agents"] = {"status": "failed", "message": "模型服务未能完成本次报告，请稍后重试。"}
                master_failed = True
                self._set_task_status(plan, "analyze_research", "failed")

        self._persist(record["id"], "running", plan, timeline, tool_results, environment_profile, memory_snapshot, {}, {}, "已完成专项 Agent 执行", "research_agents")

        reflection = self._evaluator.evaluate(sources, workspace_assets, bool(master_result), normalized_goal, master_failed)
        self._mark(timeline, "Result Evaluation", "已检查资料依据、检索结果与下一步处理条件。", "completed")

        final_output: dict[str, object] = {
            "status": "completed" if master_result else ("failed" if master_failed else "needs_evidence"),
            "research_result": master_result,
            "evidence": [self._source_pointer(item) for item in sources],
            "recommended_next_step": reflection["next_decision"],
        }
        if master_result:
            proposal = self._tools.project_tool.prepare(master_result.get("project_plan"))
            tool_results["project_planning"] = proposal
            self._mark(timeline, "Project Tool", "已形成待负责人确认的项目方案建议。", "completed")
            self._set_task_status(plan, "prepare_project", "completed")
            summary = str(master_result.get("executive_summary", "")) or "ResearchOS 已完成基于当前资料的研究分析。"
            document = self._tools.document_tool.generate_markdown(record["id"], "ResearchOS 自主科研执行交付物", summary)
            if generate_docx:
                document["word"] = self._tools.document_tool.generate_docx(record["id"], "ResearchOS 自主科研执行交付物", summary)
            tool_results["document_generation"] = document
            self._mark(timeline, "Document Tool", "已生成本地研究交付物文件。", "completed")
            self._set_task_status(plan, "generate_deliverable", "completed")

        status = "completed" if master_result else ("failed" if master_failed else "needs_evidence")
        return self._persist(
            record["id"], status, plan, timeline, tool_results, environment_profile, memory_snapshot,
            reflection, final_output, "已完成交付检查" if status == "completed" else "等待补充资料或人工处理",
            "document_generation" if master_result else "knowledge_retrieval", reflection.get("next_plan", []),
            "模型服务未完成本次报告。" if master_failed else "",
        )

    def _persist(self, run_id: str, status: str, plan: dict[str, object], timeline: list[dict[str, object]], tool_results: dict[str, object], environment_profile: dict[str, object], memory_snapshot: dict[str, object], reflection: dict[str, object], final_output: dict[str, object], current_step: str, current_tool: str, next_plan: list[dict[str, object]] | None = None, failure_reason: str = "") -> dict[str, object]:
        completed = [str(task["id"]) for task in plan.get("tasks", []) if task.get("status") == "completed"]
        return self._runs.update(
            run_id,
            status=status,
            task_plan=plan,
            execution_timeline=timeline,
            tool_results=tool_results,
            environment_profile=environment_profile,
            memory_snapshot=memory_snapshot,
            reflection=reflection,
            final_output=final_output,
            current_step=current_step,
            current_tool=current_tool,
            completed_tasks=completed,
            next_plan=next_plan,
            failure_reason=failure_reason,
        )

    @staticmethod
    def _mark(timeline: list[dict[str, object]], actor: str, message: str, status: str) -> None:
        timeline.append({"actor": actor, "message": message, "status": status})

    @staticmethod
    def _set_task_status(plan: dict[str, object], task_id: str, status: str) -> None:
        for task in plan.get("tasks", []):
            if task.get("id") == task_id:
                task["status"] = status
                return

    @staticmethod
    def _source_pointer(source: dict[str, object]) -> dict[str, object]:
        return {
            "paper_id": source.get("paper_id", ""),
            "source": source.get("filename") or source.get("paper_title", ""),
            "section": source.get("section", "正文"),
            "score": source.get("score", source.get("hybrid_score", 0)),
        }
