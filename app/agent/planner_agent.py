"""P26 deterministic Planner Agent: plan summaries only, never hidden reasoning."""
from app.services.agent_registry import AgentRegistry

class PlannerAgent:
    def __init__(self, registry=None): self.registry=registry or AgentRegistry()
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
        return {"goal":normalized,"required_agents":selected,"skip_agents":skipped,"reason_summary":reason,"execution_graph":nodes}
