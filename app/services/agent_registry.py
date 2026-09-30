"""Deterministic registry of existing ResearchOS roles and safe capabilities."""
class AgentRegistry:
    _agents = {
        "Research Agent": ["mission_planning", "solution_orchestration"],
        "Literature Agent": ["paper_search", "evidence_retrieval"],
        "Innovation Agent": ["solution_draft", "research_opportunity"],
        "Risk Agent": ["risk_review", "security_review"],
        "Computer Agent": ["workspace_analysis", "controlled_verification"],
        "Delivery Agent": ["delivery_draft", "evidence_grounded_output"],
    }
    def list(self):
        return [{"agent_name": name, "capabilities": values} for name, values in self._agents.items()]
    def capabilities(self, name): return list(self._agents.get(name, []))
