"""P36 benchmark APIs. Runs are explicit and stay inside the existing Mission runtime."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.benchmark_service import BenchmarkError, BenchmarkService
from app.services.governance_service import PermissionService, GovernanceError

router=APIRouter(prefix="/api",tags=["benchmarks"]); service=BenchmarkService()
class BenchmarkCreate(BaseModel):
    name:str=Field(min_length=1,max_length=180);category:str;difficulty:str;description:str=Field(min_length=1,max_length=4000)
    expected_agents:list[str]=Field(default_factory=list);expected_tools:list[str]=Field(default_factory=list);evaluation_rules:dict=Field(default_factory=dict)
class BenchmarkRunRequest(BaseModel):
    task_id:str;workspace_id:str|None=None;user_id:str|None=None;policy:dict=Field(default_factory=dict)
@router.get("/benchmarks")
def benchmarks():return service.list()
@router.post("/benchmarks")
def create(payload:BenchmarkCreate):
    try:return service.create(payload.model_dump())
    except BenchmarkError as error:raise HTTPException(status_code=400,detail=str(error)) from error
@router.post("/benchmarks/run")
def run(payload:BenchmarkRunRequest):
    try:
        permission=None
        if payload.workspace_id and payload.user_id: permission=lambda action:PermissionService().check(payload.workspace_id,payload.user_id,action)
        return service.run(payload.task_id,policy=payload.policy or None,permission_check=permission)
    except GovernanceError as error:raise HTTPException(status_code=403,detail=str(error)) from error
    except BenchmarkError as error:raise HTTPException(status_code=404,detail=str(error)) from error
@router.get("/benchmarks/{run_id}")
def benchmark(run_id:str):
    try:return service.detail(run_id)
    except BenchmarkError as error:raise HTTPException(status_code=404,detail=str(error)) from error
@router.get("/benchmark/dashboard")
def dashboard():return service.dashboard()
@router.get("/benchmark/regression")
def regression():return service.regression()
@router.get("/agent/versions/compare")
def versions():return service.regression()
