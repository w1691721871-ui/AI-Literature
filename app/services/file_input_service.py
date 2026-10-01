"""P29 controlled enterprise file intake; never turns customer material into RAG Evidence."""
from __future__ import annotations
import json
import re
from pathlib import Path
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.ai_mission import AIMissionEvent
from app.models.document_requirement import DocumentRequirement
from app.models.document_summary import DocumentSummary
from app.models.file_asset import FileAsset
from app.models.mission_file_source import MissionFileSource
from app.services.copilot_mission_service import CopilotMissionService
from app.services.database import PROJECT_ROOT, SessionLocal, initialize_database
from app.services.document_parser_service import DocumentParserService
from app.services.requirement_extractor import RequirementExtractor


class FileInputError(ValueError): pass


class FileInputService:
    MAX_FILE_SIZE = 15 * 1024 * 1024
    EXTENSIONS = {".pdf":"PDF", ".docx":"DOCX", ".xlsx":"XLSX", ".pptx":"PPTX", ".png":"IMAGE", ".jpg":"IMAGE", ".jpeg":"IMAGE", ".txt":"TXT", ".py":"CODE", ".js":"CODE", ".ts":"CODE", ".tsx":"CODE", ".jsx":"CODE", ".java":"CODE", ".c":"CODE", ".cpp":"CODE", ".cs":"CODE", ".go":"CODE", ".rs":"CODE", ".sql":"CODE", ".html":"CODE", ".css":"CODE", ".json":"CODE", ".yaml":"CODE", ".yml":"CODE"}
    SECRET_PATTERN = re.compile(r"(?i)(?:\bsk-[a-z0-9_-]{16,}\b|\bbearer\s+[a-z0-9._~+\/-]{16,}|(?:api[_-]?key|token|password|secret)\s*[=:]\s*[^\s]{8,})")

    def __init__(self, session_factory=SessionLocal, *, initialize: bool=True, storage_root: Path|None=None, parser=None, extractor=None, copilot=None):
        if initialize: initialize_database()
        self._sessions=session_factory; self._storage=storage_root or PROJECT_ROOT / "work" / "enterprise_inputs"
        self._parser=parser or DocumentParserService(); self._extractor=extractor or RequirementExtractor(); self._copilot=copilot or CopilotMissionService(session_factory,initialize=False)

    def upload(self, filename: str, content: bytes, user_id: str="local-user") -> dict[str, object]:
        clean_name=Path(filename or "").name
        ext=Path(clean_name).suffix.lower(); file_type=self.EXTENSIONS.get(ext)
        if not file_type: raise FileInputError("文件类型不在允许范围内；不接受可执行文件或未知格式。")
        if not content: raise FileInputError("上传文件为空。")
        if len(content)>self.MAX_FILE_SIZE: raise FileInputError("文件超过 15MB 安全限制。")
        sample=content[:min(len(content), 1_000_000)].decode("utf-8",errors="ignore")
        if self.SECRET_PATTERN.search(sample): raise FileInputError("检测到疑似敏感凭据；文件未保存，请先移除凭据后重试。")
        identifier=str(uuid4()); safe_name=re.sub(r"[^A-Za-z0-9._-]+","_",clean_name)[:180] or "input"
        self._storage.mkdir(parents=True,exist_ok=True); path=self._storage / f"{identifier}_{safe_name}"; path.write_bytes(content)
        session=self._sessions()
        try:
            asset=FileAsset(id=identifier,user_id=user_id,filename=clean_name,file_type=file_type,file_size=len(content),storage_path=str(path),status="PROCESSING")
            session.add(asset); session.commit()
            try:
                parsed=self._parser.parse(clean_name,content,file_type); text=str(parsed.get("text", "")); structure=parsed.get("structure", {})
                requirements=self._extractor.extract(text, structure if isinstance(structure,dict) else {})
                summary=self._summary(file_type,structure,text); key_points=self._key_points(structure); limitations=str(parsed.get("limitations", ""))
                session.add(DocumentSummary(file_id=asset.id,summary=summary,key_points_json=json.dumps(key_points,ensure_ascii=False),entities_json="[]",limitations=limitations))
                for item in requirements: session.add(DocumentRequirement(file_id=asset.id,category=item["category"],description=item["description"],status="NEEDS_CONFIRMATION"))
                asset.status="COMPLETED"; session.commit(); return self.analysis(asset.id, session=session)
            except Exception as error:
                asset.status="FAILED"; session.commit(); raise FileInputError("文件无法安全解析；未生成需求或 Mission。") from error
        finally: session.close()

    def list(self, user_id: str="local-user") -> list[dict[str, object]]:
        session=self._sessions()
        try:return [self._asset(x,session) for x in session.scalars(select(FileAsset).where(FileAsset.user_id==user_id).order_by(FileAsset.created_at.desc())).all()]
        finally: session.close()

    def analysis(self, file_id: str, *, session: Session|None=None) -> dict[str, object]:
        owned=session is None; s=session or self._sessions()
        try:
            asset=s.get(FileAsset,file_id)
            if not asset: raise FileInputError("文件不存在。")
            return self._asset(asset,s,include_analysis=True)
        finally:
            if owned:s.close()

    def create_mission(self, file_id: str, confirmed: bool, user_id: str="local-user") -> dict[str, object]:
        if not confirmed: raise FileInputError("客户需求尚未确认；不能自动创建 Mission。")
        session=self._sessions()
        try:
            asset=session.get(FileAsset,file_id)
            if not asset or asset.user_id!=user_id: raise FileInputError("文件不存在。")
            if asset.status!="COMPLETED": raise FileInputError("文件尚未完成解析，不能创建 Mission。")
            analysis=self._asset(asset,session,include_analysis=True); categories=[item["category"] for item in analysis["requirements"]]
            message=f"Customer-provided {asset.file_type} material: {asset.filename}. Confirmed requirement categories: {', '.join(categories)}."
            copilot=self._copilot.create_session(user_id); self._copilot.chat(str(copilot["id"]),message); created=self._copilot.start(str(copilot["id"]))
            mission_id=str(created["mission"]["id"]); session.add(MissionFileSource(mission_id=mission_id,file_id=asset.id))
            session.add(AIMissionEvent(mission_id=mission_id,stage="Customer Material",action="Source material attached",status="NEEDS_CONFIRMATION",evidence_count=0,result_summary="客户提供资料已关联为 Source Material；不作为 RAG Evidence，所有需求仍需人工确认。")); session.commit()
            created["mission"]["source_materials"]=[{"file_id":asset.id,"filename":asset.filename,"file_type":asset.file_type,"classification":"CUSTOMER_PROVIDED_DOCUMENT"}]
            return created
        finally: session.close()

    def analytics(self) -> dict[str, object]:
        s=self._sessions()
        try:
            total=int(s.scalar(select(func.count(FileAsset.id))) or 0); completed=int(s.scalar(select(func.count(FileAsset.id)).where(FileAsset.status=="COMPLETED")) or 0); failed=int(s.scalar(select(func.count(FileAsset.id)).where(FileAsset.status=="FAILED")) or 0); requirements=int(s.scalar(select(func.count(DocumentRequirement.id))) or 0)
            return {"uploaded_files":total,"processed_files":completed,"failed_files":failed,"requirement_extraction_count":requirements,"input_understanding_score":{"parse_success_rate":round(completed/total*100,1) if total else 0,"requirement_coverage":round(requirements/completed,1) if completed else 0,"user_confirmation_modifications":"not measured"},"boundary":"统计来自实际上传文件与已保存需求草稿；不包含文件正文、Prompt 或客户凭据。"}
        finally:s.close()

    def _asset(self, asset: FileAsset, s: Session, include_analysis: bool=False) -> dict[str, object]:
        result={"id":asset.id,"filename":asset.filename,"file_type":asset.file_type,"file_size":asset.file_size,"status":asset.status,"created_at":asset.created_at,"classification":"CUSTOMER_PROVIDED_DOCUMENT"}
        if include_analysis:
            summary=s.scalar(select(DocumentSummary).where(DocumentSummary.file_id==asset.id).order_by(DocumentSummary.created_at.desc()))
            result.update({"summary":None if not summary else {"summary":summary.summary,"key_points":self._decode(summary.key_points_json),"entities":self._decode(summary.entities_json),"limitations":summary.limitations},"requirements":[{"id":x.id,"category":x.category,"description":x.description,"status":x.status} for x in s.scalars(select(DocumentRequirement).where(DocumentRequirement.file_id==asset.id)).all()]})
        return result

    @staticmethod
    def _decode(value: str):
        try:return json.loads(value or "[]")
        except json.JSONDecodeError:return []
    @staticmethod
    def _key_points(structure: object) -> list[str]:
        if not isinstance(structure,dict): return []
        return [f"{key}: {value}"[:220] for key,value in structure.items() if value not in (None,"",[],{})][:8]
    @staticmethod
    def _summary(file_type: str, structure: object, text: str) -> str:
        return f"已完成 {file_type} 的基础结构解析，识别到 {len(text)} 个可处理文本字符。自动输出仅描述文件结构；业务含义、需求范围与后续 Mission 均需要人工确认。"
