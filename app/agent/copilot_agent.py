"""P28 first-entry Copilot. It emits an auditable summary, not CoT."""
from app.services.intent_service import IntentClassifier
class CopilotAgent:
    def __init__(self,classifier=None): self.classifier=classifier or IntentClassifier()
    def understand(self,text):
        intent=self.classifier.classify(text)
        goal=" ".join((text or "").strip().split())[:300]
        return {"intent":intent,"goal":goal,"required_workflow":self.classifier.mission_type(intent),"create_mission":True,"summary":f"已识别为 {intent} 任务；将创建可审阅 Mission 并交由现有 Planner 生成执行图。"}
