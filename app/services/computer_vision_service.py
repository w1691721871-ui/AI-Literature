import json
from sqlalchemy import select
from app.models.computer_vision import ComputerVisionObservation,ComputerUIElement,ComputerSimulationSession
from app.models.computer_mission import ComputerMission
from app.services.database import SessionLocal,initialize_database
class ComputerVisionAnalyzer:
 def analyze_screen(self,goal):
  excel='excel' in goal.lower() or 'report' in goal.lower();elements=[{'type':'table','name':'Data Table','location':'center','confidence':.8},{'type':'button','name':'Export','location':'top_right','confidence':.75}] if excel else []
  return {'summary':'DEMO_ONLY structured vision simulation; no screenshot was captured.','elements':elements,'confidence':.8 if elements else 0}
class ComputerVisionService:
 def __init__(self,sessions=SessionLocal,*,initialize=True):
  if initialize:initialize_database()
  self.s=sessions;self.analyzer=ComputerVisionAnalyzer()
 def analyze(self,mid):
  s=self.s()
  try:
   m=s.get(ComputerMission,mid)
   if not m:raise ValueError('Computer mission not found.')
   r=self.analyzer.analyze_screen(m.task or m.mission_name);o=ComputerVisionObservation(mission_id=mid,environment_id='SAFE_ENVIRONMENT_REFERENCE',observation_type='SCREEN_ANALYSIS',detected_elements=json.dumps(r['elements']),screen_summary=r['summary'],confidence=r['confidence']);s.add(o)
   for e in r['elements']:s.add(ComputerUIElement(mission_id=mid,element_type=e['type'],name=e['name'],location=e['location'],confidence=e['confidence'],available_actions=json.dumps(['request_approval'])) )
   s.commit();return self.vision(mid)
  finally:s.close()
 def vision(self,mid):
  s=self.s()
  try:return [{'summary':x.screen_summary,'confidence':x.confidence,'elements':json.loads(x.detected_elements),'image_reference':x.image_reference} for x in s.scalars(select(ComputerVisionObservation).where(ComputerVisionObservation.mission_id==mid)).all()]
  finally:s.close()
 def elements(self,mid):
  s=self.s()
  try:return [{'type':x.element_type,'name':x.name,'location':x.location,'confidence':x.confidence,'available_actions':json.loads(x.available_actions)} for x in s.scalars(select(ComputerUIElement).where(ComputerUIElement.mission_id==mid)).all()]
  finally:s.close()
 def simulation(self,mid):
  s=self.s()
  try:
   x=s.scalar(select(ComputerSimulationSession).where(ComputerSimulationSession.mission_id==mid));return None if not x else {'id':x.id,'scenario':x.scenario,'current_screen':x.current_screen,'actions':json.loads(x.actions),'status':x.status}
  finally:s.close()
 def start(self,mid):
  s=self.s()
  try:
   if not s.get(ComputerMission,mid):raise ValueError('Computer mission not found.')
   x=ComputerSimulationSession(mission_id=mid,scenario='DEMO_ONLY · Excel Report Assistant',current_screen='Excel workspace simulated from structured metadata only.',actions=json.dumps(['Observe environment','Detect data table','Create plan','Request export approval']),status='WAITING_APPROVAL');s.add(x);s.commit();return self.simulation(mid)
  finally:s.close()
