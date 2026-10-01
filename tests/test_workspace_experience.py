"""P38 fixture coverage for projections, comments and RBAC boundaries."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission,AIMissionEvent
from app.models.artifact import Artifact
from app.services.database import Base
from app.services.workspace_experience_service import WorkspaceExperienceService

class _Artifacts:
 def __init__(self,s):self.s=s;self.reviewed=[]
 def _data(self,row,_s):return {"id":row.id,"title":row.title,"status":row.status}
 def detail(self,ident):return {"id":ident,"preview":{"title":"Draft","summary":"Persisted only","review_status":"NEEDS_REVIEW"},"version":1,"versions":[],"evidence":[]}
 def review(self,*args):self.reviewed.append(args)
class _Permissions:
 def __init__(self,allow=True):self.allow=allow
 def check(self,*_):
  if not self.allow:raise PermissionError("blocked")
  return {"allowed":True}
class WorkspaceExperienceTests(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine("sqlite:///:memory:");Base.metadata.create_all(self.engine);self.sessions=sessionmaker(bind=self.engine,autoflush=False,autocommit=False)
  s=self.sessions();self.m=AIMission(title="Mission",goal="Goal");s.add(self.m);s.flush();s.add(AIMissionEvent(mission_id=self.m.id,stage="Mission",action="Mission Created",status="CREATED",result_summary="Created"));self.a=Artifact(mission_id=self.m.id,artifact_type="RESEARCH_BRIEF",title="Draft",status="NEEDS_REVIEW");s.add(self.a);s.commit();self.mid,self.aid=self.m.id,self.a.id;s.close();self.artifacts=_Artifacts(self.sessions)
 def tearDown(self):self.engine.dispose()
 def test_dashboard_uses_real_empty_or_persisted_records(self):
  service=WorkspaceExperienceService(self.sessions,initialize=False,artifacts=self.artifacts)
  self.assertEqual(len(service.dashboard()["missions"]),1)
 def test_preview_is_persisted_projection(self):
  service=WorkspaceExperienceService(self.sessions,initialize=False,artifacts=self.artifacts)
  self.assertEqual(service.preview(self.aid)["preview"]["title"],"Draft")
 def test_comment_requires_permission_and_can_request_revision(self):
  service=WorkspaceExperienceService(self.sessions,initialize=False,artifacts=self.artifacts,permissions=_Permissions())
  result=service.comment(self.aid,"reviewer","Please revise","workspace",True)
  self.assertEqual(result["status"],"REVISION_REQUESTED");self.assertEqual(self.artifacts.reviewed[0][1],"REVISION_REQUESTED")
 def test_comment_permission_is_enforced(self):
  service=WorkspaceExperienceService(self.sessions,initialize=False,artifacts=self.artifacts,permissions=_Permissions(False))
  with self.assertRaises(PermissionError):service.comment(self.aid,"viewer","x","workspace")
if __name__=="__main__":unittest.main()
