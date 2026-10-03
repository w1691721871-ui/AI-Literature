"""Read-only enterprise connector APIs."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.services.connector_service import ConnectorError, ConnectorManager
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware

router=APIRouter(prefix="/api/connectors",tags=["connectors"])
service=ConnectorManager()
permissions=PermissionMiddleware()

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
def list_connectors(context:IdentityContext=Depends(permissions.current)):
    permissions.require(context,"CONNECTOR_ACCESS");return service.list(context.workspace_id)

@router.post("/register")
def register(payload:ConnectorRegister,context:IdentityContext=Depends(permissions.current)):
    permissions.require(context,"CONNECTOR_ACCESS")
    try:return service.register({**payload.model_dump(),"workspace_id":context.workspace_id})
    except ConnectorError as error:raise HTTPException(400,detail=str(error)) from error

@router.get("/analytics")
def analytics(context:IdentityContext=Depends(permissions.current)):
    permissions.require(context,"CONNECTOR_ACCESS");return service.analytics()

@router.get("/tools")
def tools(context:IdentityContext=Depends(permissions.current)):
    permissions.require(context,"CONNECTOR_ACCESS");return service.available_tools()

@router.post("/database/schema")
def schema(payload:DatabaseRequest,context:IdentityContext=Depends(permissions.current)):
    permissions.connector(context,payload.connector_id)
    try:return service.schema(payload.connector_id,payload.mission_id)
    except ConnectorError as error:raise HTTPException(400,detail=str(error)) from error

@router.post("/database/query")
def query(payload:DatabaseQuery,context:IdentityContext=Depends(permissions.current)):
    permissions.connector(context,payload.connector_id)
    try:return service.query(payload.connector_id,payload.sql,payload.mission_id)
    except ConnectorError as error:raise HTTPException(400,detail=str(error)) from error

@router.post("/missions/{mission_id}/data-sources")
def attach_source(mission_id:str,payload:AttachDataSource,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_EXECUTE")
    try:return service.attach_mission_source(mission_id,payload.data_source_id)
    except ConnectorError as error:raise HTTPException(400,detail=str(error)) from error

@router.get("/{connector_id}")
def detail(connector_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.connector(context,connector_id)
    try:return service.detail(connector_id)
    except ConnectorError as error:raise HTTPException(404,detail=str(error)) from error

@router.get("/{connector_id}/traces")
def traces(connector_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.connector(context,connector_id)
    try:return service.traces(connector_id)
    except ConnectorError as error:raise HTTPException(404,detail=str(error)) from error
