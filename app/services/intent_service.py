"""Deterministic intent classification; no LLM call or hidden reasoning."""
class IntentClassifier:
    def classify(self,text):
        value=(text or "").strip(); lowered=value.lower()
        if any(word in lowered for word in ("code","api","bug","ui","python","代码","接口","修复","优化")): return "COMPUTER"
        if any(word in value for word in ("企业","方案","交付","客户","项目申报")): return "SOLUTION"
        if any(word in value for word in ("报告","综述","总结","报告生成")): return "REPORT"
        if any(word in value for word in ("知识库","问答","资料查询")): return "KNOWLEDGE"
        return "RESEARCH"
    @staticmethod
    def mission_type(intent): return "SOLUTION" if intent=="SOLUTION" else ("DELIVERY" if intent=="REPORT" else "RESEARCH")
