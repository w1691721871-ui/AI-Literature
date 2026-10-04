"""Explainable P19 intelligence; deterministic and free of prompts/source text."""
from __future__ import annotations
import json
from sqlalchemy import select
from app.models.computer_activity_summary import ComputerActivitySummary
from app.models.computer_project_memory import ComputerProjectMemory
from app.services.database import SessionLocal, initialize_database

class ComputerIntelligenceService:
    def __init__(self, session_factory=SessionLocal, *, initialize=True):
        if initialize: initialize_database()
        self._session_factory=session_factory
    def activity(self, task_id, stage, title, description, status):
        s=self._session_factory()
        try:
            r=ComputerActivitySummary(task_id=task_id,stage=stage,title=title,description=description[:1200],status=status);s.add(r);s.commit();s.refresh(r);return self._activity(r)
        finally:s.close()
    def activities(self, task_id):
        s=self._session_factory()
        try:return [self._activity(r) for r in s.scalars(select(ComputerActivitySummary).where(ComputerActivitySummary.task_id==task_id).order_by(ComputerActivitySummary.created_at.asc())).all()]
        finally:s.close()
    def remember(self, workspace_id, memory_type, content):
        if memory_type not in {"PROJECT_STYLE","TECH_STACK","TEST_COMMAND","USER_PREFERENCE","TASK_EXPERIENCE","FAILURE_LEARNING"}: raise ValueError("不支持的项目记忆类型。")
        if any(word in content.lower() for word in ("token","password","secret",".env","api_key")): raise ValueError("禁止写入敏感或凭据类记忆。")
        s=self._session_factory()
        try:
            existing=s.scalar(select(ComputerProjectMemory).where(ComputerProjectMemory.workspace_id==workspace_id,ComputerProjectMemory.memory_type==memory_type,ComputerProjectMemory.content==content[:1000]).order_by(ComputerProjectMemory.created_at.desc()))
            if existing is not None: return self._memory(existing)
            r=ComputerProjectMemory(workspace_id=workspace_id,memory_type=memory_type,content=content[:1000]);s.add(r);s.commit();s.refresh(r);return self._memory(r)
        finally:s.close()
    def memories(self, workspace_id):
        s=self._session_factory()
        try:return [self._memory(r) for r in s.scalars(select(ComputerProjectMemory).where(ComputerProjectMemory.workspace_id==workspace_id).order_by(ComputerProjectMemory.created_at.desc())).all()]
        finally:s.close()
    @staticmethod
    def review(change):
        diff=str(change.get("diff", "")); risk="LOW" if len(diff)<800 else "MEDIUM"; issues=[]
        if "console.log" in diff: issues.append({"severity":"WARNING","message":"调试输出应在合并前复核。"})
        return {"status":"WARNING" if issues else "PASS","severity":risk,"issues":issues,"boundary":"基于 Diff 规则检查；不声称完成性能或安全证明。"}
    @staticmethod
    def verification_plan(changes):
        paths=[str(c.get("file_path","")) for c in changes]; steps=[]
        if any(p.endswith((".js",".vue")) for p in paths): steps.append({"verification_type":"syntax","command":"node --check frontend/app.js","reason":"前端 JavaScript 修改"})
        if any(p.endswith(".py") for p in paths): steps.append({"verification_type":"compile","command":"python -m compileall app","reason":"Python 修改"})
        if not steps: steps.append({"verification_type":"compile","command":"python -m compileall app","reason":"基础项目完整性检查"})
        return steps
    @staticmethod
    def diff_summary(changes):
        paths=[str(c.get("file_path","")) for c in changes]; lines=sum(str(c.get("diff","" )).count("\n") for c in changes)
        area="Frontend only" if paths and all(p.startswith("frontend/") for p in paths) else "Mixed workspace"
        return {"files_changed":len(paths),"changed_lines":lines,"impact":area,"risk":"LOW" if lines<800 else "MEDIUM","main_changes":[f"{p} · {c.get('operation')}" for p,c in zip(paths,changes)]}
    @staticmethod
    def skills(): return [{"name":"Code Optimization","tools":"Code Intelligence · Diff","risk":"MEDIUM"},{"name":"UI Refinement","tools":"Workspace Action Engine","risk":"MEDIUM"},{"name":"Research Writing","tools":"Evidence Document Tool","risk":"MEDIUM"},{"name":"Experiment Planning","tools":"Research Runtime","risk":"LOW"},{"name":"Document Generation","tools":"Document Tool","risk":"MEDIUM"},{"name":"Data Analysis","tools":"Data Tool","risk":"LOW"}]
    @staticmethod
    def _activity(r): return {"id":r.id,"task_id":r.task_id,"stage":r.stage,"title":r.title,"description":r.description,"status":r.status,"created_at":r.created_at}
    @staticmethod
    def _memory(r): return {"id":r.id,"workspace_id":r.workspace_id,"memory_type":r.memory_type,"content":r.content,"created_at":r.created_at}
