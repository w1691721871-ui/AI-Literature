"""P38 projections over existing Mission, Artifact, evaluation and review records."""
from sqlalchemy import select
from app.models.agent_evaluation import AgentEvaluation
from app.models.ai_mission import AIMission,AIMissionEvent
from app.models.artifact import Artifact,ArtifactEvidence
from app.models.benchmark import BenchmarkRun
from app.models.workspace_experience import ActivityEvent,ArtifactComment
from app.services.ai_mission_service import AIMissionService
from app.services.artifact_service import ArtifactService
from app.services.database import SessionLocal,initialize_database
from app.services.dynamic_planner_service import DynamicPlannerService
from app.services.governance_service import PermissionService
class WorkspaceExperienceError(ValueError):pass
class WorkspaceExperienceService:
 def __init__(self,sessions=SessionLocal,*,initialize=True,missions=None,artifacts=None,planner=None,permissions=None):
  if initialize:initialize_database()
  self.s=sessions;self.missions=missions or AIMissionService(sessions,initialize=False);self.artifacts=artifacts or ArtifactService(sessions,initialize=False);self.planner=planner or DynamicPlannerService(sessions,initialize=False);self.permissions=permissions or PermissionService(sessions,initialize=False)
 def dashboard(self,workspace_id=None):
  s=self.s()
  try:
   mission_query=select(AIMission).order_by(AIMission.updated_at.desc())
   if workspace_id:mission_query=mission_query.where(AIMission.workspace_id==workspace_id)
   missions=list(s.scalars(mission_query).all())
   mission_ids=[item.id for item in missions]
   artifact_query=select(Artifact).order_by(Artifact.updated_at.desc())
   if workspace_id:artifact_query=artifact_query.where(Artifact.mission_id.in_(mission_ids)) if mission_ids else artifact_query.where(Artifact.mission_id=="")
   arts=list(s.scalars(artifact_query).all())
   return {"missions":[self.missions._mission(x) for x in missions[:8]],"artifacts":[self.artifacts._data(x,s) for x in arts[:8]],"reviews":{"pending":sum(x.status in {"NEEDS_REVIEW","REVISION_REQUESTED"} for x in arts),"revision_requested":sum(x.status=="REVISION_REQUESTED" for x in arts)},"agents":self.missions._team(None),"active_missions":sum(x.status not in {"COMPLETED","FAILED"} for x in missions),"boundary":"Workspace only projects persisted Mission, Artifact, Evidence and Human Review records; no prompts or hidden reasoning are exposed."}
  finally:s.close()
 def mission_workspace(self,mission_id):
  detail=self.missions.detail(mission_id);self._sync(mission_id);s=self.s()
  try:
   evaluation=s.scalar(select(AgentEvaluation).where(AgentEvaluation.mission_id==mission_id));benchmark=s.scalar(select(BenchmarkRun).where(BenchmarkRun.mission_id==mission_id).order_by(BenchmarkRun.created_at.desc()))
   events=self.activities(mission_id,s);plan=self.planner.plan(mission_id)
   return {"mission":detail,"plan":plan,"timeline":detail.get("timeline",[]),"evidence":detail.get("evidence_refs",[]),"artifacts":[self.artifacts._data(x,s) for x in s.scalars(select(Artifact).where(Artifact.mission_id==mission_id)).all()],"review":{"status":detail.get("status"),"comment":detail.get("review_comment","")},"activities":events,"quality":{"evidence_coverage":evaluation.evidence_coverage if evaluation else None,"agent_score":evaluation.evaluation_score if evaluation else None,"benchmark_score":benchmark.score if benchmark else None}}
  finally:s.close()
 def preview(self,artifact_id):
  data=self.artifacts.detail(artifact_id);return {"preview":data["preview"],"version":data["version"],"versions":data["versions"],"evidence":data["evidence"],"boundary":"Preview is sourced from the persisted Artifact draft and Evidence references only; it does not create content."}
 def comment(self,artifact_id,reviewer_id,comment,workspace_id,request_revision=False):
  self.permissions.check(workspace_id,reviewer_id,"ARTIFACT_REVIEW");s=self.s()
  try:
   if not s.get(Artifact,artifact_id):raise WorkspaceExperienceError("Artifact not found.")
   row=ArtifactComment(artifact_id=artifact_id,reviewer_id=reviewer_id,comment=comment.strip(),status="REVISION_REQUESTED" if request_revision else "COMMENTED");s.add(row);s.commit();result={"id":row.id,"artifact_id":artifact_id,"reviewer":reviewer_id,"status":row.status,"comment":comment}
  finally:s.close()
  if request_revision:self.artifacts.review(artifact_id,"REVISION_REQUESTED",comment)
  return result
 def activities(self,mission_id,s=None):
  close=s is None;s=s or self.s()
  try:return [{"id":x.id,"mission_id":x.mission_id,"event_type":x.event_type,"title":x.title,"summary":x.summary,"created_at":x.created_at} for x in s.scalars(select(ActivityEvent).where(ActivityEvent.mission_id==mission_id).order_by(ActivityEvent.created_at)).all()]
  finally:
   if close:s.close()
 def _sync(self,mission_id):
  s=self.s()
  try:
   for e in s.scalars(select(AIMissionEvent).where(AIMissionEvent.mission_id==mission_id)).all():
    if s.scalar(select(ActivityEvent).where(ActivityEvent.source_event_id==e.id)):continue
    action=e.action.upper();kind="MISSION_CREATED" if "CREATED" in action else "EVIDENCE_FOUND" if "EVIDENCE" in action else "ARTIFACT_CREATED" if "DELIVERY" in action else "REVIEW_REQUESTED" if "REVIEW" in action else "AGENT_STARTED"
    s.add(ActivityEvent(mission_id=mission_id,source_event_id=e.id,event_type=kind,title=e.action[:180],summary=e.result_summary[:1000],created_at=e.created_at))
   s.commit()
  finally:s.close()
