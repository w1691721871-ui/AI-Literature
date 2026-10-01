"""P40 read-only product showcase projections over persisted platform records."""
from sqlalchemy import func,select
from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.models.paper_chunk import PaperChunk
from app.models.enterprise_memory import KnowledgeAsset
from app.models.agent_evaluation import AgentEvaluation
from app.models.benchmark import BenchmarkRun
from app.services.database import SessionLocal,initialize_database
class ProductShowcaseService:
 def __init__(self,sessions=SessionLocal,*,initialize=True):
  if initialize:initialize_database()
  self.s=sessions
 def overview(self):return {"product":"ResearchOS","subtitle":"Enterprise AI Agent Workspace","boundary":"DEMO_ONLY content describes platform flow, not a real customer, outcome, deployment, or benefit."}
 def workflow(self):return {"scenario":"智能制造AI质量优化方案","classification":"DEMO_ONLY","steps":[{"title":"Customer Need","summary":"企业希望提升质量分析效率。"},{"title":"Requirement Analysis","summary":"Business · Data · AI · System · Delivery · Security"},{"title":"AI Planning","summary":"Planner generates a reviewable task plan."},{"title":"Agent Team","summary":"Research · Solution · Risk · Delivery agents collaborate through the existing Mission Runtime."},{"title":"Evidence","summary":"Only existing Knowledge Base references can be used."},{"title":"Artifact","summary":"AI GENERATED DRAFT · Solution Document / Research Brief."},{"title":"Human Review","summary":"A reviewer must approve before delivery."},{"title":"Knowledge Memory","summary":"A completed Mission creates only a Decision Draft; approval is required for reuse."}]}
 def capabilities(self):return {"groups":[{"name":"Agent Intelligence","items":["Multi-Agent","Planning","Adaptive Loop"]},{"name":"Knowledge Intelligence","items":["RAG","Evidence","Memory"]},{"name":"Enterprise Delivery","items":["Artifact","Review","Governance"]},{"name":"Automation","items":["Connector","Computer Agent","Runtime"]}],"boundary":"Capabilities reference existing controlled platform modules; no Prompt or Chain-of-Thought is shown."}
 def releases(self):return {"releases":[["P21","FDE Solution Studio"],["P27","Adaptive Agent Loop"],["P30","Artifact Agent"],["P33","Governance"],["P39","Knowledge Memory"],["P40","Product Showcase Layer"]]}
 def business(self):
  s=self.s()
  try:
   count=lambda model:int(s.scalar(select(func.count(model))) or 0)
   missions=count(AIMission.id);arts=count(Artifact.id);evidence=count(PaperChunk.id);assets=count(KnowledgeAsset.id);evaluations=count(AgentEvaluation.id);benchmarks=count(BenchmarkRun.id)
   return {"missions":missions,"artifacts":arts,"evidence":evidence,"knowledge_assets":assets,"agent_evaluations":evaluations,"benchmark_runs":benchmarks,"data_state":"PRODUCTION_RECORDS" if any([missions,arts,evidence,assets,evaluations,benchmarks]) else "NO_PRODUCTION_DATA","boundary":"Counts are read from existing persisted records. Zero is shown as No Production Data and is never synthesized."}
  finally:s.close()
