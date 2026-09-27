"""Run a real-data acceptance check for the ResearchOS decision loop.

This script never uploads, creates, or fabricates research material.  It only
uses papers already uploaded by the user.  When the knowledge base is empty it
prints ``等待用户上传真实科研PDF`` and exits successfully.

The optional project/action/decision/outcome records are explicitly labelled as
temporary acceptance records and are deleted by default.  They prove API
linkage only; they are not scientific findings or actual project deliverables.

Usage (after uploading authorised PDFs):
    .venv\\Scripts\\python.exe scripts/e2e_researchos_test.py ^
      --question "请比较已上传论文中明确描述的研究方法差异" ^
      --goal "基于已上传资料梳理可进一步人工验证的研究方向" ^
      --decision "已采纳"
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    """Call the existing API using only the Python standard library."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed ({error.code}): {detail}") from error
    except URLError as error:
        raise RuntimeError(f"无法访问 ResearchOS 服务：{error.reason}") from error


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ResearchOS real-data E2E acceptance")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--question", help="由验收人员提供、针对已上传资料的真实科研问题")
    parser.add_argument("--goal", help="由验收人员提供的真实科研目标；省略时复用 question")
    parser.add_argument("--paper-id", action="append", dest="paper_ids", default=[], help="可重复指定，省略则使用所有已就绪资料")
    parser.add_argument(
        "--decision",
        choices=["待确认", "已采纳", "已修改", "已拒绝"],
        default="待确认",
        help="人工确认状态；默认仅创建待确认记录，不假定人工已采纳",
    )
    parser.add_argument("--decided-by", default="科研负责人", help="作出确认的实际人员角色")
    parser.add_argument("--keep-artifacts", action="store_true", help="保留明确标注为验收临时的项目、行动和成果记录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_id: str | None = None
    success = False

    health = request_json(args.base_url, "GET", "/health")
    require(health == {"status": "ok"}, "健康检查未返回预期状态。")
    print("PASS health")

    papers: list[dict[str, Any]] = request_json(args.base_url, "GET", "/research/papers")
    selected = [paper for paper in papers if not args.paper_ids or paper["paper_id"] in args.paper_ids]
    ready_papers = [paper for paper in selected if paper.get("quality_status") == "ready" and int(paper.get("chunk_count", 0)) > 0]
    if not ready_papers:
        print("等待用户上传真实科研PDF")
        return 0

    if not args.question:
        raise RuntimeError("检测到真实已索引资料；请通过 --question 提供真实科研问题后再继续验收。")
    goal = args.goal or args.question
    paper_ids = [paper["paper_id"] for paper in ready_papers]
    filename_by_paper_id = {paper["paper_id"]: paper.get("filename", paper.get("title", "")) for paper in ready_papers}
    print(f"PASS knowledge-base papers={len(ready_papers)} chunks={sum(int(paper.get('chunk_count', 0)) for paper in ready_papers)}")

    rag = request_json(args.base_url, "POST", "/research/questions", {"question": args.question, "paper_ids": paper_ids})
    sources: list[dict[str, Any]] = rag.get("sources", [])
    require(sources, "RAG 未返回真实资料依据；停止后续闭环，避免创建无依据行动。")
    for source in sources:
        require(all(key in source for key in ("paper_id", "paper_title", "section", "score")), "RAG 引用缺少 paper_id、来源、章节或相关性字段。")
        require(source["paper_id"] in filename_by_paper_id, "RAG 返回了不在本次资料范围内的来源。")
    print(f"PASS rag sources={len(sources)} confidence={rag.get('confidence', 'unknown')}")

    master = request_json(
        args.base_url,
        "POST",
        "/researchos/tasks/run",
        {
            "user_goal": goal,
            "selected_agents": ["literature", "knowledge", "innovation", "project"],
            "paper_ids": paper_ids,
        },
    )
    require(master.get("sources"), "Research Master 未返回知识库来源，停止后续闭环。")
    require(master.get("master_plan") and master.get("agent_runs"), "Research Master 未返回计划或 Agent 执行摘要。")
    print(f"PASS research-master sources={len(master['sources'])} agent-runs={len(master['agent_runs'])}")

    evidence_items = request_json(args.base_url, "GET", "/researchos/evidence")
    evidence_items = evidence_items.get("items", [])
    evidence_by_pointer = {f"{item.get('paper_id')}:{item.get('section', '正文')}" for item in evidence_items}

    evidence_refs = []
    for source in sources:
        evidence_id = f"{source['paper_id']}:{source['section']}"
        # The Evidence Center has no independent database ID.  This compact
        # pointer reuses its actual paper/section relation without copying text.
        require(evidence_id in evidence_by_pointer, "RAG 引用无法在现有 Evidence Center 中找到对应资料。")
        evidence_refs.append(
            {
                "evidence_id": evidence_id,
                "source": filename_by_paper_id[source["paper_id"]],
                "chapter": source["section"],
                "agent": "Knowledge Agent",
                "score": source["score"],
            }
        )
    print(f"PASS evidence-center linked={len(evidence_refs)}")

    try:
        project = request_json(
            args.base_url,
            "POST",
            "/researchos/projects",
            {
                "name": "验收临时项目（自动清理）",
                "enterprise_requirement": "",
                "research_goal": goal,
                "technology_route": "",
                "paper_plan": "",
                "patent_plan": "",
                "outcome_management": "",
                "status": "acceptance-test",
            },
        )
        project_id = project["id"]
        action = request_json(
            args.base_url,
            "POST",
            "/researchos/actions",
            {
                "project_id": project_id,
                "title": "基于本次真实资料分析结果的后续人工核验（验收临时）",
                "description": "仅验证 ResearchOS 可追溯决策闭环；不构成科研结论或实际执行任务。",
                "status": "待执行",
                "source_agent": "Research Master",
                "source_context": str(master.get("executive_summary", ""))[:4000] or "Research Master 已完成基于资料的任务输出。",
                "rationale": "该验收行动仅引用本次真实资料检索与 Research Master 输出，用于验证建议、依据、人工确认和成果追溯关系；任何科研执行仍须由负责人独立确认。",
                "evidence_refs": evidence_refs,
            },
        )
        require(action.get("evidence_refs") and action.get("rationale"), "Action 未保存 Evidence 引用或 rationale。")
        print(f"PASS action evidence-refs={len(action['evidence_refs'])}")

        decision = request_json(
            args.base_url,
            "POST",
            "/researchos/decisions",
            {"action_id": action["id"], "decision": args.decision, "decided_by": args.decided_by, "note": "验收记录：仅验证人工确认状态流转，不代表科研事实判断。"},
        )
        require(decision.get("decision") == args.decision, "Decision 状态未被正确保存。")
        print(f"PASS decision status={args.decision}")

        outcome = request_json(
            args.base_url,
            "POST",
            f"/researchos/projects/{project_id}/outcomes",
            {
                "outcome_type": "技术报告",
                "title": "验收临时成果记录（自动清理）",
                "status": "规划中",
                "description": "仅验证来源行动追溯字段，不代表已产生真实科研成果。",
                "source_action_id": action["id"],
            },
        )
        require(outcome.get("source_action_id") == action["id"], "Outcome 未正确关联来源 Action。")
        print("PASS project-outcome source-action linked")
        success = True
        print("PASS Paper -> Chunk -> RAG -> Agent -> Evidence -> Action -> Decision -> Project -> Outcome")
        return 0
    finally:
        if project_id and not args.keep_artifacts:
            request_json(args.base_url, "DELETE", f"/researchos/projects/{project_id}")
            print("CLEANUP temporary project/action/decision/outcome removed")
        elif project_id and success:
            print("NOTICE temporary acceptance artifacts kept by --keep-artifacts")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
