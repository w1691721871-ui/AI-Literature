import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.computer_mission import ComputerMission
from app.services.database import Base
from app.services.advanced_computer_service import AdvancedComputerService
class AdvancedComputerTests(unittest.TestCase):
 def setUp(self):self.e=create_engine('sqlite:///:memory:');Base.metadata.create_all(self.e);self.s=sessionmaker(bind=self.e);s=self.s();self.m=ComputerMission(task_id='t',mission_name='Excel Demo',task='Analyze workbook');s.add(self.m);s.commit();s.refresh(self.m);s.close();self.x=AdvancedComputerService(self.s,initialize=False)
 def tearDown(self):self.e.dispose()
 def test_environment_plan_approval_observation(self):
  self.assertEqual(self.x.environment(self.m.id)[0]['application'],'ResearchOS Controlled Workspace');p=self.x.plan(self.m.id);self.assertEqual(self.x.approve(p['id'])['status'],'RUNNING');self.assertTrue(self.x.observations(self.m.id))
if __name__=='__main__':unittest.main()
