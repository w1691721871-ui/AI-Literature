"""P31 read-only enterprise connector framework.

Only SQLite is executable in this release.  The registry never persists a
password, token, authorization header, or connection URI with credentials.
"""
from __future__ import annotations
import json
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from sqlalchemy import func, select
from app.models.connector import Connector, ConnectorTrace, DataSource, MissionDataSource, ArtifactDataSource
from app.models.ai_mission import AIMissionEvent
from app.services.database import SessionLocal, initialize_database


class ConnectorError(ValueError): pass


class SQLValidator:
    """A deliberately small SELECT-only SQL boundary."""
    blocked = re.compile(r"\b(insert|update|delete|drop|alter|truncate|attach|detach|pragma|vacuum|reindex|replace|create|grant|revoke)\b", re.I)

    @classmethod
    def validate(cls, sql: str) -> str:
        statement = (sql or "").strip()
        if not statement or not re.match(r"^select\b", statement, re.I):
            raise ConnectorError("SQL 仅允许单条 SELECT 查询。")
        if ";" in statement or "--" in statement or "/*" in statement or "*/" in statement:
            raise ConnectorError("SQL 不允许多语句或注释。")
        if cls.blocked.search(statement):
            raise ConnectorError("检测到危险 SQL 操作，已被安全策略阻止。")
        return statement


class ConnectorManager:
    TYPES = {"DATABASE", "FILE", "KNOWLEDGE"}
    PERMISSIONS = {"READ_ONLY", "APPROVED_WRITE"}
    SENSITIVE_KEYS = re.compile(r"(password|secret|token|credential|authorization|api[_-]?key)", re.I)
    MAX_ROWS = 200

    def __init__(self, session_factory=SessionLocal, *, initialize=True):
        if initialize: initialize_database()
        self.sessions = session_factory

    def register(self, payload: dict) -> dict:
        kind = str(payload.get("type", "")).upper()
        permission = str(payload.get("permission", "READ_ONLY")).upper()
        if kind not in self.TYPES: raise ConnectorError("Connector type 必须为 DATABASE、FILE 或 KNOWLEDGE。")
        if permission not in self.PERMISSIONS: raise ConnectorError("无效 Connector permission。")
        name = str(payload.get("name", "")).strip()
        if not name: raise ConnectorError("Connector 名称不能为空。")
        config = self._safe_config(payload.get("config", {}))
        backend = str(config.get("backend", "")).upper()
        state = "ACTIVE"
        if kind == "DATABASE" and backend not in {"SQLITE", ""}:
            state = "DISABLED"  # no credentials / drivers are accepted in P31
        if kind == "DATABASE" and backend in {"SQLITE", ""}:
            path = config.get("sqlite_path")
            if not path: raise ConnectorError("SQLite Connector 需要 sqlite_path，且该路径不会保存凭证。")
            self._sqlite_path(path)
            config["backend"] = "SQLITE"
        session = self.sessions()
        try:
            row = Connector(name=name, connector_type=kind, status=state, permission=permission, workspace_id=payload.get("workspace_id") or None, config_summary=json.dumps(config, ensure_ascii=False))
            session.add(row); session.flush()
            if kind == "DATABASE":
                session.add(DataSource(connector_id=row.id, name=f"{name} data source", source_type="SQLITE" if config.get("backend") == "SQLITE" else backend or "UNCONFIGURED", description="Registered read-only enterprise data source."))
            session.commit(); return self._connector(row, session, detail=True)
        finally: session.close()

    def list(self, workspace_id=None) -> list[dict]:
        session = self.sessions()
        try:
            query=select(Connector).order_by(Connector.created_at.desc())
            if workspace_id: query=query.where(Connector.workspace_id==workspace_id)
            return [self._connector(item, session) for item in session.scalars(query).all()]
        finally: session.close()

    @staticmethod
    def available_tools() -> list[dict]:
        return [
            {"name":"Database Connector","purpose":"Read SQLite schema and execute validated SELECT queries.","permission":"READ_ONLY","status":"ACTIVE"},
            {"name":"File Connector","purpose":"Register approved customer spreadsheet sources without converting them to RAG Evidence.","permission":"READ_ONLY","status":"ACTIVE"},
            {"name":"Knowledge Connector","purpose":"Reference the existing FAISS knowledge base through the current retrieval flow.","permission":"READ_ONLY","status":"ACTIVE"},
        ]

    def detail(self, connector_id: str) -> dict:
        session = self.sessions()
        try: return self._connector(self._require(session, connector_id), session, detail=True)
        finally: session.close()

    def schema(self, connector_id: str, mission_id: str | None = None) -> dict:
        started = time.perf_counter(); session = self.sessions()
        try:
            connector = self._readable_sqlite(session, connector_id); path = self._path(connector)
            with closing(self._connection(path)) as db:
                tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]
                result = {"connector_id":connector.id,"tables":[{"name":name,"columns":[{"name":c[1],"type":c[2],"nullable":not bool(c[3])} for c in db.execute(f'PRAGMA table_info("{name.replace(chr(34), chr(34)*2)}")').fetchall()]} for name in tables]}
            self._trace(session, connector, mission_id, "SCHEMA_READ", started, "COMPLETED", f"Read schema for {len(tables)} tables."); session.commit(); return result
        except Exception as error:
            self._trace_failure(session, connector_id, mission_id, "SCHEMA_READ", started, error); session.commit(); raise
        finally: session.close()

    def query(self, connector_id: str, sql: str, mission_id: str | None = None) -> dict:
        started = time.perf_counter(); session = self.sessions()
        try:
            statement = SQLValidator.validate(sql); connector = self._readable_sqlite(session, connector_id)
            with closing(self._connection(self._path(connector))) as db:
                cursor = db.execute(statement); columns = [item[0] for item in cursor.description or []]
                rows = [dict(zip(columns, row)) for row in cursor.fetchmany(self.MAX_ROWS)]
            result = {"connector_id":connector.id,"columns":columns,"rows":rows,"row_count":len(rows),"limited_to":self.MAX_ROWS}
            self._trace(session, connector, mission_id, "SELECT_QUERY", started, "COMPLETED", f"Read {len(rows)} rows with a read-only SELECT query.")
            if mission_id: self._mission_event(session, mission_id, connector.name, "SELECT query completed", len(rows))
            session.commit(); return result
        except Exception as error:
            self._trace_failure(session, connector_id, mission_id, "SELECT_QUERY", started, error); session.commit(); raise
        finally: session.close()

    def attach_mission_source(self, mission_id: str, data_source_id: str) -> dict:
        session = self.sessions()
        try:
            if not session.get(DataSource, data_source_id): raise ConnectorError("DataSource 不存在。")
            exists = session.scalar(select(MissionDataSource).where(MissionDataSource.mission_id == mission_id, MissionDataSource.data_source_id == data_source_id))
            if not exists: session.add(MissionDataSource(mission_id=mission_id, data_source_id=data_source_id)); session.commit()
            return {"mission_id":mission_id,"data_source_id":data_source_id,"status":"ATTACHED"}
        finally: session.close()

    @staticmethod
    def register_file_data_source(session, asset) -> str:
        """Register an uploaded spreadsheet as a provenance record, never as RAG Evidence."""
        connector=session.scalar(select(Connector).where(Connector.connector_type=="FILE",Connector.name=="Customer File Connector"))
        if not connector:
            connector=Connector(name="Customer File Connector",connector_type="FILE",status="ACTIVE",permission="READ_ONLY",config_summary=json.dumps({"scope":"customer-provided files"}))
            session.add(connector); session.flush()
        description=f"Customer-provided {asset.file_type} source; file_asset:{asset.id}; requires human confirmation."
        source=session.scalar(select(DataSource).where(DataSource.connector_id==connector.id,DataSource.description==description))
        if not source:
            source=DataSource(connector_id=connector.id,name=asset.filename,source_type=asset.file_type,description=description)
            session.add(source); session.flush()
        return source.id

    def traces(self, connector_id: str) -> list[dict]:
        session = self.sessions()
        try:
            self._require(session, connector_id)
            return [{"operation":x.operation,"duration_ms":x.duration_ms,"status":x.status,"result_summary":x.result_summary,"mission_id":x.mission_id,"created_at":x.created_at} for x in session.scalars(select(ConnectorTrace).where(ConnectorTrace.connector_id==connector_id).order_by(ConnectorTrace.created_at.desc())).all()]
        finally: session.close()

    def analytics(self) -> dict:
        session = self.sessions()
        try:
            rows=list(session.scalars(select(ConnectorTrace)).all()); calls=len(rows); completed=sum(x.status=="COMPLETED" for x in rows)
            return {"connectors":int(session.scalar(select(func.count(Connector.id))) or 0),"tool_usage_count":calls,"failures":calls-completed,"connector_success_rate":round(completed/calls*100,1) if calls else 0,"average_duration_ms":round(sum(x.duration_ms for x in rows)/calls,1) if calls else 0,"data_source_usage":int(session.scalar(select(func.count(DataSource.id))) or 0)}
        finally: session.close()

    def mission_tools(self, mission_id: str) -> list[dict]:
        session = self.sessions()
        try:
            traces=session.scalars(select(ConnectorTrace).where(ConnectorTrace.mission_id==mission_id).order_by(ConnectorTrace.created_at.asc())).all()
            return [{"connector_name":self._require(session,x.connector_id).name,"operation":x.operation,"duration_ms":x.duration_ms,"status":x.status,"result_summary":x.result_summary} for x in traces]
        finally: session.close()

    def mission_sources(self, mission_id: str) -> list[dict]:
        session = self.sessions()
        try:
            links=session.scalars(select(MissionDataSource).where(MissionDataSource.mission_id==mission_id)).all()
            return [{"id":source.id,"name":source.name,"type":source.source_type,"description":source.description} for link in links if (source:=session.get(DataSource, link.data_source_id))]
        finally: session.close()

    def artifact_sources(self, artifact_id: str) -> list[str]:
        session = self.sessions()
        try: return [x.data_source_id for x in session.scalars(select(ArtifactDataSource).where(ArtifactDataSource.artifact_id==artifact_id)).all()]
        finally: session.close()

    def link_artifact_sources(self, session, artifact_id: str, mission_id: str) -> None:
        for link in session.scalars(select(MissionDataSource).where(MissionDataSource.mission_id==mission_id)).all():
            exists=session.scalar(select(ArtifactDataSource).where(ArtifactDataSource.artifact_id==artifact_id,ArtifactDataSource.data_source_id==link.data_source_id))
            if not exists: session.add(ArtifactDataSource(artifact_id=artifact_id,data_source_id=link.data_source_id))

    def _readable_sqlite(self, session, connector_id):
        row=self._require(session,connector_id)
        if row.status!="ACTIVE" or row.permission not in {"READ_ONLY","APPROVED_WRITE"}: raise ConnectorError("Connector 未启用或权限不足。")
        config=self._config(row)
        if row.connector_type!="DATABASE" or config.get("backend")!="SQLITE": raise ConnectorError("当前 Connector 不支持 SQLite 只读操作。")
        return row

    @staticmethod
    def _connection(path: Path): return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    def _path(self,row): return self._sqlite_path(self._config(row).get("sqlite_path"))
    @staticmethod
    def _sqlite_path(value):
        path=Path(str(value or "")).expanduser().resolve()
        if path.suffix.lower() not in {".db",".sqlite",".sqlite3"} or not path.is_file(): raise ConnectorError("SQLite 路径必须指向已有 .db/.sqlite/.sqlite3 文件。")
        return path
    def _safe_config(self, config):
        if not isinstance(config,dict): raise ConnectorError("Connector config 必须是对象。")
        if any(self.SENSITIVE_KEYS.search(str(key)) for key in config): raise ConnectorError("Connector config 不允许保存密码、Token、Secret 或 API Key。")
        return {key:value for key,value in config.items() if key in {"backend","sqlite_path","label","scope"}}
    @staticmethod
    def _config(row):
        try:return json.loads(row.config_summary or "{}")
        except json.JSONDecodeError:return {}
    @staticmethod
    def _require(session, connector_id):
        row=session.get(Connector,connector_id)
        if not row: raise ConnectorError("Connector 不存在。")
        return row
    def _connector(self,row,session,detail=False):
        data={"id":row.id,"name":row.name,"type":row.connector_type,"status":row.status,"permission":row.permission,"config_summary":self._config(row),"created_at":row.created_at}
        if detail:data["data_sources"]=[{"id":x.id,"name":x.name,"type":x.source_type,"description":x.description} for x in session.scalars(select(DataSource).where(DataSource.connector_id==row.id)).all()]
        return data
    @staticmethod
    def _trace(session,row,mission_id,operation,started,status,summary):session.add(ConnectorTrace(connector_id=row.id,mission_id=mission_id,operation=operation,duration_ms=int((time.perf_counter()-started)*1000),status=status,result_summary=summary))
    def _trace_failure(self,session,connector_id,mission_id,operation,started,error):
        row=session.get(Connector,connector_id)
        if row:self._trace(session,row,mission_id,operation,started,"FAILED",f"Connector operation failed: {type(error).__name__}.")
    @staticmethod
    def _mission_event(session,mission_id,name,action,count):
        session.add(AIMissionEvent(mission_id=mission_id,stage="Connector",action=f"{name} · {action}",status="COMPLETED",evidence_count=0,result_summary=f"Read-only connector operation completed; {count} rows returned."))
