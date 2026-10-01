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
    _communication = {
        "Research Agent": ["CAN_REQUEST_EVIDENCE", "CAN_REQUEST_SUMMARY"],
        "Literature Agent": ["CAN_RETURN_EVIDENCE"],
        "Innovation Agent": ["CAN_REQUEST_SUMMARY", "CAN_RETURN_PROPOSAL"],
        "Risk Agent": ["CAN_SEND_WARNING"],
        "Computer Agent": ["CAN_RETURN_VERIFICATION"],
        "Delivery Agent": ["CAN_REQUEST_SUMMARY", "CAN_RETURN_DELIVERY_DRAFT"],
    }
    def list(self):
        return [{"agent_name": name, "capabilities": values, "communication_capability": self._communication.get(name, [])} for name, values in self._agents.items()]
    def capabilities(self, name): return list(self._agents.get(name, []))
    def communication_capabilities(self, name): return list(self._communication.get(name, []))
