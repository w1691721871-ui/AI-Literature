"""On-demand, workspace-isolated research monitoring; never background polls."""
from __future__ import annotations
import json
from sqlalchemy import select
from app.models.research_monitoring import ResearchMonitoringTask
from app.services.database import SessionLocal, initialize_database
from app.services.research_query_planner import ResearchQueryPlanner

class ResearchMonitoringService:
 def __init__(self, sessions=SessionLocal, *, initialize=True):
  if initialize: initialize_database()
  self.s=sessions; self.planner=ResearchQueryPlanner()
 def create(self, workspace_id, topic, goal=""):
  if not workspace_id: raise PermissionError("A Workspace is required for research monitoring.")
  plan=self.planner.plan(topic); session=self.s()
  try:
   row=ResearchMonitoringTask(workspace_id=workspace_id,topic=topic[:500],goal=goal[:2000],keywords_json=json.dumps(plan["queries"]));session.add(row);session.commit();session.refresh(row);return self._data(row)
  finally: session.close()
 def detect_updates(self, monitor_id, workspace_id, approved_evidence):
  session=self.s()
  try:
   row=session.get(ResearchMonitoringTask,monitor_id)
   if not row or row.workspace_id!=workspace_id: raise PermissionError("Monitoring task is not available in this Workspace.")
   prior=set(json.loads(row.baseline_json or "[]")); current={str(x.get("source")) for x in approved_evidence if str(x.get("status")).upper() in {"APPROVED","VERIFIED"} and x.get("source")}; new=sorted(current-prior)
   row.baseline_json=json.dumps(sorted(current));session.commit()
   return {"monitor_id":row.id,"status":"UPDATE_CANDIDATE" if new else "NO_CHANGE","new_evidence_sources":new,"notification":"New approved Evidence may change this monitored topic." if new else "No new approved Evidence was detected.","boundary":"Detection runs only when explicitly requested and only over approved Workspace Evidence; it does not poll, infer conclusions, or create notifications automatically."}
  finally: session.close()
 @staticmethod
 def _data(row): return {"id":row.id,"workspace_id":row.workspace_id,"topic":row.topic,"goal":row.goal,"keywords":json.loads(row.keywords_json or "[]"),"status":row.status,"update_frequency":"ON_DEMAND","boundary":"No background polling or unbounded resource use."}
