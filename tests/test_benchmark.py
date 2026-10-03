"""Fixture-only P36 coverage; no production knowledge or FAISS state is touched."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission
from app.models.benchmark import BenchmarkRun, BenchmarkScore, BenchmarkTask
from app.services.benchmark_service import BenchmarkService
from app.services.database import Base

class _MissionService:
    def __init__(self,sessions):self.s=sessions;self.created_payloads=[]
    def create(self,data):
        self.created_payloads.append(dict(data)
        )
        s=self.s();row=AIMission(title=data["title"],goal=data["goal"],workspace_id=data.get("workspace_id"));s.add(row);s.commit();s.refresh(row);out={"id":row.id};s.close();return out
class _Runtime:
    def execute(self,mission_id,**_):return {"mission_id":mission_id,"status":"WAITING_REVIEW"}
class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:");Base.metadata.create_all(self.engine);self.sessions=sessionmaker(bind=self.engine,autoflush=False,autocommit=False);self.service=BenchmarkService(self.sessions,initialize=False,missions=_MissionService(self.sessions),runtime=_Runtime())
    def tearDown(self):self.engine.dispose()
    def test_create_and_empty_dashboard_are_real_zeroes(self):
        self.assertEqual(self.service.dashboard()["benchmarks"],0)
        task=self.service.create({"name":"Plan fixture","category":"RESEARCH","difficulty":"EASY","description":"Fixture only","expected_agents":[],"expected_tools":[],"evaluation_rules":{}})
        self.assertEqual(task["category"],"RESEARCH");self.assertEqual(self.service.dashboard()["runs"],0)
    def test_runner_scores_observed_records(self):
        task=self.service.create({"name":"Run fixture","category":"RESEARCH","difficulty":"EASY","description":"Fixture only","expected_agents":[],"expected_tools":[],"evaluation_rules":{}})
        result=self.service.run(task["id"])
        self.assertEqual(result["status"],"SUCCESS");self.assertIsNotNone(result["scores"])
    def test_regression_uses_existing_runs_only(self):
        task=self.service.create({"name":"Regression","category":"RESEARCH","difficulty":"EASY","description":"Fixture only","expected_agents":[],"expected_tools":[],"evaluation_rules":{}})
        self.service.run(task["id"]);self.service.run(task["id"])
        self.assertEqual(len(self.service.regression()),1)
    def test_invalid_task_is_rejected(self):
        with self.assertRaises(Exception):self.service.create({"name":"x","category":"OTHER","difficulty":"EASY","description":"x"})
    def test_permission_check_blocks_runner_before_mission_creation(self):
        task=self.service.create({"name":"Guarded","category":"RESEARCH","difficulty":"EASY","description":"Fixture only","expected_agents":[],"expected_tools":[],"evaluation_rules":{}})
        with self.assertRaises(PermissionError): self.service.run(task["id"],permission_check=lambda _action: (_ for _ in ()).throw(PermissionError("blocked")))
    def test_runner_forwards_workspace_boundary_to_created_mission(self):
        task=self.service.create({"name":"Scoped","category":"RESEARCH","difficulty":"EASY","description":"Fixture only","expected_agents":[],"expected_tools":[],"evaluation_rules":{}})
        self.service.run(task["id"],workspace_id="workspace-fixture")
        self.assertEqual(self.service.missions.created_payloads[-1]["workspace_id"],"workspace-fixture")
if __name__=="__main__":unittest.main()
