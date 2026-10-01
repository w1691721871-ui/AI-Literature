import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.computer_mission import ComputerMission
from app.services.database import Base
from app.services.computer_vision_service import ComputerVisionService
class VisionTests(unittest.TestCase):
 def setUp(self):self.e=create_engine('sqlite:///:memory:');Base.metadata.create_all(self.e);self.s=sessionmaker(bind=self.e);x=self.s();self.m=ComputerMission(task_id='v',mission_name='Excel',task='Export Excel report');x.add(self.m);x.commit();x.refresh(self.m);x.close();self.v=ComputerVisionService(self.s,initialize=False)
 def tearDown(self):self.e.dispose()
 def test_demo_observation_has_no_screenshot_and_waits_approval(self):
  self.v.analyze(self.m.id);self.assertEqual(self.v.vision(self.m.id)[0]['image_reference'],'SAFE_REFERENCE_ONLY');self.assertEqual(self.v.start(self.m.id)['status'],'WAITING_APPROVAL')
if __name__=='__main__':unittest.main()
