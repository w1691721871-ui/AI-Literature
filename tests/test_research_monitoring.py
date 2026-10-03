import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.research_monitoring import ResearchMonitoringTask
from app.services.research_monitoring_service import ResearchMonitoringService
class ResearchMonitoringTests(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine("sqlite:///:memory:");ResearchMonitoringTask.__table__.create(self.engine);self.service=ResearchMonitoringService(sessionmaker(bind=self.engine),initialize=False)
 def tearDown(self):self.engine.dispose()
 def test_monitor_is_workspace_bound_and_on_demand(self):
  monitor=self.service.create("w1","low carbon materials")
  self.assertEqual(monitor["update_frequency"],"ON_DEMAND")
  update=self.service.detect_updates(monitor["id"],"w1",[{"status":"APPROVED","source":"https://doi.org/a"}])
  self.assertEqual(update["status"],"UPDATE_CANDIDATE")
  with self.assertRaises(PermissionError):self.service.detect_updates(monitor["id"],"w2",[])
