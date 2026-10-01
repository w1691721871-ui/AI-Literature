import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.artifact import Artifact, ArtifactEvidence, ArtifactVersion
from app.models.connector import ArtifactDataSource, Connector, ConnectorTrace, DataSource, MissionDataSource
from app.models.file_asset import FileAsset
from app.models.mission_file_source import MissionFileSource
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.artifact_service import ArtifactService
from app.services.connector_service import ConnectorError, ConnectorManager, SQLValidator


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.database=Path(self.temp.name)/"sales.sqlite"
        db=sqlite3.connect(self.database)
        try:
            db.execute("CREATE TABLE sales (id INTEGER, region TEXT, amount REAL)")
            db.executemany("INSERT INTO sales VALUES (?, ?, ?)",[(1,"East",10.0),(2,"West",15.0)])
            db.commit()
        finally:
            db.close()
        self.engine=create_engine("sqlite:///:memory:"); self.Session=sessionmaker(bind=self.engine)
        for table in (Connector.__table__,DataSource.__table__,ConnectorTrace.__table__,MissionDataSource.__table__,ArtifactDataSource.__table__,AIMission.__table__,AIMissionEvent.__table__,Artifact.__table__,ArtifactVersion.__table__,ArtifactEvidence.__table__,Paper.__table__,PaperChunk.__table__,FileAsset.__table__,MissionFileSource.__table__): table.create(self.engine)
        self.manager=ConnectorManager(self.Session,initialize=False)

    def tearDown(self): self.engine.dispose(); self.temp.cleanup()

    def _sqlite_connector(self):
        return self.manager.register({"name":"Sales SQLite","type":"DATABASE","permission":"READ_ONLY","config":{"backend":"SQLITE","sqlite_path":str(self.database)}})

    def test_register_schema_select_and_trace(self):
        connector=self._sqlite_connector(); self.assertEqual(connector["status"],"ACTIVE")
        schema=self.manager.schema(connector["id"]); self.assertEqual(schema["tables"][0]["name"],"sales")
        result=self.manager.query(connector["id"],"SELECT region, amount FROM sales ORDER BY id")
        self.assertEqual(result["row_count"],2); self.assertEqual(result["rows"][0]["region"],"East")
        self.assertEqual(len(self.manager.traces(connector["id"])),2)
        self.assertEqual(self.manager.analytics()["connector_success_rate"],100.0)
        self.assertEqual([item["name"] for item in self.manager.available_tools()], ["Database Connector","File Connector","Knowledge Connector"])

    def test_rejects_dangerous_sql_and_sensitive_config(self):
        connector=self._sqlite_connector()
        for statement in ("DELETE FROM sales","SELECT * FROM sales; DROP TABLE sales","SELECT * FROM sales -- comment"):
            with self.assertRaises(ConnectorError): self.manager.query(connector["id"],statement)
        with self.assertRaises(ConnectorError): self.manager.register({"name":"unsafe","type":"DATABASE","config":{"backend":"SQLITE","sqlite_path":str(self.database),"password":"not-stored"}})
        self.assertEqual(SQLValidator.validate("SELECT * FROM sales"),"SELECT * FROM sales")

    def test_mission_and_artifact_provenance(self):
        connector=self._sqlite_connector(); source=connector["data_sources"][0]
        session=self.Session(); session.add(Paper(paper_id="p1",title="Indexed",filename="x.pdf",file_path="work/x.pdf",text_content="real")); session.add(PaperChunk(id="c1",paper_id="p1",chunk_index=0,content="real",embedding="[]")); session.add(AIMission(id="m1",title="Data mission",mission_type="DATA_ANALYSIS",goal="Analyze sales",status="COMPLETED",evidence_refs_json=json.dumps([{ "paper_id":"p1","chunk_id":"c1" }]))) ; session.commit(); session.close()
        self.manager.attach_mission_source("m1",source["id"])
        self.manager.query(connector["id"],"SELECT * FROM sales",mission_id="m1")
        self.assertEqual(self.manager.mission_tools("m1")[0]["operation"],"SELECT_QUERY")
        artifact=ArtifactService(self.Session,initialize=False,root=Path(self.temp.name)/"artifacts").generate("m1","DATA_REPORT")
        self.assertEqual(self.manager.artifact_sources(artifact["id"]),[source["id"]])

    def test_excel_file_source_registration(self):
        session=self.Session(); asset=FileAsset(id="excel-1",user_id="local",filename="metrics.xlsx",file_type="XLSX",file_size=12,storage_path="work/metrics.xlsx",status="COMPLETED")
        session.add(asset); session.flush(); source_id=ConnectorManager.register_file_data_source(session,asset); session.commit(); session.close()
        detail=self.manager.detail(self.manager.list()[0]["id"])
        self.assertEqual(source_id,detail["data_sources"][0]["id"])


if __name__=="__main__": unittest.main()
