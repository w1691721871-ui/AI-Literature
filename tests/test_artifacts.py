import json,tempfile,unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission,AIMissionEvent
from app.models.artifact import Artifact,ArtifactEvidence,ArtifactVersion
from app.models.file_asset import FileAsset
from app.models.mission_file_source import MissionFileSource
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.artifact_service import ArtifactError,ArtifactService

class ArtifactTests(unittest.TestCase):
 def setUp(self):
  self.e=create_engine('sqlite:///:memory:');self.S=sessionmaker(bind=self.e)
  for t in (AIMission.__table__,AIMissionEvent.__table__,Artifact.__table__,ArtifactVersion.__table__,ArtifactEvidence.__table__,FileAsset.__table__,MissionFileSource.__table__,Paper.__table__,PaperChunk.__table__):t.create(self.e)
  self.tmp=tempfile.TemporaryDirectory();s=self.S();s.add(Paper(paper_id='p1',title='Real indexed paper',filename='real.pdf',file_path='work/real.pdf',text_content='text'));s.add(PaperChunk(id='c1',paper_id='p1',chunk_index=0,content='real chunk',embedding='[]'));s.add(AIMission(id='m1',title='Evidence mission',mission_type='RESEARCH',goal='Compare evidence',status='COMPLETED',evidence_refs_json=json.dumps([{'paper_id':'p1','chunk_id':'c1','source':'Real indexed paper','section':'Results'}])));s.add(FileAsset(id='f1',user_id='local-user',filename='brief.txt',file_type='TXT',file_size=5,storage_path='work/x',status='COMPLETED'));s.add(MissionFileSource(mission_id='m1',file_id='f1'));s.commit();s.close();self.service=ArtifactService(self.S,initialize=False,root=Path(self.tmp.name))
 def tearDown(self):self.tmp.cleanup();self.e.dispose()
 def test_formats_evidence_review_and_download_gate(self):
  for kind,suffix in [('RESEARCH_BRIEF','.pdf'),('SOLUTION_DOCUMENT','.pdf'),('PRESENTATION','.pptx'),('DATA_REPORT','.xlsx')]:
   row=self.service.generate('m1',kind);self.assertEqual(row['status'],'NEEDS_REVIEW');self.assertTrue((Path(self.tmp.name)/f"{row['id']}_v1{suffix}").is_file());self.assertEqual(row['evidence_count'],2);self.assertIn('CUSTOMER_PROVIDED_DOCUMENT',[x['evidence_type'] for x in row['evidence']])
  brief=self.service.list('m1')[0]
  with self.assertRaises(ArtifactError):self.service.download_path(brief['id'])
  approved=self.service.review(brief['id'],'APPROVED');self.assertEqual(approved['status'],'APPROVED');self.assertTrue(self.service.download_path(brief['id']).is_file())
 def test_revision_and_three_round_cap(self):
  row=self.service.generate('m1','RESEARCH_BRIEF');self.service.review(row['id'],'REVISION_REQUESTED','Add risk');row=self.service.revise(row['id'],'Add risk');self.assertEqual(row['version'],2);self.service.review(row['id'],'REVISION_REQUESTED');row=self.service.revise(row['id'],'Again');self.assertEqual(row['version'],3);self.service.review(row['id'],'REVISION_REQUESTED')
  with self.assertRaises(ArtifactError):self.service.revise(row['id'],'Too many')
 def test_failed_mission_and_no_evidence_boundary(self):
  s=self.S();s.add(AIMission(id='failed',title='failed',mission_type='RESEARCH',goal='',status='FAILED'));s.add(AIMission(id='empty',title='empty',mission_type='RESEARCH',goal='',status='COMPLETED'));s.commit();s.close()
  with self.assertRaises(ArtifactError):self.service.generate('failed','RESEARCH_BRIEF')
  row=self.service.generate('empty','DATA_REPORT');self.assertEqual(row['evidence_count'],0);self.assertEqual(row['status'],'NEEDS_REVIEW');self.assertIn('NEEDS_CONFIRMATION',row['content_summary'])
if __name__=='__main__':unittest.main()
