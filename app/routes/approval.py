from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.services.approval_service import ApprovalError, ApprovalService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware

router=APIRouter(prefix="/api/approvals",tags=["approvals"])
service=ApprovalService();permissions=PermissionMiddleware()
class Create(BaseModel):
 source_type:str=Field(min_length=1,max_length=40);source_id:str=Field(min_length=1,max_length=36);request_type:str;priority:str="NORMAL";comment:str=""
class Decision(BaseModel):comment:str=""
@router.post("",status_code=status.HTTP_201_CREATED)
def create(payload:Create,context:IdentityContext=Depends(permissions.current)):
 permissions.require(context,"MISSION_CREATE")
 try:return service.create_request(context,payload.source_type,payload.source_id,payload.request_type,payload.priority,payload.comment)
 except ApprovalError as error:raise HTTPException(400,detail=str(error)) from error
@router.get("")
def list_items(context:IdentityContext=Depends(permissions.current)):
 permissions.require(context,"MISSION_VIEW");return service.list_pending(context)
@router.get("/{request_id}")
def detail(request_id:str,context:IdentityContext=Depends(permissions.current)):
 permissions.require(context,"MISSION_VIEW")
 try:return service.get_request(context,request_id)
 except ApprovalError as error:raise HTTPException(404,detail=str(error)) from error
def _review(context,request_id,payload,action):
 permissions.require(context,"ARTIFACT_REVIEW")
 try:return action(context,request_id,payload.comment)
 except ApprovalError as error:raise HTTPException(400,detail=str(error)) from error
@router.post("/{request_id}/approve")
def approve(request_id:str,payload:Decision,context:IdentityContext=Depends(permissions.current)):return _review(context,request_id,payload,service.approve_request)
@router.post("/{request_id}/reject")
def reject(request_id:str,payload:Decision,context:IdentityContext=Depends(permissions.current)):return _review(context,request_id,payload,service.reject_request)
@router.post("/{request_id}/changes")
def changes(request_id:str,payload:Decision,context:IdentityContext=Depends(permissions.current)):return _review(context,request_id,payload,service.request_changes)
