import json
from sqlalchemy import select
from app.models.advanced_computer import ComputerEnvironment,ComputerPlan,ComputerObservation,ComputerExperience
from app.models.computer_mission import ComputerMission
from app.services.database import SessionLocal,initialize_database
class AdvancedComputerService:
 def __init__(self,sessions=SessionLocal,*,initialize=True):
  if initialize:initialize_database()
  self.s=sessions
 def _mission(self,s,mid):return s.get(ComputerMission,mid) or s.scalar(select(ComputerMission).where(ComputerMission.mission_id==mid))
 def plan(self,mid):
  s=self.s()
  try:
   m=self._mission(s,mid)
   if not m:return None
   row=s.scalar(select(ComputerPlan).where(ComputerPlan.mission_id==m.id))
   if not row:row=ComputerPlan(mission_id=m.id,goal=m.task or m.mission_name,steps=json.dumps(["Observe controlled workspace","Prepare approval-gated action proposal","Execute only after approval","Verify result and request human review on failure"]),risk_level=m.risk_level,status="WAITING_APPROVAL");s.add(row);s.commit();s.refresh(row)
   return {"id":row.id,"mission_id":row.mission_id,"goal":row.goal,"steps":json.loads(row.steps),"risk_level":row.risk_level,"status":row.status}
  finally:s.close()
 def environment(self,mid):
  s=self.s()
  try:
   m=self._mission(s,mid)
   if not m:return []
   row=s.scalar(select(ComputerEnvironment).where(ComputerEnvironment.mission_id==m.id))
   if not row:row=ComputerEnvironment(mission_id=m.id,application="ResearchOS Controlled Workspace",window_title=m.mission_name,available_actions=json.dumps(["read_content","save_file","export_file"]),current_state=json.dumps({"approval":m.approval_status,"stage":m.current_stage}));s.add(row);s.flush();s.add(ComputerObservation(mission_id=m.id,environment_id=row.id,observation_type="STATE",summary="Environment metadata observed without capturing screen content.",detected_elements=json.dumps([m.current_stage])));s.commit()
   return [{"id":row.id,"application":row.application,"window_title":row.window_title,"screen_summary":row.screen_summary,"available_actions":json.loads(row.available_actions),"current_state":json.loads(row.current_state)}]
  finally:s.close()
 def observations(self,mid):
  s=self.s()
  try:return [{"type":x.observation_type,"summary":x.summary,"detected_elements":json.loads(x.detected_elements)} for x in s.scalars(select(ComputerObservation).where(ComputerObservation.mission_id==mid)).all()]
  finally:s.close()
 def approve(self,pid):
  s=self.s()
  try:r=s.get(ComputerPlan,pid);r.status="RUNNING";s.commit();return {"id":r.id,"status":r.status}
  finally:s.close()
 def experience(self):
  s=self.s()
  try:return [{"task_type":x.task_type,"solution_steps":json.loads(x.solution_steps),"success_rate":x.success_rate,"approval_status":x.approval_status} for x in s.scalars(select(ComputerExperience).where(ComputerExperience.approval_status=="APPROVED")).all()]
  finally:s.close()
