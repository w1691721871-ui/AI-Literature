from __future__ import annotations

import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.file_asset import FileAsset
from app.models.mission_file_source import MissionFileSource
from app.services.database import Base, PROJECT_ROOT
from app.services.enterprise_computer_worker_service import EnterpriseComputerWorkerService


class EnterpriseComputerWorkerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        (PROJECT_ROOT / "work").mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=PROJECT_ROOT / "work"))
        session = self.sessions()
        session.add_all([
            AIMission(id="mission-doc", title="Source review", goal="Summarize this document", workspace_id="workspace-a", status="PLANNING"),
            AIMission(id="mission-data", title="Data review", goal="Analyze this spreadsheet data", workspace_id="workspace-a", status="PLANNING"),
            AIMission(id="mission-other", title="Other", goal="Other", workspace_id="workspace-b", status="PLANNING"),
        ])
        self.document = self.root / "notes.txt"; self.document.write_text("Authorized research notes\nScope and limitations", encoding="utf-8")
        self.sheet = self.root / "experiment.xlsx"
        with zipfile.ZipFile(self.sheet, "w") as archive:
            archive.writestr("xl/sharedStrings.xml", "<sst xmlns='s'><si><t>temperature</t></si><si><t>yield</t></si></sst>")
            archive.writestr("xl/worksheets/sheet1.xml", "<worksheet xmlns='x'><sheetData><row r='1'><c t='s'><v>0</v></c><c t='s'><v>1</v></c></row><row r='2'><c><v>20</v></c><c><v>5</v></c></row></sheetData></worksheet>")
        session.add_all([
            FileAsset(id="doc", user_id="user-a", filename="notes.txt", file_type="TXT", file_size=self.document.stat().st_size, storage_path=str(self.document), status="COMPLETED"),
            FileAsset(id="sheet", user_id="user-a", filename="experiment.xlsx", file_type="XLSX", file_size=self.sheet.stat().st_size, storage_path=str(self.sheet), status="COMPLETED"),
            FileAsset(id="other", user_id="user-b", filename="other.txt", file_type="TXT", file_size=1, storage_path=str(self.document), status="COMPLETED"),
            MissionFileSource(mission_id="mission-doc", file_id="doc"),
            MissionFileSource(mission_id="mission-data", file_id="sheet"),
            MissionFileSource(mission_id="mission-other", file_id="other"),
        ])
        session.commit(); session.close()
        self.worker = EnterpriseComputerWorkerService(self.sessions, initialize=False)

    def tearDown(self):
        self.engine.dispose(); shutil.rmtree(self.root, ignore_errors=True)

    def test_document_worker_reads_only_attached_authorized_document(self):
        result = self.worker.execute({"id": "mission-doc", "goal": "Summarize this document", "status": "PLANNING"})
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["output"]["source"]["id"], "doc")
        self.assertNotIn("Authorized research notes", str(result["output"]))

    def test_data_worker_returns_a_candidate_not_an_analytical_claim(self):
        result = self.worker.execute({"id": "mission-data", "goal": "Analyze this spreadsheet data", "status": "PLANNING"})
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["output"]["classification"], "DATA_INSIGHT_CANDIDATE")
        self.assertEqual(result["output"]["sheets"][0]["rows"], 2)
        self.assertIn("reviewer", result["summary"].lower())

    def test_unlinked_source_is_not_available_to_another_mission(self):
        result = self.worker.execute({"id": "mission-other", "goal": "Summarize this document", "status": "PLANNING"})
        self.assertEqual(result["output"]["source"]["id"], "other")
        denied = self.worker.execute({"id": "mission-doc", "goal": "Analyze spreadsheet data", "status": "PLANNING"})
        self.assertEqual(denied["status"], "NEEDS_REVIEW")

    def test_report_worker_never_generates_before_mission_approval(self):
        result = self.worker.execute({"id": "mission-doc", "goal": "Create a research report", "status": "PLANNING", "evidence_refs": [{"paper_id": "p", "chunk_id": "c"}]})
        self.assertEqual(result["status"], "WAITING_REVIEW")
        self.assertIn("approval", result["summary"].lower())


if __name__ == "__main__":
    unittest.main()
