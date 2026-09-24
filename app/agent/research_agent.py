"""Focused RAG Agent for multi-paper research knowledge questions."""

from app.agent.research_planner import ResearchPlanner
from app.services.citation_service import build_source_quality
from app.services.agent_trace_service import AgentTraceService
from app.services.llm_service import (
    answer_question_with_retrieved_context,
    generate_research_report,
)
from app.services.query_service import rewrite_query
from app.services.rag_query_record_service import RagQueryRecordService
from app.services.rag_evaluation_service import evaluate_retrieval
from app.services.retrieval_service import RetrievalService


class ResearchAgent:
    """Retrieve paper evidence, compose a grounded prompt, and answer with Qwen."""

    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        planner: ResearchPlanner | None = None,
        record_service: RagQueryRecordService | None = None,
        trace_service: AgentTraceService | None = None,
    ) -> None:
        self._retrieval_service = retrieval_service or RetrievalService()
        self._planner = planner or ResearchPlanner()
        self._record_service = record_service or RagQueryRecordService()
        self._trace_service = trace_service or AgentTraceService()

    def answer_question(
        self,
        question: str,
        paper_ids: list[str] | None = None,
    ) -> dict[str, object]:
        """Return an evidence-grounded multi-paper answer and its citations."""
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("请输入科研知识问题。")
        trace_id = self._trace_service.create_trace_id()
        trace_steps = [self._record_trace(trace_id, "分析问题", "已理解用户的科研知识问题。")]
        plan = self._planner.plan(normalized_question)
        trace_steps.append(self._record_trace(
            trace_id, "制定研究任务", f"已识别为“{plan['task_type']}”任务，并选择对应分析策略。"
        ))
        retrieval_query = rewrite_query(normalized_question)
        trace_steps.append(self._record_trace(trace_id, "优化检索 Query", "已将问题转换为适合文献检索的查询表达。"))
        sources = self._retrieval_service.retrieve(retrieval_query, paper_ids, top_k=5)
        trace_steps.append(self._record_trace(
            trace_id, "检索相关论文", f"已检索并获得 {len(sources)} 条候选论文证据。"
        ))
        trace_steps.append(self._record_trace(
            trace_id, "筛选关键证据", f"已完成混合检索与重排，保留 {len(sources)} 条相关证据。"
        ))
        if not sources:
            result = {
                "answer": "未在选定论文中检索到足够证据，建议上传更多相关论文或调整问题表述。",
                "sources": [],
                "confidence": "low",
                "source_quality": build_source_quality([]),
                "retrieval_evaluation": evaluate_retrieval([]),
                "agent_plan": {**plan, "retrieval_query": retrieval_query},
                "agent_trace": {"trace_id": trace_id, "steps": trace_steps},
            }
            self._record_service.save(normalized_question, result["answer"], [], paper_ids or [], plan["task_type"])
            return result

        answer = answer_question_with_retrieved_context(
            normalized_question,
            sources,
            task_instruction=plan["instruction"],
        )
        trace_steps.append(self._record_trace(trace_id, "生成研究结论", "已基于筛选后的论文证据生成回答。"))
        public_sources = [self._public_source(source) for source in sources]
        result = {
            "answer": answer,
            "sources": public_sources,
            "confidence": self._retrieval_confidence(float(sources[0]["score"])),
            "source_quality": build_source_quality(public_sources),
            "retrieval_evaluation": evaluate_retrieval(public_sources),
            "agent_plan": {**plan, "retrieval_query": retrieval_query},
            "agent_trace": {"trace_id": trace_id, "steps": trace_steps},
        }
        self._record_service.save(normalized_question, answer, public_sources, paper_ids or [], plan["task_type"])
        return result

    def generate_report(
        self,
        report_type: str,
        paper_ids: list[str] | None = None,
    ) -> dict[str, object]:
        """Generate a structured cross-paper report from retriever evidence."""
        report_queries = {
            "literature_review": "总结选定论文的研究背景、技术路线、方法比较、创新点、不足和未来方向。",
            "technology_roadmap": "梳理选定论文反映的技术发展路线、关键阶段、技术演进和当前挑战。",
            "research_gap": "分析选定论文已覆盖内容、尚未解决的研究空白和潜在研究方向。",
        }
        question = report_queries.get(report_type)
        if question is None:
            raise ValueError("不支持的研究报告类型。")
        trace_id = self._trace_service.create_trace_id()
        trace_steps = [self._record_trace(trace_id, "分析问题", "已理解用户希望生成跨论文研究报告。")]
        trace_steps.append(self._record_trace(trace_id, "制定研究任务", f"已选择“{report_type}”报告模板。"))
        sources = self._retrieval_service.retrieve(question, paper_ids, top_k=5)
        trace_steps.append(self._record_trace(trace_id, "检索相关论文", f"已检索到 {len(sources)} 条研究证据。"))
        trace_steps.append(self._record_trace(trace_id, "筛选关键证据", f"已筛选出 {len(sources)} 条可用于报告的证据。"))
        if not sources:
            return {
                "report_type": report_type,
                "report": {"说明": "未检索到足够论文证据，暂时无法生成报告。"},
                "sources": [],
                "confidence": "low",
                "source_quality": build_source_quality([]),
                "retrieval_evaluation": evaluate_retrieval([]),
                "agent_trace": {"trace_id": trace_id, "steps": trace_steps},
            }
        public_sources = [self._public_source(source) for source in sources]
        report = generate_research_report(report_type, sources)
        trace_steps.append(self._record_trace(trace_id, "生成研究结论", "已依据引用证据生成结构化研究报告。"))
        summary = "；".join(
            str(value) if isinstance(value, str) else "、".join(value)
            for value in report.values()
        )[:2_000]
        self._record_service.save(question, summary, public_sources, paper_ids or [], "report")
        return {
            "report_type": report_type,
            "report": report,
            "sources": public_sources,
            "confidence": self._retrieval_confidence(float(sources[0]["score"])),
            "source_quality": build_source_quality(public_sources),
            "retrieval_evaluation": evaluate_retrieval(public_sources),
            "agent_trace": {"trace_id": trace_id, "steps": trace_steps},
        }

    def _record_trace(self, trace_id: str, step: str, message: str) -> dict[str, str]:
        """Write a safe product-facing milestone and return it for the API response."""
        return self._trace_service.record(trace_id, step, message)

    @staticmethod
    def _public_source(source: dict[str, object]) -> dict[str, object]:
        """Return a compact citation card rather than a full stored chunk."""
        content = str(source["content"]).strip()
        return {
            "paper_id": source["paper_id"],
            "paper_title": source["paper_title"],
            "section": source["section"],
            "content": content[:600] + ("…" if len(content) > 600 else ""),
            "score": round(float(source["score"]), 4),
        }

    @staticmethod
    def _retrieval_confidence(top_score: float) -> str:
        """Describe evidence similarity only; it is not a factual-accuracy score."""
        if top_score >= 0.65:
            return "high"
        if top_score >= 0.4:
            return "medium"
        return "low"
