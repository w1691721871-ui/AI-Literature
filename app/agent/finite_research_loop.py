"""Bounded, evidence-driven subtask execution for ResearchOS P2.

The loop deliberately contains no retrieval, embedding, reranking, or model
implementation.  It coordinates the existing services and records only
user-readable execution facts, never prompts or hidden reasoning.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.agent.research_result_evaluator import ResearchResultEvaluator
from app.services.agent_trace_service import AgentTraceService
from app.services.evidence_conflict_service import detect_evidence_conflicts
from app.services.evidence_claim_service import extract_evidence_claims
from app.services.evidence_pair_service import plan_complementary_retrieval
from app.services.evidence_validation_service import validate_evidence_grounding
from app.services.query_service import rewrite_query
from app.services.retrieval_service import RetrievalService
from app.agent.research_strategy_planner import ResearchStrategyPlanner


class FiniteResearchLoop:
    """Execute a small, finite set of independently evidenced subtasks."""

    MAX_SUBTASKS = 3
    # Keep one bounded slot for evidence-driven adjustment.  The Strategy
    # Planner can describe three user-facing research dimensions, while the
    # first execution pass starts with two and reserves capacity for a real
    # Evidence gap rather than consuming the whole loop on a fixed template.
    INITIAL_EXECUTION_SUBTASKS = 2
    MAX_RETRIEVAL_ROUNDS = 3
    MAX_STEPS = 12
    # Query rewrite calls plus one final synthesis performed by Research Master.
    MAX_MODEL_CALLS = 4
    MAX_COMPLEMENTARY_RETRIEVAL = 1
    # A source can be traceable yet irrelevant to the user's goal.  Keep the
    # finite-loop sufficiency check conservative so it cannot promote an
    # unrelated top-k result into a research conclusion.
    MIN_AVERAGE_RELEVANCE = 0.50

    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        evaluator: ResearchResultEvaluator | None = None,
        *,
        query_rewriter: Callable[[str], str] = rewrite_query,
        evidence_validator: Callable[[list[dict[str, object]], str], dict[str, object]] | None = None,
        conflict_detector: Callable[[list[dict[str, object]]], dict[str, object]] = detect_evidence_conflicts,
        evidence_pair_planner: Callable[[list[dict[str, object]], set[str] | None], dict[str, str] | None] = plan_complementary_retrieval,
        strategy_planner: ResearchStrategyPlanner | None = None,
        trace_service: AgentTraceService | None = None,
    ) -> None:
        self._retrieval = retrieval_service or RetrievalService()
        self._evaluator = evaluator or ResearchResultEvaluator()
        self._query_rewriter = query_rewriter
        self._evidence_validator = evidence_validator or validate_evidence_grounding
        self._conflict_detector = conflict_detector
        self._evidence_pair_planner = evidence_pair_planner
        self._strategy_planner = strategy_planner or ResearchStrategyPlanner()
        self._trace_service = trace_service

    def execute(
        self,
        goal: str,
        task_understanding: dict[str, object],
        paper_ids: list[str] | None = None,
        run_context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Run independently retrieved subtasks until a finite stop condition.

        This method does not synthesize a scientific conclusion.  It returns a
        verified process record for ResearchMasterAgent's existing final Qwen
        synthesis step.
        """
        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("请输入需要完成的科研任务。")

        trace_id = self._trace_service.create_trace_id() if self._trace_service else ""
        timeline: list[dict[str, object]] = []
        self._event(timeline, trace_id, phase="task_understanding", message="已理解研究目标并确认需要可追溯资料依据。")

        strategy = self._strategy_planner.plan(normalized_goal, task_understanding)
        queue = self._initial_subtasks(strategy)
        subtasks: list[dict[str, object]] = []
        seen_evidence_ids: set[str] = set()
        seen_questions: set[str] = set()
        retrieval_rounds = 0
        complementary_retrievals = 0
        context = run_context if run_context is not None else self.new_run_context()
        steps = 2
        requires_human_review = False
        stop_reason = "TASK_COMPLETED"

        self._event(
            timeline,
            trace_id,
            phase="strategy_planning",
            strategy_type=str(strategy["strategy_type"]),
            message=f"已选择 {strategy['strategy_type']} 研究策略并生成 {len(queue)} 个待执行研究子任务。",
        )
        self._event(timeline, trace_id, phase="planning", message=f"已生成 {len(queue)} 个待执行研究子任务。")

        while queue:
            if len(subtasks) >= self.MAX_SUBTASKS:
                stop_reason = "MAX_SUBTASKS_REACHED"
                break
            if retrieval_rounds >= self.MAX_RETRIEVAL_ROUNDS:
                stop_reason = "MAX_RETRIEVAL_ROUNDS_REACHED"
                break
            if steps >= self.MAX_STEPS:
                stop_reason = "MAX_STEPS_REACHED"
                break
            # Reserve one model call for final synthesis.
            # Reserve one shared call for Research Master's final synthesis.
            if not self.can_consume_model_call(context, reserve_final_synthesis=True):
                stop_reason = "MAX_MODEL_CALLS_REACHED"
                break

            subtask = queue.pop(0)
            question = str(subtask["research_question"])
            normalized_question = self._normalize_question(question)
            if normalized_question in seen_questions:
                stop_reason = "NO_NEW_EVIDENCE"
                break
            seen_questions.add(normalized_question)

            retrieval_rounds += 1
            subtask["status"] = "running"
            subtask["retrieval_round"] = retrieval_rounds
            self._event(
                timeline,
                trace_id,
                phase="subtask",
                subtask_id=str(subtask["subtask_id"]),
                retrieval_round=retrieval_rounds,
                message=f"开始执行：{subtask['title']}。",
            )

            self.consume_model_call(context)
            query = self._query_rewriter(question).strip() or question
            subtask["retrieval_query"] = query[:300]
            steps += 1
            self._event(
                timeline,
                trace_id,
                phase="query_rewrite",
                subtask_id=str(subtask["subtask_id"]),
                retrieval_round=retrieval_rounds,
                tool="Query Rewrite",
                message="已生成本子任务的检索查询。",
            )

            sources = self._retrieval.retrieve(query, paper_ids, top_k=5)
            initial_round = retrieval_rounds
            steps += 1
            self._event(
                timeline,
                trace_id,
                phase="retrieval",
                subtask_id=str(subtask["subtask_id"]),
                retrieval_round=initial_round,
                tool="RetrievalService",
                evidence_count=len(sources),
                message=f"已完成独立检索与重排，获得 {len(sources)} 条候选 Evidence。",
            )
            complementary_plan = None
            if (
                sources
                and complementary_retrievals < self.MAX_COMPLEMENTARY_RETRIEVAL
                and retrieval_rounds < self.MAX_RETRIEVAL_ROUNDS
            ):
                claims = [
                    claim
                    for source in sources
                    for claim in extract_evidence_claims(source)
                ]
                complementary_plan = self._evidence_pair_planner(
                    claims,
                    seen_questions | {self._normalize_question(query)},
                )
                if complementary_plan:
                    complementary_retrievals += 1
                    retrieval_rounds += 1
                    steps += 1
                    complementary_query = str(complementary_plan["query"])
                    complementary_sources = self._retrieval.retrieve(
                        complementary_query, paper_ids, top_k=5
                    )
                    source_ids = {
                        self._evidence_ref(item)["evidence_id"] for item in sources
                    }
                    additions = [
                        item for item in complementary_sources
                        if self._evidence_ref(item)["evidence_id"] not in source_ids
                    ]
                    sources.extend(additions)
                    subtask["complementary_retrieval"] = {
                        "reason": str(complementary_plan["reason"]),
                        "source_claim": str(complementary_plan["source_claim"]),
                        "query": complementary_query[:300],
                        "evidence_count": len(additions),
                    }
                    self._event(
                        timeline,
                        trace_id,
                        phase="complementary_retrieval",
                        subtask_id=str(subtask["subtask_id"]),
                        retrieval_round=retrieval_rounds,
                        tool="RetrievalService",
                        evidence_count=len(additions),
                        reason=str(complementary_plan["reason"]),
                        source_claim=str(complementary_plan["source_claim"])[:180],
                        query=complementary_query[:300],
                        message=f"已基于现有 Claim 补充检索 {len(additions)} 条可能的条件差异 Evidence。",
                    )
            evidence_refs = [self._evidence_ref(source) for source in sources]
            current_ids = {str(item["evidence_id"]) for item in evidence_refs if item["evidence_id"]}
            new_ids = current_ids - seen_evidence_ids

            if sources and not new_ids:
                subtask.update({
                    "status": "stopped",
                    "_sources": sources,
                    "evidence_refs": evidence_refs,
                    "evidence_count": len(evidence_refs),
                    "validation": self._evidence_validator(sources, ""),
                    "conflict_report": self._conflict_detector(sources),
                    "intermediate_result": "本轮未获得新的稳定 Evidence 标识，停止重复检索。",
                    "decision": self._decision("stop", "NO_NEW_EVIDENCE", "本轮资料与已使用 Evidence 完全重复。", [], False),
                })
                subtasks.append(subtask)
                self._event(
                    timeline, trace_id, phase="intermediate_decision", subtask_id=str(subtask["subtask_id"]),
                    retrieval_round=retrieval_rounds, evidence_count=len(evidence_refs), decision="stop",
                    stop_reason="NO_NEW_EVIDENCE", message="未检索到新的 Evidence，停止重复搜索。",
                )
                stop_reason = "NO_NEW_EVIDENCE"
                break

            validation = self._evidence_validator(sources, "")
            conflict_report = self._conflict_detector(sources)
            conflict_status = str(conflict_report.get("status", "insufficient_evidence"))
            requires_human_review = requires_human_review or bool(conflict_report.get("requires_human_review", False))
            seen_evidence_ids.update(current_ids)
            self._event(
                timeline, trace_id, phase="evidence_validation", subtask_id=str(subtask["subtask_id"]),
                retrieval_round=retrieval_rounds, evidence_count=len(evidence_refs),
                validation_status=str(validation.get("status", "")),
                message=str(validation.get("message", "已完成 Evidence 完整性检查。")),
            )
            self._event(
                timeline, trace_id, phase="conflict_check", subtask_id=str(subtask["subtask_id"]),
                retrieval_round=retrieval_rounds, evidence_count=len(evidence_refs), conflict_status=conflict_status,
                message=self._conflict_message(conflict_status),
            )

            evaluation = self._evaluator.evaluate(sources, [], bool(sources), goal)
            has_valid_evidence = bool(validation.get("valid_source_count", 0))
            average_relevance = float(validation.get("average_relevance", 0) or 0)
            relevance_sufficient = average_relevance >= self.MIN_AVERAGE_RELEVANCE
            evaluator_missing = [str(item) for item in evaluation.get("missing_evidence", []) if str(item).strip()]
            missing = evaluator_missing or (
                [] if has_valid_evidence and relevance_sufficient else [
                    "需要与当前研究目标相关且可追溯的 Evidence；当前候选资料相关度不足。"
                ]
            )
            evidence_sufficient = (
                bool(evaluation.get("sufficient", False))
                and has_valid_evidence
                and relevance_sufficient
            )
            paired_condition_difference = (
                complementary_plan is not None
                and conflict_status in {"potential_conflict", "context_difference"}
            )
            if paired_condition_difference:
                decision = self._decision(
                    "sufficient",
                    "NEEDS_HUMAN_REVIEW",
                    "已获得方向不同且条件可区分的 Evidence，需人工核验后再形成科研结论。",
                    [],
                    bool(new_ids),
                )
                subtask["status"] = "completed"
                intermediate = "已获得可追溯的条件差异 Evidence，不能自动裁决，需人工复核。"
            elif evidence_sufficient:
                decision = self._decision("sufficient", "SUFFICIENT_EVIDENCE", "本子任务已获得可追溯 Evidence，可继续下一个必要子任务。", missing, bool(new_ids))
                subtask["status"] = "completed"
                intermediate = "已获得可追溯资料；结论仍需人工复核。"
            else:
                replan_already_queued = any(item.get("title") == "补充证据检索" for item in queue)
                can_enqueue_replan = (
                    not replan_already_queued
                    and len(subtasks) + len(queue) < self.MAX_SUBTASKS
                    and retrieval_rounds < self.MAX_RETRIEVAL_ROUNDS
                )
                can_replan = can_enqueue_replan or (
                    replan_already_queued and retrieval_rounds < self.MAX_RETRIEVAL_ROUNDS
                )
                decision = self._decision(
                    "need_more_evidence" if can_replan else "stop",
                    "INSUFFICIENT_EVIDENCE" if not can_replan else "NEED_MORE_EVIDENCE",
                    "本子任务缺少可追溯 Evidence。" if not can_replan else "本子任务资料不足，将执行一个不同的补充检索任务。",
                    missing,
                    bool(new_ids),
                )
                subtask["status"] = "needs_evidence" if can_replan else "stopped"
                intermediate = "暂无可验证资料，不能形成科研结论。"
                if can_enqueue_replan:
                    replanned = self._replan_subtask(
                        normalized_goal,
                        question,
                        missing,
                        # The next normal subtask remains in ``queue`` after
                        # popping the current one, so reserve one additional
                        # position to keep every execution trace ID unique.
                        len(subtasks) + len(queue) + 2,
                        str(subtask["subtask_id"]),
                        task_understanding,
                    )
                    if self._normalize_question(replanned["research_question"]) not in seen_questions:
                        queue.append(replanned)
                    else:
                        decision = self._decision("stop", "NO_NEW_EVIDENCE", "补充问题与已执行问题重复，停止重复检索。", missing, False)
                        subtask["status"] = "stopped"

            subtask.update({
                # Internal only: removed from the public subtask record below.
                "_sources": sources,
                "evidence_refs": evidence_refs,
                "evidence_count": len(evidence_refs),
                "validation": validation,
                "conflict_report": conflict_report,
                "intermediate_result": intermediate,
                "decision": decision,
                "evaluation": {
                    "has_evidence": evaluation["has_evidence"],
                    "source_integrity": evaluation["source_integrity"],
                    "needs_more_retrieval": evaluation["needs_more_retrieval"],
                },
            })
            subtasks.append(subtask)
            self._event(
                timeline, trace_id, phase="intermediate_decision", subtask_id=str(subtask["subtask_id"]),
                retrieval_round=retrieval_rounds, evidence_count=len(evidence_refs),
                validation_status=str(validation.get("status", "")), conflict_status=conflict_status,
                decision=str(decision["status"]), stop_reason=str(decision["stop_reason"]),
                message=str(decision["reason"]),
            )

            if decision["status"] == "stop":
                stop_reason = str(decision["stop_reason"])
                break
            if decision["stop_reason"] == "NEEDS_HUMAN_REVIEW":
                # A complementary pair directly addresses the core claim but
                # exposes a condition-qualified difference.  Do not spend the
                # remaining budget on duplicate broad retrievals; preserve the
                # pair for a human-reviewed final synthesis instead.
                stop_reason = "NEEDS_HUMAN_REVIEW"
                break

        if stop_reason == "TASK_COMPLETED":
            if not subtasks or not any(item.get("evidence_count", 0) for item in subtasks):
                stop_reason = "INSUFFICIENT_EVIDENCE"
            elif self._has_unresolved_evidence_gap(subtasks):
                stop_reason = "INSUFFICIENT_EVIDENCE"
            elif any(
                str(item.get("conflict_report", {}).get("status"))
                in {"potential_conflict", "context_difference"}
                for item in subtasks
            ):
                stop_reason = "NEEDS_HUMAN_REVIEW"
            else:
                stop_reason = "SUFFICIENT_EVIDENCE"

        all_sources = self._deduplicate_sources(subtasks)
        for subtask in subtasks:
            subtask.pop("_sources", None)
        self._event(
            timeline, trace_id, phase="loop_completion", evidence_count=len(all_sources),
            decision="final" if all_sources else "stop", stop_reason=stop_reason,
            message=f"有限研究循环结束：{stop_reason}。",
        )
        return {
            "trace_id": trace_id,
            "strategy": strategy,
            "subtasks": subtasks,
            "execution_timeline": timeline,
            "sources": all_sources,
            "stop_reason": stop_reason,
            "status": "completed" if stop_reason == "SUFFICIENT_EVIDENCE" else "stopped",
            "retrieval_rounds": retrieval_rounds,
            "steps": steps,
            "model_calls": int(context["model_calls"]),
            "max_model_calls": int(context["max_model_calls"]),
            "evidence_count": len(all_sources),
            "requires_human_review": requires_human_review or stop_reason == "NEEDS_HUMAN_REVIEW",
        }

    def _initial_subtasks(self, strategy: dict[str, object]) -> list[dict[str, object]]:
        """Translate the Strategy Planner's public plan into executable work."""
        subtasks: list[dict[str, object]] = []
        initial_limit = min(self.INITIAL_EXECUTION_SUBTASKS, self.MAX_SUBTASKS)
        for index, item in enumerate(strategy.get("subtasks", [])[:initial_limit]):
            if not isinstance(item, dict):
                continue
            subtask = self._subtask(
                index + 1,
                str(item.get("title", "研究资料检索")),
                str(item.get("research_question", "")),
            )
            subtask["expected_evidence"] = str(item.get("expected_evidence", ""))
            subtask["purpose"] = str(item.get("purpose", ""))
            subtasks.append(subtask)
        return subtasks

    @staticmethod
    def _subtask(index: int, title: str, question: str) -> dict[str, object]:
        return {
            "subtask_id": f"subtask_{index}",
            "title": title,
            "research_question": question,
            "status": "pending",
            "retrieval_round": 0,
            "evidence_refs": [],
            "evidence_count": 0,
            "intermediate_result": None,
            "decision": None,
        }

    def _replan_subtask(
        self,
        goal: str,
        prior_question: str,
        missing_evidence: list[str],
        index: int,
        parent_subtask_id: str,
        task_understanding: dict[str, object],
    ) -> dict[str, object]:
        adjustment = self._strategy_planner.replan(
            goal, prior_question, missing_evidence, task_understanding
        )
        replanned = self._subtask(index, adjustment["title"], adjustment["research_question"])
        replanned["expected_evidence"] = adjustment["expected_evidence"]
        replanned["purpose"] = adjustment["purpose"]
        replanned["replan_for"] = parent_subtask_id
        return replanned

    @staticmethod
    def _has_unresolved_evidence_gap(subtasks: list[dict[str, object]]) -> bool:
        """Require a successful, executed replan before treating a gap as closed."""
        for subtask in subtasks:
            decision = subtask.get("decision")
            if not isinstance(decision, dict) or decision.get("status") != "need_more_evidence":
                continue
            subtask_id = str(subtask.get("subtask_id", ""))
            resolved = any(
                candidate.get("replan_for") == subtask_id
                and isinstance(candidate.get("decision"), dict)
                and candidate["decision"].get("status") == "sufficient"
                for candidate in subtasks
            )
            if not resolved:
                return True
        return False

    def new_run_context(self) -> dict[str, object]:
        """Create the small shared budget context for one research run."""
        return {"model_calls": 0, "max_model_calls": self.MAX_MODEL_CALLS}

    @staticmethod
    def can_consume_model_call(context: dict[str, object], *, reserve_final_synthesis: bool = False) -> bool:
        limit = int(context.get("max_model_calls", 0))
        used = int(context.get("model_calls", 0))
        reserved = 1 if reserve_final_synthesis else 0
        return used < limit - reserved

    @staticmethod
    def consume_model_call(context: dict[str, object]) -> None:
        if not FiniteResearchLoop.can_consume_model_call(context):
            raise RuntimeError("MAX_MODEL_CALLS_REACHED")
        context["model_calls"] = int(context.get("model_calls", 0)) + 1

    def _event(self, timeline: list[dict[str, object]], trace_id: str, *, phase: str, message: str, **details: object) -> None:
        event: dict[str, object] = {
            "phase": phase,
            "message": message,
            "subtask_id": "",
            "retrieval_round": 0,
            "tool": "",
            "evidence_count": 0,
            "validation_status": "",
            "conflict_status": "",
            "decision": "",
            "stop_reason": "",
            **{key: value for key, value in details.items() if value not in ("", None)},
        }
        timeline.append(event)
        if self._trace_service and trace_id:
            self._trace_service.record(trace_id, phase, message)

    @staticmethod
    def _evidence_ref(source: dict[str, object]) -> dict[str, object]:
        paper_id = str(source.get("paper_id", "")).strip()
        chunk_id = str(source.get("chunk_id", "")).strip()
        return {
            "evidence_id": f"{paper_id}:{chunk_id}" if paper_id and chunk_id else paper_id,
            "paper_id": paper_id,
            "chunk_id": chunk_id,
            "source": str(source.get("filename") or source.get("paper_title") or "未命名资料"),
            "section": str(source.get("section") or "正文"),
            "score": round(float(source.get("score", source.get("hybrid_score", 0)) or 0), 4),
        }

    @staticmethod
    def _decision(status: str, stop_reason: str, reason: str, missing_evidence: list[str], new_evidence: bool) -> dict[str, object]:
        return {
            "status": status,
            "stop_reason": stop_reason,
            "reason": reason,
            "missing_evidence": missing_evidence,
            "new_evidence": new_evidence,
        }

    @staticmethod
    def _normalize_question(value: str) -> str:
        return "".join(value.lower().split())

    @staticmethod
    def _conflict_message(status: str) -> str:
        return {
            "potential_conflict": "发现潜在资料结论差异，已保留给人工复核。",
            "context_difference": "发现可能由不同研究条件引起的差异，不能直接横向比较。",
            "insufficient_evidence": "可比较 Evidence 不足，无法完成冲突判断。",
        }.get(status, "当前规则未发现明显冲突；不代表所有研究结论一致。")

    @staticmethod
    def _deduplicate_sources(subtasks: list[dict[str, object]]) -> list[dict[str, object]]:
        sources: list[dict[str, object]] = []
        seen: set[str] = set()
        for subtask in subtasks:
            for source in subtask.get("_sources", []):
                key = f"{source.get('paper_id', '')}:{source.get('chunk_id', '')}"
                if key not in seen:
                    seen.add(key)
                    sources.append(source)
        return sources
