from fastapi import APIRouter,HTTPException
from app.services.advanced_computer_service import AdvancedComputerService
router=APIRouter(prefix="/api",tags=["advanced-computer"]);service=AdvancedComputerService()
@router.get("/computer/environments/{mid}")
def environment(mid:str):return service.environment(mid)
@router.get("/computer/plans/{mid}")
def plan(mid:str):
 r=service.plan(mid)
 if not r:raise HTTPException(404,detail="Computer mission not found.")
 return r
@router.get("/computer/observations/{mid}")
def observations(mid:str):return service.observations(mid)
@router.post("/computer/plans/{pid}/approve")
def approve(pid:str):return service.approve(pid)
@router.post("/computer/actions/{aid}/verify")
def verify(aid:str):return {"action_id":aid,"success":False,"reason":"Use the existing controlled Computer Mission verification endpoint; this layer does not bypass approval."}
@router.get("/computer/experience")
def experience():return service.experience()
