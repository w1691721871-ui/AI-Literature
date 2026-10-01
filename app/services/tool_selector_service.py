"""Policy-aware selection of existing controlled tool boundaries."""
class ToolSelector:
    agent_tools={"Research Agent":["KNOWLEDGE_CONNECTOR"],"Literature Agent":["KNOWLEDGE_CONNECTOR"],"Innovation Agent":["KNOWLEDGE_CONNECTOR"],"Risk Agent":["KNOWLEDGE_CONNECTOR"],"Computer Agent":["FILE_CONNECTOR","COMPUTER_AGENT"],"Delivery Agent":["FILE_CONNECTOR"]}
    def select(self, agents, *, requested_tools=None, policy=None, permission_check=None):
        selected=[]
        for agent in agents:
            for tool in self.agent_tools.get(agent,[]):
                if tool not in selected: selected.append(tool)
        if requested_tools is not None:
            selected=[tool for tool in selected if tool in requested_tools]
        allowed=(policy or {}).get("allowed_connectors",[])
        if allowed:
            selected=[tool for tool in selected if tool in allowed or tool=="COMPUTER_AGENT"]
        if permission_check: permission_check("CONNECTOR_ACCESS")
        return selected
