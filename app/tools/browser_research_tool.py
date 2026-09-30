"""A connector contract for future web research; it performs no web control."""


class BrowserResearchTool:
    name = "browser_research_connector"
    description = "Connector interface for a future approved research browser. No browser is controlled in this version."

    def search(self, topic: str) -> dict[str, object]:
        return {"status": "connector_not_configured", "topic": topic, "candidate_sources": [], "boundary": "当前版本不控制浏览器，也不会生成或声称存在候选来源。"}
