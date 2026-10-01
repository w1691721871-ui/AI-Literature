"""P39 fixture-only memory tests; no RAG, FAISS, or customer files are touched."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.services.database import Base
from app.services.enterprise_memory_service import DecisionMemoryService
class _Permissions:
 def __init__(self,allow=True):self.allow=allow
 def check(self,*_):
  if not self.allow:raise PermissionError("blocked")
  return {"allowed":True}
class EnterpriseMemoryTests(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine("sqlite:///:memory:");Base.metadata.create_all(self.engine);self.sessions=sessionmaker(bind=self.engine,autoflush=False,autocommit=False)
  s=self.sessions();m=AIMission(title="RAG decision",goal="Compare RAG",status="COMPLETED",evidence_refs_json='[{"paper_id":"p","chunk_id":"c"}]');s.add(m);s.flush();s.add(Artifact(mission_id=m.id,artifact_type="SOLUTION_DOCUMENT",title="Draft",status="APPROVED"));s.commit();self.mid=m.id;s.close()
 def tearDown(self):self.engine.dispose()
 def test_completed_mission_creates_draft_not_asset(self):
  service=DecisionMemoryService(self.sessions,initialize=False,permissions=_Permissions());decision=service.extract(self.mid)
  self.assertEqual(decision["review_status"],"DRAFT");self.assertEqual(service.dashboard()["approved_knowledge"],0)
 def test_approval_creates_verified_asset_and_retrieval(self):
  service=DecisionMemoryService(self.sessions,initialize=False,permissions=_Permissions());decision=service.extract(self.mid);service.approve(decision["id"],"ws","reviewer")
  assets=service.assets();self.assertEqual(assets[0]["status"],"VERIFIED");self.assertEqual(service.experiences.search("RAG decision")[0]["id"],assets[0]["id"])
 def test_permission_blocks_approval(self):
  service=DecisionMemoryService(self.sessions,initialize=False,permissions=_Permissions(False));decision=service.extract(self.mid)
  with self.assertRaises(PermissionError):service.approve(decision["id"],"ws","viewer")
 def test_confidence_is_observed_from_approval_and_references(self):
  service=DecisionMemoryService(self.sessions,initialize=False,permissions=_Permissions());decision=service.extract(self.mid);service.approve(decision["id"],"ws","reviewer")
  self.assertGreater(service.assets()[0]["confidence"],0)
if __name__=="__main__":unittest.main()
