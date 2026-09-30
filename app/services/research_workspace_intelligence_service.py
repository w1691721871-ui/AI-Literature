"""Persistent, evidence-bounded snapshots for continuing Research Master work.

This service deliberately reuses the existing ``research_workspaces`` and
``research_memories`` tables.  A workspace snapshot stores product-facing
research state, not prompts, token logs, hidden reasoning, or source text.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.models.research_memory import ResearchMemory
from app.models.research_workspace import ResearchWorkspace
from app.services.database import SessionLocal, initialize_database
from app.services.workspace_service import WorkspaceNotFoundError


class ResearchWorkspaceIntelligenceService:
    """Create, persist, resume and evaluate compact research workspaces."""

    MEMORY_PREFIX = "research_workspace:"

    def __init__(self, session_factory=SessionLocal, *, initialize: bool = True) -> None:
        if initialize:
            initialize_database()
        self._sessions = session_factory

    def resolve_or_create(self, research_goal: str, workspace_id: str | None = None) -> dict[str, object]:
        """Use a requested workspace or create one for this Research Master run."""
        session = self._sessions()
        try:
            if workspace_id:
                workspace = session.get(ResearchWorkspace, workspace_id)
                if workspace is None:
                    raise WorkspaceNotFoundError("未找到指定的 Research Workspace。")
            else:
                title = self._workspace_title(research_goal)
                workspace = ResearchWorkspace(
                    name=title,
                    member_roles=json.dumps(["科研负责人", "Research Master"], ensure_ascii=False),
                )
                session.add(workspace)
                session.commit()
                session.refresh(workspace)
            return self._workspace_identity(workspace)
        finally:
            session.close()

    def save_run(self, workspace_id: str, master_result: dict[str, object]) -> dict[str, object]:
        """Persist a safe workspace snapshot after a real Master execution."""
        session = self._sessions()
        try:
            workspace = session.get(ResearchWorkspace, workspace_id)
            if workspace is None:
                raise WorkspaceNotFoundError("未找到指定的 Research Workspace。")
            scope = self._scope(workspace_id)
            record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == scope))
            previous = self._decode_snapshot(record.memory_json) if record is not None else {}
            snapshot = self._snapshot(workspace, master_result, previous)
            if record is None:
                record = ResearchMemory(scope=scope)
                session.add(record)
            record.memory_json = json.dumps(snapshot, ensure_ascii=False)
            session.commit()
            return snapshot
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_workspaces(self) -> list[dict[str, object]]:
        """List workspace identities with their latest safe research status."""
        session = self._sessions()
        try:
            workspaces = session.scalars(
                select(ResearchWorkspace).order_by(ResearchWorkspace.created_at.desc())
            ).all()
            return [self._list_payload(session, workspace) for workspace in workspaces]
        finally:
            session.close()

    def get_workspace(self, workspace_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            workspace = self._require_workspace(session, workspace_id)
            return self._load_snapshot(session, workspace)
        finally:
            session.close()

    def update_workspace_snapshot(self, workspace_id: str, snapshot: dict[str, object]) -> dict[str, object]:
        """Persist a caller-provided product state without altering source knowledge."""
        session = self._sessions()
        try:
            self._require_workspace(session, workspace_id)
            scope = self._scope(workspace_id)
            record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == scope))
            if record is None:
                record = ResearchMemory(scope=scope)
                session.add(record)
            snapshot["saved_at"] = self._now()
            record.memory_json = json.dumps(snapshot, ensure_ascii=False)
            session.commit()
            return snapshot
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def resume(self, workspace_id: str) -> dict[str, object]:
        """Return only the research context needed to continue a prior task."""
        snapshot = self.get_workspace(workspace_id)
        return {
            "workspace_id": snapshot["workspace_id"],
            "research_goal": snapshot.get("research_goal", ""),
            "strategy": snapshot.get("strategy", {}),
            "used_evidence": snapshot.get("evidence_summary", []),
            "unresolved_questions": snapshot.get("unresolved_questions", []),
            "human_review": snapshot.get("human_review", {}),
            "decision_status": [
                item.get("status", "") for item in snapshot.get("decisions", []) if isinstance(item, dict)
            ],
            "memory_boundary": "恢复的是已执行任务的摘要、Evidence 引用与待确认事项；不恢复 Prompt、Token、内部推理或论文全文。",
        }

    def quality_metrics(self, workspace_id: str) -> dict[str, object]:
        snapshot = self.get_workspace(workspace_id)
        evidence = list(snapshot.get("evidence_summary", []))
        scores = [float(item["score"]) for item in evidence if isinstance(item.get("score"), (int, float))]
        papers = {str(item.get("paper_id", "")) for item in evidence if item.get("paper_id")}
        conflict = dict(snapshot.get("conflict_report", {}))
        evidence_count = len(evidence)
        return {
            "workspace_id": workspace_id,
            "metrics": {
                "evidence_coverage": self._level(evidence_count, good=3, excellent=6),
                "evidence_diversity": self._level(len(papers), good=2, excellent=3),
                "conflict_detection": conflict.get("status", "not_observed"),
                "retrieval_quality": self._score_level(sum(scores) / len(scores)) if scores else "not_available",
                "human_review_requirement": bool(snapshot.get("human_review", {}).get("required", False)),
            },
            "support_note": "Research Support Quality 描述当前资料对任务的支持范围，不表示科研事实准确率或模型准确率。",
        }

    def decision_candidate(self, workspace_id: str) -> dict[str, object]:
        """Return a cautious candidate; it never creates a formal Action."""
        snapshot = self.get_workspace(workspace_id)
        evidence = list(snapshot.get("evidence_summary", []))
        conflict = dict(snapshot.get("conflict_report", {}))
        needs_review = bool(snapshot.get("human_review", {}).get("required", False))
        if not evidence:
            return {
                "workspace_id": workspace_id,
                "statement": "当前没有可验证资料，暂不形成研究判断。",
                "evidence_refs": [],
                "confidence_level": "insufficient_evidence",
                "human_review": True,
                "next_action": "请上传并索引与研究目标相关的资料后，再由科研负责人确认下一步。",
                "boundary": "该候选不创建正式 Action，也不构成科研结论。",
            }
        if needs_review:
            statement = "当前 Evidence 显示存在需要人工核查的条件差异或潜在冲突，建议先完成条件比对后再决定验证方向。"
            next_action = "核验各来源的研究对象、评价指标与实验条件，并由科研负责人确认。"
            confidence = "needs_human_review"
        else:
            statement = "当前 Evidence 支持进一步验证该研究目标中的可行方向；该判断仍需科研人员结合实验条件确认。"
            next_action = "将已引用资料转为可验证的研究或实验计划，并由科研负责人确认。"
            confidence = "evidence_supported"
        return {
            "workspace_id": workspace_id,
            "statement": statement,
            "evidence_refs": evidence,
            "confidence_level": confidence,
            "human_review": True,
            "next_action": next_action,
            "boundary": "这是基于当前 Evidence 的待确认研究判断，不是自动生成的科研事实，也不会自动创建正式 Action。",
        }

    def _snapshot(
        self, workspace: ResearchWorkspace, result: dict[str, object], previous: dict[str, object] | None = None
    ) -> dict[str, object]:
        previous = previous or {}
        finite = dict(result.get("finite_loop", {}))
        strategy = dict(finite.get("strategy", {}))
        sources = self._evidence_summary(result.get("sources", []))
        subtasks = [self._subtask_summary(item) for item in finite.get("subtasks", []) if isinstance(item, dict)]
        conflict = dict(finite.get("conflict_report", result.get("conflict_report", {})) or {})
        review_required = bool(finite.get("requires_human_review", False) or conflict.get("requires_human_review", False))
        stop_reason = str(finite.get("stop_reason", result.get("status", "completed")))
        unresolved = self._unresolved_questions(finite, review_required)
        return {
            **self._workspace_identity(workspace),
            "research_goal": str(result.get("master_plan", {}).get("user_goal", result.get("user_goal", ""))),
            "strategy_type": strategy.get("strategy_type", "summary"),
            "strategy": self._safe_strategy(strategy),
            "status": str(finite.get("status", "completed")),
            "stop_reason": stop_reason,
            "evidence_count": len(sources),
            "tasks": subtasks,
            "evidence_summary": sources,
            "conflict_report": self._conflict_summary(conflict),
            "human_review": {"required": review_required, "status": "待人工确认" if review_required else "可人工确认"},
            "decisions": [{
                "status": "待确认",
                "statement": "已生成基于当前 Evidence 的待确认研究判断；系统不会自动创建正式 Action 或替代人工决策。",
                "evidence_count": len(sources),
                "requires_human_review": review_required,
            }],
            "deliverables": self._deliverable_summary(result, sources),
            "final_outcome": self._final_outcome_summary(result),
            "unresolved_questions": unresolved,
            "members": previous.get("members") or self._default_members(workspace.id),
            "workflow": self._workflow_state(len(sources), review_required),
            "review_items": self._review_items(sources, conflict),
            "evidence_graph": self._evidence_graph(sources, conflict),
            "saved_at": self._now(),
            "memory_boundary": "仅保存目标、执行摘要、Evidence 引用、冲突/人工审核状态和交付物摘要；不保存 Prompt、Token、内部推理或论文全文。",
        }

    def _load_snapshot(self, session: Any, workspace: ResearchWorkspace) -> dict[str, object]:
        record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == self._scope(workspace.id)))
        if record is None:
            return self._ensure_product_fields(workspace, {
                **self._workspace_identity(workspace), "research_goal": "", "strategy_type": "", "strategy": {}, "status": "empty",
                "evidence_count": 0, "tasks": [], "evidence_summary": [], "conflict_report": {},
                "human_review": {"required": False, "status": "尚未运行"}, "decisions": [], "deliverables": [],
                "final_outcome": {}, "unresolved_questions": ["尚未在此 Workspace 中运行 Research Master 任务。"],
                "memory_boundary": "该 Workspace 尚无研究执行快照。",
            })
        try:
            parsed = json.loads(record.memory_json)
            return self._ensure_product_fields(workspace, parsed if isinstance(parsed, dict) else {})
        except json.JSONDecodeError:
            return {**self._workspace_identity(workspace), "status": "invalid_snapshot", "evidence_count": 0, "tasks": []}

    def _list_payload(self, session: Any, workspace: ResearchWorkspace) -> dict[str, object]:
        snapshot = self._load_snapshot(session, workspace)
        return {
            **self._workspace_identity(workspace),
            "research_goal": snapshot.get("research_goal", ""),
            "strategy_type": snapshot.get("strategy_type", ""),
            "status": snapshot.get("status", "empty"),
            "evidence_count": snapshot.get("evidence_count", 0),
            "human_review_required": bool(snapshot.get("human_review", {}).get("required", False)),
            "saved_at": snapshot.get("saved_at"),
        }

    @staticmethod
    def _evidence_summary(sources: object) -> list[dict[str, object]]:
        if not isinstance(sources, list):
            return []
        result = []
        for item in sources:
            if not isinstance(item, dict):
                continue
            result.append({
                "evidence_id": str(item.get("evidence_id") or item.get("chunk_id") or ""),
                "paper_id": str(item.get("paper_id", "")),
                "source": str(item.get("paper_title") or item.get("source") or ""),
                "chapter": str(item.get("section") or item.get("chapter") or ""),
                "agent": "Research Master",
                "score": item.get("score"),
            })
        return result

    @staticmethod
    def _subtask_summary(item: dict[str, object]) -> dict[str, object]:
        refs = item.get("evidence_refs", [])
        return {
            "subtask_id": item.get("subtask_id", ""), "title": item.get("title", ""),
            "status": item.get("status", ""), "evidence_count": len(refs) if isinstance(refs, list) else 0,
            "evidence_refs": list(refs) if isinstance(refs, list) else [],
            "decision": item.get("decision", ""),
            "conflict_status": item.get("conflict_status", ""),
            "expected_evidence": item.get("expected_evidence", ""), "purpose": item.get("purpose", ""),
        }

    @staticmethod
    def _safe_strategy(strategy: dict[str, object]) -> dict[str, object]:
        allowed = {"strategy_type", "research_objective", "subtasks", "reasoning_basis", "expected_evidence", "stop_condition"}
        return {key: value for key, value in strategy.items() if key in allowed}

    @staticmethod
    def _conflict_summary(conflict: dict[str, object]) -> dict[str, object]:
        claim_pairs = []
        for item in conflict.get("conflicts", []) if isinstance(conflict.get("conflicts"), list) else []:
            if not isinstance(item, dict):
                continue
            claims = item.get("normalized_claims", [])
            if isinstance(claims, list):
                claim_pairs.append({
                    "claims": [{key: claim.get(key, "") for key in ("evidence_id", "subject", "property", "claim_direction", "condition", "scope")} for claim in claims if isinstance(claim, dict)],
                    "reason": item.get("reason", ""),
                })
        return {
            "status": conflict.get("status", "not_observed"),
            "requires_human_review": bool(conflict.get("requires_human_review", False)),
            "count": int(conflict.get("count", len(conflict.get("conflicts", [])) if isinstance(conflict.get("conflicts"), list) else 0)),
            "claim_pairs": claim_pairs,
        }

    @staticmethod
    def _deliverable_summary(result: dict[str, object], evidence: list[dict[str, object]]) -> list[dict[str, object]]:
        report = result.get("report", {})
        return [{
            "type": "research_decision_report", "title": "Research Master 科研决策辅助结果",
            "status": "available" if report else "not_generated", "evidence_count": len(evidence),
        }]

    @staticmethod
    def _final_outcome_summary(result: dict[str, object]) -> dict[str, object]:
        return {"executive_summary": str(result.get("executive_summary", "")), "boundary_note": str(result.get("boundary_note", ""))}

    @staticmethod
    def _unresolved_questions(finite: dict[str, object], review: bool) -> list[str]:
        gaps = list(finite.get("research_gaps", [])) if isinstance(finite.get("research_gaps"), list) else []
        if review:
            gaps.append("存在需要科研负责人核验的 Evidence 条件差异或潜在冲突。")
        if not gaps and finite.get("stop_reason") not in {"SUFFICIENT_EVIDENCE", "TASK_COMPLETED"}:
            gaps.append(f"当前任务以 {finite.get('stop_reason')} 停止，建议补充资料或人工核验。")
        return list(dict.fromkeys(str(item) for item in gaps if item))

    @staticmethod
    def _workspace_title(goal: str) -> str:
        compact = " ".join(goal.split())
        return f"Research Workspace · {compact[:110]}"

    @staticmethod
    def _workspace_identity(workspace: ResearchWorkspace) -> dict[str, object]:
        return {"workspace_id": workspace.id, "title": workspace.name, "created_at": workspace.created_at.isoformat() if workspace.created_at else ""}

    @classmethod
    def _scope(cls, workspace_id: str) -> str:
        return f"{cls.MEMORY_PREFIX}{workspace_id}"

    @staticmethod
    def _require_workspace(session: Any, workspace_id: str) -> ResearchWorkspace:
        workspace = session.get(ResearchWorkspace, workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError("未找到指定的 Research Workspace。")
        return workspace

    @staticmethod
    def _level(value: int, *, good: int, excellent: int) -> str:
        if value >= excellent: return "excellent"
        if value >= good: return "good"
        if value > 0: return "limited"
        return "not_available"

    @staticmethod
    def _score_level(value: float) -> str:
        if value >= 0.8: return "strong"
        if value >= 0.6: return "moderate"
        return "limited"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _decode_snapshot(value: str) -> dict[str, object]:
        try:
            parsed = json.loads(value or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _ensure_product_fields(
        self, workspace: ResearchWorkspace, snapshot: dict[str, object]
    ) -> dict[str, object]:
        """Read old P3 snapshots safely without migrating their stored JSON."""
        normalized = dict(snapshot)
        evidence = list(normalized.get("evidence_summary", []))
        review_required = bool(normalized.get("human_review", {}).get("required", False))
        normalized.setdefault("members", self._default_members(workspace.id))
        normalized.setdefault("workflow", self._workflow_state(len(evidence), review_required))
        normalized.setdefault("review_items", self._review_items(evidence, {}))
        normalized.setdefault("evidence_graph", self._evidence_graph(evidence, {}))
        normalized.setdefault("decisions", [])
        normalized.setdefault("deliverables", [])
        return normalized

    @staticmethod
    def _default_members(workspace_id: str) -> list[dict[str, object]]:
        return [
            {"workspace_id": workspace_id, "user_role": "Researcher", "role_type": "researcher", "permissions": ["upload_material", "start_research", "view_evidence"]},
            {"workspace_id": workspace_id, "user_role": "Reviewer", "role_type": "reviewer", "permissions": ["view_evidence", "mark_review", "approve_decision", "reject_decision"]},
            {"workspace_id": workspace_id, "user_role": "Leader", "role_type": "leader", "permissions": ["view_progress", "view_deliverable", "view_research_quality"]},
        ]

    @staticmethod
    def _workflow_state(evidence_count: int, review_required: bool) -> dict[str, object]:
        if evidence_count <= 0:
            current, reason = "needs_data", "Evidence Collection requires at least one traceable Evidence."
        else:
            current, reason = "evidence_review", "Evidence exists and requires human review before a decision can proceed."
        return {
            "current_state": current,
            "history": ["created", "research_planning", "evidence_collection", current],
            "state_requirements": {
                "evidence_review": "evidence_count > 0",
                "decision_pending": "requires_human_review = true or evidence-backed decision awaits a reviewer",
                "deliverable_draft": "at least one review item is approved and an evidence-grounded draft exists",
                "completed": "Leader confirms a reviewed deliverable; no formal Action is auto-created",
            },
            "reason": reason,
        }

    @staticmethod
    def _review_items(sources: list[dict[str, object]], conflict: dict[str, object]) -> list[dict[str, object]]:
        if not sources:
            return []
        statement = (
            "当前 Evidence 存在条件差异或潜在冲突，请审核后决定是否继续研究。"
            if conflict.get("requires_human_review") else
            "请确认当前 Evidence 是否足以支持该待确认研究判断。"
        )
        return [{
            "id": "review_evidence_support", "type": "evidence_support_review", "evidence_refs": sources,
            "statement": statement, "status": "pending", "reviewer_note": "", "reviewer_role": "",
        }]

    @staticmethod
    def _evidence_graph(sources: list[dict[str, object]], conflict: dict[str, object]) -> dict[str, object]:
        nodes = []
        edges = []
        for source in sources:
            paper_id = str(source.get("paper_id", ""))
            evidence_id = str(source.get("evidence_id", ""))
            if paper_id:
                nodes.append({"id": f"paper:{paper_id}", "type": "paper", "label": source.get("source", "未命名资料")})
            if evidence_id:
                nodes.append({"id": f"evidence:{evidence_id}", "type": "evidence", "label": source.get("chapter", "正文")})
                if paper_id:
                    edges.append({"from": f"paper:{paper_id}", "to": f"evidence:{evidence_id}", "relation": "contains"})
        for pair in conflict.get("conflicts", []) if isinstance(conflict.get("conflicts"), list) else []:
            if not isinstance(pair, dict):
                continue
            for claim in pair.get("normalized_claims", []) if isinstance(pair.get("normalized_claims"), list) else []:
                if not isinstance(claim, dict) or not claim.get("evidence_id"):
                    continue
                claim_id = f"claim:{claim['evidence_id']}:{claim.get('claim_direction', 'unknown')}"
                label = " · ".join(str(claim.get(key, "")) for key in ("subject", "property", "claim_direction") if claim.get(key))
                nodes.append({"id": claim_id, "type": "claim", "label": label or "未完整提取的 Claim"})
                edges.append({"from": f"evidence:{claim['evidence_id']}", "to": claim_id, "relation": "supports"})
        nodes.extend([
            {"id": "decision:pending", "type": "decision", "label": "待确认研究判断"},
            {"id": "deliverable:research_brief", "type": "deliverable", "label": "Research Brief 草案"},
        ])
        for source in sources:
            if source.get("evidence_id"):
                edges.append({"from": f"evidence:{source['evidence_id']}", "to": "decision:pending", "relation": "grounds"})
        edges.append({"from": "decision:pending", "to": "deliverable:research_brief", "relation": "informs"})
        return {"nodes": nodes, "edges": edges, "boundary": "图谱只展示真实 Evidence、确定性 Claim 提取结果与待确认关系；没有可提取 Claim 时不会伪造 Claim 节点。"}
