"""P29 tests use an isolated SQLite database and temporary customer-file storage."""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.ai_mission import AIMissionEvent
from app.models.document_requirement import DocumentRequirement
from app.models.document_summary import DocumentSummary
from app.models.file_asset import FileAsset
from app.models.mission_file_source import MissionFileSource
from app.services.file_input_service import FileInputError, FileInputService


class FakeCopilot:
    def create_session(self, _user): return {"id":"session-fixture"}
    def chat(self, _session, _message): return {"intent":"SOLUTION"}
    def start(self, _session): return {"mission":{"id":"mission-fixture","status":"PLANNING"},"intent":"SOLUTION"}


def zipped(files):
    output=io.BytesIO()
    with zipfile.ZipFile(output,"w") as archive:
        for name,value in files.items(): archive.writestr(name,value)
    return output.getvalue()


class MultimodalInputTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine("sqlite:///:memory:"); self.Session=sessionmaker(bind=self.engine)
        for table in (FileAsset.__table__,DocumentSummary.__table__,DocumentRequirement.__table__,MissionFileSource.__table__,AIMissionEvent.__table__): table.create(self.engine)
        self.temp=tempfile.TemporaryDirectory(); self.service=FileInputService(self.Session,initialize=False,storage_root=Path(self.temp.name),copilot=FakeCopilot())
    def tearDown(self): self.temp.cleanup(); self.engine.dispose()
    def test_pdf_docx_xlsx_pptx_image_and_code_parse(self):
        pdf=io.BytesIO(); writer=PdfWriter(); writer.add_blank_page(width=100,height=100); writer.write(pdf)
        docx=zipped({"word/document.xml":"<w:document xmlns:w='w'><w:body><w:p><w:r><w:t>Customer AI delivery</w:t></w:r></w:p></w:body></w:document>"})
        xlsx=zipped({"xl/sharedStrings.xml":"<sst xmlns='s'><si><t>MES data</t></si></sst>","xl/worksheets/sheet1.xml":"<worksheet xmlns='x'><sheetData><row r='1'><c t='s'><v>0</v></c></row><row r='2'><c><v>1</v></c></row></sheetData></worksheet>"})
        pptx=zipped({"ppt/slides/slide1.xml":"<p:sld xmlns:p='p' xmlns:a='a'><a:t>Research proposal</a:t></p:sld>"})
        cases=[("a.pdf",pdf.getvalue()),("a.docx",docx),("a.xlsx",xlsx),("a.pptx",pptx),("a.png",b"not-a-real-image"),("a.py",b"def analyze_data():\n return 1")]
        for filename,data in cases:
            result=self.service.upload(filename,data); self.assertEqual(result["status"],"COMPLETED"); self.assertIsNotNone(result["summary"])
        self.assertEqual(len(self.service.list()),6)
    def test_security_and_size_boundaries(self):
        with self.assertRaises(FileInputError): self.service.upload("unsafe.exe",b"x")
        with self.assertRaises(FileInputError): self.service.upload("notes.txt",b"API_KEY=abcdefghijklmnopqrstuvwxyz")
        with self.assertRaises(FileInputError): self.service.upload("large.txt",b"x"*(self.service.MAX_FILE_SIZE+1))
    def test_requirement_drafts_are_confirmation_only_and_source_is_linked(self):
        item=self.service.upload("brief.txt",b"Customer needs AI prediction with MES data and security isolation.")
        self.assertTrue(item["requirements"]); self.assertTrue(all(x["status"]=="NEEDS_CONFIRMATION" for x in item["requirements"]))
        with self.assertRaises(FileInputError): self.service.create_mission(item["id"],False)
        created=self.service.create_mission(item["id"],True); self.assertEqual(created["mission"]["id"],"mission-fixture")
        self.assertEqual(created["mission"]["source_materials"][0]["classification"],"CUSTOMER_PROVIDED_DOCUMENT")
        session=self.Session(); self.assertEqual(session.query(MissionFileSource).count(),1); session.close()
    def test_analytics_uses_real_saved_records(self):
        self.service.upload("notes.txt",b"business delivery")
        metrics=self.service.analytics(); self.assertEqual(metrics["uploaded_files"],1); self.assertEqual(metrics["processed_files"],1); self.assertGreater(metrics["requirement_extraction_count"],0)

if __name__=="__main__": unittest.main()
