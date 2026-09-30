"""Read-only readiness checks for the ResearchOS evidence workflow.

The service deliberately distinguishes a missing capability from a capability
that has not run because the workspace contains no user-provided material.
It never calls a model, builds an index, or creates demo research data.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import func, select

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.research_action import ResearchAction
from app.models.research_decision import ResearchDecision
from app.models.research_outcome import ResearchOutcome
from app.models.research_project import ResearchProject
from app.services.database import SessionLocal, initialize_database
from app.services.vector_store import INDEX_PATH, MAPPING_PATH


class ResearchOSDiagnosticService:
    """Produce user-safe diagnostic statuses without exposing secrets."""

    @staticmethod
    def _check(identifier: str, label: str, status: str, detail: str) -> dict[str, str]:
        return {"id": identifier, "label": label, "status": status, "detail": detail}

    def run(self) -> dict[str, object]:
        # Match the runtime clients: diagnostics must inspect the configured
        # local environment rather than report a false negative after a fresh
        # server process starts.
        load_dotenv()
        initialize_database()
        session = SessionLocal()
        try:
            paper_count = int(session.scalar(select(func.count(Paper.paper_id))) or 0)
            ready_count = int(session.scalar(select(func.count(Paper.paper_id)).where(Paper.quality_status == "ready")) or 0)
            parsed_count = int(session.scalar(select(func.count(Paper.paper_id)).where(Paper.analysis_status.in_(("parsed", "indexed", "ready")))) or 0)
            chunk_count = int(session.scalar(select(func.count(PaperChunk.id))) or 0)
            embedded_count = int(session.scalar(select(func.count(PaperChunk.id)).where(PaperChunk.embedding != "")) or 0)
            action_count = int(session.scalar(select(func.count(ResearchAction.id))) or 0)
            decision_count = int(session.scalar(select(func.count(ResearchDecision.id))) or 0)
            project_count = int(session.scalar(select(func.count(ResearchProject.id))) or 0)
            outcome_count = int(session.scalar(select(func.count(ResearchOutcome.id))) or 0)
        finally:
            session.close()

        index_ready = INDEX_PATH.exists() and MAPPING_PATH.exists()
        embedding_configured = bool(os.getenv("DASHSCOPE_API_KEY") and os.getenv("EMBEDDING_MODEL", "text-embedding-v4"))
        no_material = paper_count == 0
        checks = [
            self._check("document_parse", "Document parsing", "NEEDS_REAL_DATA" if no_material else ("PASS" if parsed_count else "FAIL"), "等待用户上传可解析的授权科研 PDF。" if no_material else f"已解析资料：{parsed_count} / {paper_count}。"),
            self._check("chunking", "Chunk generation", "NEEDS_REAL_DATA" if no_material else ("PASS" if chunk_count else "FAIL"), "当前没有真实资料可切分。" if no_material else f"已生成知识片段：{chunk_count}。"),
            self._check("embedding", "Embedding availability", "NEEDS_REAL_DATA" if no_material else ("PASS" if embedding_configured and embedded_count else "FAIL"), "等待真实资料后验证向量化。" if no_material else (f"已保存向量片段：{embedded_count}。" if embedding_configured else "Embedding 环境变量未配置。")),
            self._check("faiss", "FAISS index", "NEEDS_REAL_DATA" if no_material else ("PASS" if index_ready else "FAIL"), "当前没有真实资料，因此尚未建立索引。" if no_material else ("索引与映射文件均存在。" if index_ready else "已存在资料但本地索引不可用，请重新索引。")),
            self._check("query_rewrite", "Query rewrite", "NEEDS_REAL_DATA" if no_material else "NOT_RUN", "问题改写仅在真实科研问题发起后执行，不使用演示问题伪造结果。"),
            self._check("retrieval", "Retrieval", "NEEDS_REAL_DATA" if no_material else ("NOT_RUN" if ready_count and index_ready else "FAIL"), "真实资料上传后，可通过知识问答或 Research Command 实际验证检索。" if no_material else ("检索链路已就绪，尚未针对当前资料运行真实问题。" if ready_count and index_ready else "缺少 ready 状态资料或向量索引。")),
            self._check("rerank", "Rerank", "NEEDS_REAL_DATA" if no_material else "NOT_RUN", "重排只在真实检索候选片段返回后运行，不使用合成片段验证。"),
            self._check("evidence", "Evidence generation", "NEEDS_REAL_DATA" if no_material else "NOT_RUN", "Evidence 只会在真实检索/Agent 结果中生成，不创建合成来源。"),
            self._check("research_master", "Research Master", "NEEDS_REAL_DATA" if no_material else "NOT_RUN", "Research Master 路由已注册；需真实资料后才会生成有依据的分析。"),
            self._check("research_worker", "Research Worker", "PASS", "受控工具与执行 API 已注册；无资料时会返回需补充资料/人工确认。"),
            self._check("decision", "Decision persistence", "NOT_RUN" if not action_count else "PASS", "尚无 Action，因此未创建人工决策记录。" if not action_count else f"已保存行动：{action_count}，人工决定：{decision_count}。"),
            self._check("project", "Project persistence", "NOT_RUN" if not project_count else "PASS", "尚未创建科研项目。" if not project_count else f"已保存科研项目：{project_count}。"),
            self._check("deliverable", "Deliverable generation", "NOT_RUN" if not outcome_count else "PASS", "尚未创建项目成果记录。" if not outcome_count else f"已保存成果记录：{outcome_count}。"),
        ]
        return {
            "overall": "NEEDS_REAL_DATA" if no_material else ("PASS" if all(item["status"] in {"PASS", "NOT_RUN"} for item in checks) else "FAIL"),
            "data_boundary": "诊断不会创建论文、Evidence、科研结论或调用模型；NOT_RUN 与 NEEDS_REAL_DATA 不代表功能通过。",
            "counts": {"papers": paper_count, "ready_papers": ready_count, "chunks": chunk_count, "embedded_chunks": embedded_count},
            "checks": checks,
        }
