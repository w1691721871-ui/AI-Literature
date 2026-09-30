"""Evidence-bounded proactive suggestions for existing Research Workspaces."""
from __future__ import annotations
import re
from collections import Counter
from sqlalchemy import select
from app.models.paper import Paper
from app.services.database import SessionLocal
from app.services.research_workspace_intelligence_service import ResearchWorkspaceIntelligenceService

class ResearchCopilotService:
    """Reads actual Workspace state; suggestions never execute themselves."""
    def __init__(self, workspace_service=None, session_factory=SessionLocal):
        self._workspaces = workspace_service or ResearchWorkspaceIntelligenceService()
        self._sessions = session_factory
    def intelligence(self, workspace_id: str) -> dict[str, object]:
        snapshot = self._workspaces.get_workspace(workspace_id)
        evidence = list(snapshot.get("evidence_summary", []))
        coverage = self._coverage(evidence)
        return {"workspace_id": workspace_id, "research_goal": snapshot.get("research_goal",""), "evidence_intelligence": coverage, "research_readiness": self._readiness(snapshot, coverage), "follow_up_suggestions": self._suggestions(snapshot, coverage), "boundary": "Copilot 仅根据当前 Workspace、论文元数据与 Evidence 引用建议；不会自动执行、导入资料或形成科研结论。"}
    def _coverage(self, evidence):
        ids = {str(x.get("paper_id","")) for x in evidence if x.get("paper_id")}
        sections = {str(x.get("chapter","")) for x in evidence if x.get("chapter")}
        papers = self._papers(ids); types = Counter(str(x.get("document_type","paper")) for x in papers)
        years = sorted({y for p in papers for y in re.findall(r"\b(?:19|20)\d{2}\b", str(p["title"]))})
        terms=[]
        for x in evidence: terms += [t for t in re.split(r"[^\w\u4e00-\u9fff]+", str(x.get("source",""))) if len(t)>=3 and not t.isdigit()]
        gaps=[]
        if not evidence: gaps.append("当前 Workspace 没有可验证 Evidence，不能形成研究建议。")
        if 0 < len(ids) < 3: gaps.append("当前 Evidence 来源少于 3 篇资料，方法或条件比较覆盖有限。")
        if not years: gaps.append("当前论文元数据未提供可识别发表年份，无法评估年份覆盖。")
        if types and not any(k in types for k in ("patent","experiment_report","project")): gaps.append("当前引用资料未覆盖专利、实验报告或项目资料类型。")
        return {"evidence_count":len(evidence),"topic_coverage":[t for t,_ in Counter(terms).most_common(8)],"method_coverage":sorted(sections),"source_diversity":len(ids),"dataset_coverage":"not_available","year_coverage":years or "not_available","document_type_coverage":dict(types),"evidence_gaps":gaps,"support_note":"覆盖范围来自已引用 Evidence 与论文元数据；缺少元数据时标记 not_available，不推断科研事实。"}
    @staticmethod
    def _readiness(snapshot, coverage):
        n=int(coverage["evidence_count"]); d=int(coverage["source_diversity"]); review=bool(snapshot.get("human_review",{}).get("required",False)); conflict=dict(snapshot.get("conflict_report",{}))
        dims={"evidence_coverage":min(100,round(n/6*100)),"source_diversity":min(100,round(d/3*100)),"conflict_status":40 if conflict.get("requires_human_review") else (80 if n else 0),"review_status":40 if review else (80 if n else 0),"deliverable_completeness":100 if any(x.get("status")=="available" for x in snapshot.get("deliverables",[]) if isinstance(x,dict)) else 0}
        return {"score":round(sum(dims.values())/len(dims)),"label":"Research Ready","dimensions":dims,"boundary":"Research Readiness 是资料、审核与交付准备度，不是准确率或科研正确率。"}
    @staticmethod
    def _suggestions(snapshot, coverage):
        refs=list(snapshot.get("evidence_summary",[]))[:6]
        if not refs: return [{"title":"补充与当前目标相关的授权科研资料","rationale":"当前没有可验证 Evidence；系统不会生成科研结论。","evidence_refs":[],"type":"needs_data"}]
        items=[]
        if int(coverage["source_diversity"])<3: items.append({"title":"补充更多来源以完成方法或条件比较","rationale":"当前引用来源少于 3 篇，支持范围有限。","evidence_refs":refs,"type":"coverage_gap"})
        if snapshot.get("human_review",{}).get("required"): items.append({"title":"核验条件差异后再决定验证方向","rationale":"当前 Workspace 需要人工审核；系统不自动裁决证据差异。","evidence_refs":refs,"type":"human_review"})
        items.append({"title":"生成 Evidence-grounded 的后续验证计划草案","rationale":"已有可追溯 Evidence，可准备待审核的验证计划。","evidence_refs":refs,"type":"deliverable"})
        return items[:3]
    def _papers(self, ids):
        if not ids: return []
        s=self._sessions()
        try:
            return [{"title":x.title,"document_type":x.document_type} for x in s.scalars(select(Paper).where(Paper.paper_id.in_(ids))).all()]
        finally: s.close()
