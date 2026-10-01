"""P26 deterministic Planner Agent: plan summaries only, never hidden reasoning."""
from app.services.agent_registry import AgentRegistry
from app.services.llm_gateway import LLMGateway

class PlannerAgent:
    def __init__(self, registry=None, gateway=None): self.registry=registry or AgentRegistry(); self.gateway=gateway or LLMGateway()
    def analyze(self, goal: str, mission_type: str = "RESEARCH", memory_context=None):
        normalized=(goal or "").strip()
        if not normalized: raise ValueError("请输入客户需求或研究目标。")
        lowered=normalized.lower()
        selected=["Research Agent", "Literature Agent"]
        if any(word in normalized for word in ("方案","交付","项目")) or mission_type in {"SOLUTION","DELIVERY"}: selected.append("Innovation Agent")
        if any(word in normalized for word in ("风险","安全","合规","审核")) or mission_type in {"SOLUTION","DELIVERY"}: selected.append("Risk Agent")
        implementation = any(word in lowered for word in ("code", "api", "ui", "bug", "python", "前端", "代码", "接口", "修复", "实现"))
        if implementation: selected.append("Computer Agent")
        selected.append("Delivery Agent")
        skipped=[name for name in self.registry._agents if name not in selected]
        reason="基于研究目标选择检索、方案、风险与交付能力。"
        if not implementation: reason+=" 未检测到实现或代码变更任务，因此跳过 Computer Agent。"
        if memory_context: reason+=f" 已参考 {len(memory_context)} 条经人工确认的相关历史摘要。"
        nodes=[]
        for index,name in enumerate(selected, start=1):
            nodes.append({"node_name": name.replace(" Agent", ""), "agent_name": name, "status":"PENDING", "order":index, "depends_on": [] if index==1 else [selected[index-2]]})
        generated, metadata = self.gateway.generate_plan(normalized, mission_type, list(self.registry._agents), ["KNOWLEDGE_CONNECTOR","FILE_CONNECTOR","DATABASE_CONNECTOR","COMPUTER_AGENT"])
        source="DETERMINISTIC_FALLBACK"
        tools=[]; steps=[]; risks=[]
        if isinstance(generated,dict):
            candidate_agents=generated.get("agents",[])
            candidate_steps=generated.get("steps",[])
            candidate_tools=generated.get("tools",[])
            if candidate_agents and all(item in self.registry._agents for item in candidate_agents) and candidate_steps and all(isinstance(item,str) for item in candidate_steps):
                selected=list(dict.fromkeys(candidate_agents)); skipped=[name for name in self.registry._agents if name not in selected]
                nodes=[{"node_name":name.replace(" Agent", ""),"agent_name":name,"status":"PENDING","order":index,"depends_on":[] if index==1 else [selected[index-2]]} for index,name in enumerate(selected,1)]
                tools=[item for item in candidate_tools if item in {"KNOWLEDGE_CONNECTOR","FILE_CONNECTOR","DATABASE_CONNECTOR","COMPUTER_AGENT"}]
                steps=[item[:200] for item in candidate_steps]
                risks=[item[:300] for item in generated.get("risk_points",[]) if isinstance(item,str)]
                source="LLM_VALIDATED"
                reason="LLM 生成的结构化计划已通过 Agent 与步骤白名单校验；执行仍受系统权限、Policy 与人工审核约束。"
        return {"goal":normalized,"required_agents":selected,"skip_agents":skipped,"reason_summary":reason,"execution_graph":nodes,"tools":tools,"steps":steps,"risk_points":risks,"plan_source":source,"model_metadata":{key:metadata.get(key) for key in ("status","model","latency","token_usage_summary")}}
