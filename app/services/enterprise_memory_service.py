"""P39 governed memory projections. Drafts never become reusable knowledge automatically."""
import json
from sqlalchemy import select
from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.models.agent_evaluation import AgentEvaluation
from app.models.benchmark import BenchmarkRun
from app.models.enterprise_memory import DecisionRecord,KnowledgeAsset
from app.services.database import SessionLocal,initialize_database
from app.services.governance_service import PermissionService
class MemoryError(ValueError):pass
class KnowledgeConfidenceService:
 @staticmethod
 def score(evidence,artifact,benchmark,approved,age_days=0):
  return max(0,min(100,round((35 if approved else 0)+min(25,evidence*5)+(15 if artifact else 0)+min(15,(benchmark or 0)*.15)+max(0,10-age_days*.03))))
class ExperienceRetriever:
 def __init__(self,sessions=SessionLocal):self.s=sessions
 def search(self,query,workspace_id=None):
  terms={x.lower() for x in query.split() if len(x)>2};s=self.s()
  try:
   rows=[]
   query_rows=select(KnowledgeAsset).where(KnowledgeAsset.status=="VERIFIED")
   if workspace_id:query_rows=query_rows.where(KnowledgeAsset.workspace_id==workspace_id)
   for x in s.scalars(query_rows).all():
    overlap=len(terms & {y.lower() for y in (x.title+" "+x.summary).split()});
    if overlap:rows.append((overlap,x))
   rows.sort(key=lambda item:(item[0],item[1].confidence),reverse=True)
   return [{"id":x.id,"title":x.title,"previous_solution":x.summary,"related_artifacts":json.loads(x.references_json or "[]"),"confidence":x.confidence} for _,x in rows[:5]]
  finally:s.close()
class DecisionMemoryService:
 def __init__(self,sessions=SessionLocal,*,initialize=True,permissions=None):
  if initialize:initialize_database()
  self.s=sessions;self.permissions=permissions or PermissionService(sessions,initialize=False);self.experiences=ExperienceRetriever(sessions)
 def extract(self,mission_id):
  s=self.s()
  try:
   old=s.scalar(select(DecisionRecord).where(DecisionRecord.mission_id==mission_id))
   if old:return self._decision(old)
   mission=s.get(AIMission,mission_id)
   if not mission or mission.status!="COMPLETED":raise MemoryError("Only completed Missions can create a draft decision record.")
   arts=list(s.scalars(select(Artifact).where(Artifact.mission_id==mission_id)).all());refs=self._array(mission.evidence_refs_json)
   row=DecisionRecord(mission_id=mission_id,workspace_id=mission.workspace_id,title=mission.title,problem_summary=mission.goal,decision_summary="AI-generated decision draft. Human review is required before it can become enterprise knowledge.",selected_solution="Review the evidence-backed delivery artifact and confirm the selected solution.",evidence_refs_json=json.dumps(refs),artifact_refs_json=json.dumps([x.id for x in arts]));s.add(row);s.commit();s.refresh(row);return self._decision(row)
  finally:s.close()
 def approve(self,decision_id,workspace_id,user_id):
  self.permissions.check(workspace_id,user_id,"ARTIFACT_REVIEW");s=self.s()
  try:
   row=s.get(DecisionRecord,decision_id)
   if not row:raise MemoryError("Decision not found.")
   if row.review_status=="APPROVED":return self._decision(row)
   refs=self._array(row.evidence_refs_json);artifact_ids=self._array(row.artifact_refs_json);benchmark=s.scalar(select(BenchmarkRun).where(BenchmarkRun.mission_id==row.mission_id).order_by(BenchmarkRun.created_at.desc()))
   confidence=KnowledgeConfidenceService.score(len(refs),bool(artifact_ids),benchmark.score if benchmark else None,True)
   if row.workspace_id and row.workspace_id!=workspace_id:raise MemoryError("Cross-workspace knowledge approval is not allowed.")
   # Legacy direct-service callers can retain their existing records. New API
   # calls are fail-closed by PermissionMiddleware before reaching here.
   asset=KnowledgeAsset(decision_id=row.id,workspace_id=row.workspace_id or None,asset_type="DECISION_KNOWLEDGE",source_type="HUMAN_APPROVED",title=row.title,summary=row.selected_solution,references_json=json.dumps({"evidence":refs,"artifacts":artifact_ids}),confidence=confidence,status="VERIFIED")
   row.review_status="APPROVED";s.add(asset);s.commit();return self._decision(row)
  finally:s.close()
 def decisions(self,workspace_id=None):
  s=self.s()
  try:
   query=select(DecisionRecord).order_by(DecisionRecord.created_at.desc())
   if workspace_id:query=query.where(DecisionRecord.workspace_id==workspace_id)
   return [self._decision(x) for x in s.scalars(query).all()]
  finally:s.close()
 def assets(self,ident=None,workspace_id=None):
  s=self.s()
  try:
   query=select(KnowledgeAsset).order_by(KnowledgeAsset.created_at.desc())
   if workspace_id:query=query.where(KnowledgeAsset.workspace_id==workspace_id,KnowledgeAsset.status=="VERIFIED")
   rows=[s.get(KnowledgeAsset,ident)] if ident else s.scalars(query).all()
   return [self._asset(x) for x in rows if x]
  finally:s.close()
 def dashboard(self,workspace_id=None):
  assets=self.assets(workspace_id=workspace_id);decisions=self.decisions(workspace_id);verified=[x for x in assets if x["status"]=="VERIFIED"]
  return {"approved_knowledge":len(verified),"decision_count":len(decisions),"experience_reuse_count":0,"average_confidence":round(sum(x["confidence"] for x in verified)/len(verified),1) if verified else 0,"boundary":"Only HUMAN_APPROVED and VERIFIED assets are eligible for Experience Retrieval. Demo data and customer files are excluded."}
 @staticmethod
 def _array(value):
  try:return json.loads(value or "[]")
  except (ValueError,TypeError):return []
 def _decision(self,x):return {"id":x.id,"mission_id":x.mission_id,"workspace_id":x.workspace_id,"title":x.title,"problem_summary":x.problem_summary,"decision_summary":x.decision_summary,"selected_solution":x.selected_solution,"evidence_refs":self._array(x.evidence_refs_json),"artifact_refs":self._array(x.artifact_refs_json),"review_status":x.review_status,"created_at":x.created_at}
 @staticmethod
 def _asset(x):return {"id":x.id,"decision_id":x.decision_id,"asset_type":x.asset_type,"source_type":x.source_type,"title":x.title,"summary":x.summary,"references":DecisionMemoryService._array(x.references_json),"confidence":x.confidence,"status":x.status,"created_at":x.created_at}
