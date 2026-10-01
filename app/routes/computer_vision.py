from fastapi import APIRouter,HTTPException
from app.services.computer_vision_service import ComputerVisionService
router=APIRouter(prefix='/api',tags=['computer-vision']);service=ComputerVisionService()
@router.get('/computer/vision/{mid}')
def vision(mid:str):return service.vision(mid)
@router.get('/computer/ui-elements/{mid}')
def elements(mid:str):return service.elements(mid)
@router.post('/computer/vision/analyze/{mid}')
def analyze(mid:str):
 try:return service.analyze(mid)
 except ValueError as e:raise HTTPException(404,detail=str(e))
@router.get('/computer/simulation/{mid}')
def simulation(mid:str):return service.simulation(mid)
@router.post('/computer/simulation/start')
def start(mission_id:str):
 try:return service.start(mission_id)
 except ValueError as e:raise HTTPException(404,detail=str(e))
