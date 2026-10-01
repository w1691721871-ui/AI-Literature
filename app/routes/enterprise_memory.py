from fastapi import APIRouter,HTTPException
from app.services.enterprise_memory_service import DecisionMemoryService,MemoryError
from app.services.governance_service import GovernanceError
router=APIRouter(prefix="/api",tags=["enterprise-memory"]);service=DecisionMemoryService()
@router.get("/knowledge/assets")
def assets():return service.assets()
@router.get("/knowledge/assets/{ident}")
def asset(ident:str):
 rows=service.assets(ident)
 if not rows:raise HTTPException(404,detail="Knowledge asset not found.")
 return rows[0]
@router.get("/knowledge/decisions")
def decisions():return service.decisions()
@router.post("/knowledge/decisions/{ident}/approve")
def approve(ident:str,workspace_id:str,user_id:str):
 try:return service.approve(ident,workspace_id,user_id)
 except GovernanceError as e:raise HTTPException(403,detail=str(e))
 except MemoryError as e:raise HTTPException(404,detail=str(e))
@router.get("/knowledge/experience/search")
def search(query:str):return service.experiences.search(query)
@router.get("/knowledge/dashboard")
def dashboard():return service.dashboard()
