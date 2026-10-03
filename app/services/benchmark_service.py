"""Benchmark runner that scores existing Mission records without fabricating results."""
from __future__ import annotations
import json
from sqlalchemy import func, select
from app.models.agent_trace import AgentTrace
from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.models.benchmark import AgentVersion,BenchmarkRun,BenchmarkScore,BenchmarkTask
from app.services.ai_mission_service import AIMissionService
from app.services.agent_runtime_loop import AgentRuntimeLoop
from app.services.database import SessionLocal,initialize_database
from app.services.llm_gateway import LLMGateway

class BenchmarkError(ValueError):pass
class BenchmarkService:
    categories={"RESEARCH","ENTERPRISE","DATA","COMPUTER"}; difficulties={"EASY","MEDIUM","HARD"}
    def __init__(self,sessions=SessionLocal,*,initialize=True,missions=None,runtime=None):
        if initialize:initialize_database()
        self.s=sessions;self.missions=missions or AIMissionService(sessions,initialize=False);self.runtime=runtime or AgentRuntimeLoop(sessions,initialize=False)
    def create(self,data):
        if data.get("category") not in self.categories or data.get("difficulty") not in self.difficulties:raise BenchmarkError("Invalid benchmark category or difficulty.")
        s=self.s()
        try:
            row=BenchmarkTask(name=data["name"].strip(),category=data["category"],difficulty=data["difficulty"],description=data["description"].strip(),expected_agents_json=json.dumps(data.get("expected_agents",[])),expected_tools_json=json.dumps(data.get("expected_tools",[])),evaluation_rules_json=json.dumps(data.get("evaluation_rules",{})));s.add(row);s.commit();s.refresh(row);return self._task(row)
        finally:s.close()
    def list(self):
        s=self.s()
        try:return [self._task(x) for x in s.scalars(select(BenchmarkTask).order_by(BenchmarkTask.created_at.desc())).all()]
        finally:s.close()
    def run(self,task_id,*,workspace_id=None,policy=None,permission_check=None):
        s=self.s()
        try: task=s.get(BenchmarkTask,task_id)
        finally:s.close()
        if not task:raise BenchmarkError("Benchmark task not found.")
        if permission_check:permission_check("MISSION_CREATE")
        mission_payload={"title":f"Benchmark · {task.name}","mission_type":task.category,"goal":task.description}
        if workspace_id:
            mission_payload["workspace_id"]=workspace_id
        mission=self.missions.create(mission_payload)
        config=LLMGateway().configuration();s=self.s()
        try:
            run=BenchmarkRun(task_id=task.id,mission_id=mission["id"],runtime_version="P36",planner_version="v1",model_version=config["model"]);s.add(run);s.add(AgentVersion(runtime_version=run.runtime_version,planner_version=run.planner_version,model_version=run.model_version));s.commit();s.refresh(run)
        finally:s.close()
        try:
            runtime_result=self.runtime.execute(mission["id"],policy=policy,permission_check=permission_check)
            return self.score(run.id,runtime_result)
        except Exception:
            return self._fail(run.id)
    def track_existing_mission(self, data, mission_id, runtime_result):
        """Score a completed existing Mission; never starts a second benchmark flow."""
        task = self.create(data)
        s = self.s()
        try:
            mission = s.get(AIMission, mission_id)
            if not mission: raise BenchmarkError("Mission not found for benchmark observation.")
            config = LLMGateway().configuration()
            run = BenchmarkRun(task_id=task["id"], mission_id=mission_id, runtime_version="P36", planner_version="v1", model_version=config["model"])
            s.add(run); s.add(AgentVersion(runtime_version=run.runtime_version, planner_version=run.planner_version, model_version=run.model_version)); s.commit(); s.refresh(run)
            run_id = run.id
        finally: s.close()
        return self.score(run_id, runtime_result)
    def score(self,run_id,runtime_result=None):
        s=self.s()
        try:
            run=s.get(BenchmarkRun,run_id);task=s.get(BenchmarkTask,run.task_id);mission=s.get(AIMission,run.mission_id)
            if not run or not task or not mission:raise BenchmarkError("Benchmark records are incomplete.")
            traces=s.scalars(select(AgentTrace).where(AgentTrace.mission_id==mission.id)).all();artifacts=s.scalars(select(Artifact).where(Artifact.mission_id==mission.id)).all()
            expected_agents=self._array(task.expected_agents_json);expected_tools=self._array(task.expected_tools_json);actual_agents={x.agent_name for x in traces};actual_tools={x.tool_used for x in traces}
            planning=self._coverage(expected_agents,actual_agents);tools=self._coverage(expected_tools,actual_tools);evidence=min(100,len(self._array(mission.evidence_refs_json))*20);artifact=min(100,len(artifacts)*50);safety=0 if any(x.status in {"BLOCKED","UNSAFE"} for x in traces) else 100;human=100 if mission.status in {"WAITING_REVIEW","WAITING_ADAPTIVE_REVIEW"} else 50
            total=round((planning+tools+evidence+artifact+safety+human)/6,1);row=s.scalar(select(BenchmarkScore).where(BenchmarkScore.benchmark_id==run.id)) or BenchmarkScore(benchmark_id=run.id);row.planning_score,row.tool_score,row.evidence_score,row.artifact_score,row.safety_score,row.human_score,row.total_score=planning,tools,evidence,artifact,safety,human,total;s.add(row);run.status="SUCCESS" if runtime_result is not None else "FAILED";run.score=total;s.commit();return self.detail(run.id)
        finally:s.close()
    def track_existing_mission(self, data, mission_id, runtime_result):
        """Score an existing Mission; this deliberately does not launch a second flow."""
        task=self.create(data);s=self.s()
        try:
            if not s.get(AIMission,mission_id):raise BenchmarkError("Mission not found for benchmark observation.")
            config=LLMGateway().configuration();run=BenchmarkRun(task_id=task["id"],mission_id=mission_id,runtime_version="P36",planner_version="v1",model_version=config["model"])
            s.add(run);s.add(AgentVersion(runtime_version=run.runtime_version,planner_version=run.planner_version,model_version=run.model_version));s.commit();s.refresh(run);run_id=run.id
        finally:s.close()
        return self.score(run_id,runtime_result)
    def detail(self,run_id):
        s=self.s()
        try:
            run=s.get(BenchmarkRun,run_id)
            if not run:raise BenchmarkError("Benchmark run not found.")
            score=s.scalar(select(BenchmarkScore).where(BenchmarkScore.benchmark_id==run.id));return {"id":run.id,"task_id":run.task_id,"mission_id":run.mission_id,"status":run.status,"score":run.score,"version":{"runtime":run.runtime_version,"planner":run.planner_version,"model":run.model_version},"scores":self._score(score),"trace_summary":"Only persisted Agent Trace metadata is evaluated; no prompt, CoT, private content or synthetic result is stored.","created_at":run.created_at}
        finally:s.close()
    def dashboard(self):
        s=self.s()
        try:
            runs=s.scalars(select(BenchmarkRun)).all();scores=s.scalars(select(BenchmarkScore)).all();successful=[x for x in runs if x.status=="SUCCESS"];return {"benchmarks":int(s.scalar(select(func.count(BenchmarkTask.id)))or 0),"runs":len(runs),"average_score":round(sum(x.total_score for x in scores)/len(scores),1) if scores else 0,"success_rate":round(len(successful)/len(runs)*100,1) if runs else 0,"capabilities":{key:round(sum(getattr(x,key) for x in scores)/len(scores),1) if scores else 0 for key in ("planning_score","tool_score","evidence_score","artifact_score","safety_score","human_score")},"boundary":"Zero means no real benchmark run has produced an observed score; it is not a synthetic baseline."}
        finally:s.close()
    def regression(self):
        s=self.s()
        try:
            result=[]
            for task in s.scalars(select(BenchmarkTask)).all():
                runs=s.scalars(select(BenchmarkRun).where(BenchmarkRun.task_id==task.id).order_by(BenchmarkRun.created_at.desc())).all()
                if len(runs)>=2 and runs[0].score is not None and runs[1].score is not None:result.append({"task_id":task.id,"latest":runs[0].score,"previous":runs[1].score,"regression":runs[0].score<runs[1].score})
            return result
        finally:s.close()
    def _fail(self,run_id):
        s=self.s()
        try:run=s.get(BenchmarkRun,run_id);run.status="FAILED";s.commit();return self.detail(run_id)
        finally:s.close()
    @staticmethod
    def _coverage(expected,actual):return 100 if not expected else round(len(set(expected)&set(actual))/len(set(expected))*100)
    @staticmethod
    def _array(value):
        try:return json.loads(value or "[]")
        except (TypeError,json.JSONDecodeError):return []
    @staticmethod
    def _task(x):return {"id":x.id,"name":x.name,"category":x.category,"difficulty":x.difficulty,"description":x.description,"expected_agents":BenchmarkService._array(x.expected_agents_json),"expected_tools":BenchmarkService._array(x.expected_tools_json),"evaluation_rules":BenchmarkService._array(x.evaluation_rules_json) if x.evaluation_rules_json.startswith("[") else json.loads(x.evaluation_rules_json or "{}"),"created_at":x.created_at}
    @staticmethod
    def _score(x):return {"planning":x.planning_score,"tool":x.tool_score,"evidence":x.evidence_score,"artifact":x.artifact_score,"safety":x.safety_score,"human":x.human_score,"total":x.total_score} if x else None
