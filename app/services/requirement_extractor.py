"""Deterministic requirement drafts aligned with the existing FDE requirement boundary."""
from __future__ import annotations


class RequirementExtractor:
    RULES = {
        "BUSINESS": ("业务", "客户", "效率", "生产", "project", "business", "customer"),
        "DATA": ("数据", "字段", "dataset", "data", "mes", "excel"),
        "AI": ("模型", "智能", "预测", "ai", "rag", "model"),
        "SYSTEM": ("系统", "平台", "接口", "部署", "system", "api", "integration"),
        "DELIVERY": ("交付", "验收", "培训", "报告", "delivery", "report", "training"),
        "SECURITY": ("安全", "权限", "隐私", "隔离", "security", "privacy", "access"),
    }

    def extract(self, text: str, structure: dict[str, object]) -> list[dict[str, str]]:
        haystack = f"{text} {structure}".lower(); drafts = []
        for category, keywords in self.RULES.items():
            if any(keyword in haystack for keyword in keywords):
                drafts.append({"category": category, "description": f"客户资料包含与 {category} 相关的线索；具体范围、优先级与验收口径需要客户确认。", "status": "NEEDS_CONFIRMATION"})
        return drafts or [{"category": "SYSTEM", "description": "资料已完成基础结构解析；尚未识别到可自动归类的明确需求，需客户确认任务范围。", "status": "NEEDS_CONFIRMATION"}]
