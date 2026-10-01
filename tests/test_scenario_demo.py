"""Fixture-only P37 scenario coverage; no production knowledge or FAISS is used."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission
from app.services.benchmark_service import BenchmarkService
from app.services.database import Base
from app.services.scenario_demo_service import ScenarioDemoService

class _Missions:
    def __init__(self, sessions): self.s = sessions
    def create(self, data):
        s=self.s(); row=AIMission(title=data["title"], mission_type=data["mission_type"], goal=data["goal"]); s.add(row); s.commit(); s.refresh(row); output={"id":row.id}; s.close(); return output
    def detail(self, mission_id): return {"id":mission_id,"timeline":[],"status":"WAITING_REVIEW"}
class _Runtime:
    def execute(self, mission_id, **_): return {"mission_id":mission_id,"status":"WAITING_REVIEW"}
class _Artifacts:
    def generate(self, mission_id, _kind): return {"id":"artifact-fixture","mission_id":mission_id,"status":"NEEDS_REVIEW"}
    def detail(self, artifact_id): return {"id":artifact_id,"status":"NEEDS_REVIEW","evidence_count":0}

class ScenarioDemoTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:"); Base.metadata.create_all(self.engine); self.sessions=sessionmaker(bind=self.engine,autoflush=False,autocommit=False)
        missions=_Missions(self.sessions); runtime=_Runtime(); benchmark=BenchmarkService(self.sessions,initialize=False,missions=missions,runtime=runtime)
        self.service=ScenarioDemoService(self.sessions,initialize=False,missions=missions,runtime=runtime,artifacts=_Artifacts(),benchmarks=benchmark)
    def tearDown(self): self.engine.dispose()
    def test_seeded_scenario_is_explicitly_demo_only(self):
        scenario=self.service.list()[0]
        self.assertEqual(scenario["industry"],"MANUFACTURING")
        self.assertEqual(scenario["data_sources"][0]["classification"],"DEMO_ONLY")
        self.assertIn("DEMO_ONLY",scenario["description"])
    def test_runner_reuses_one_mission_and_records_artifact_benchmark(self):
        scenario=self.service.list()[0]; result=self.service.run(scenario["id"])
        self.assertEqual(result["status"],"COMPLETED")
        self.assertTrue(result["mission"]["id"])
        self.assertEqual(result["artifact"]["status"],"NEEDS_REVIEW")
        self.assertEqual(result["benchmark"]["mission_id"],result["mission"]["id"])
    def test_permission_prevents_run(self):
        scenario=self.service.list()[0]
        with self.assertRaises(PermissionError): self.service.run(scenario["id"],permission_check=lambda _:(_ for _ in ()).throw(PermissionError("blocked")))
if __name__=="__main__": unittest.main()
