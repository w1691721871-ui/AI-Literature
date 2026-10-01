"""Read-only enterprise connector APIs."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.connector_service import ConnectorError, ConnectorManager

router=APIRouter(prefix="/api/connectors",tags=["connectors"])
service=ConnectorManager()

class ConnectorRegister(BaseModel):
    name:str
    type:str
    permission:str="READ_ONLY"
    config:dict=Field(default_factory=dict)

class DatabaseRequest(BaseModel):
    connector_id:str
    mission_id:str|None=None

class DatabaseQuery(DatabaseRequest):
    sql:str

class AttachDataSource(BaseModel):
    data_source_id:str

@router.get("")
def list_connectors(): return service.list()

@router.post("/register")
def register(payload:ConnectorRegister):
    try:return service.register(payload.model_dump())
    except ConnectorError as error:raise HTTPException(400,detail=str(error)) from error

@router.get("/analytics")
def analytics(): return service.analytics()

@router.get("/tools")
def tools(): return service.available_tools()

@router.post("/database/schema")
def schema(payload:DatabaseRequest):
    try:return service.schema(payload.connector_id,payload.mission_id)
    except ConnectorError as error:raise HTTPException(400,detail=str(error)) from error

@router.post("/database/query")
def query(payload:DatabaseQuery):
    try:return service.query(payload.connector_id,payload.sql,payload.mission_id)
    except ConnectorError as error:raise HTTPException(400,detail=str(error)) from error

@router.post("/missions/{mission_id}/data-sources")
def attach_source(mission_id:str,payload:AttachDataSource):
    try:return service.attach_mission_source(mission_id,payload.data_source_id)
    except ConnectorError as error:raise HTTPException(400,detail=str(error)) from error

@router.get("/{connector_id}")
def detail(connector_id:str):
    try:return service.detail(connector_id)
    except ConnectorError as error:raise HTTPException(404,detail=str(error)) from error

@router.get("/{connector_id}/traces")
def traces(connector_id:str):
    try:return service.traces(connector_id)
    except ConnectorError as error:raise HTTPException(404,detail=str(error)) from error
