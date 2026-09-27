"""Explicit Research Worker tool selection; no arbitrary dispatch or shell access."""

from app.tools.research_worker.data_tool import DataTool
from app.tools.research_worker.document_tool import DocumentTool
from app.tools.research_worker.file_tool import FileTool
from app.tools.research_worker.knowledge_tool import KnowledgeTool
from app.tools.research_worker.project_tool import ProjectTool


class ResearchWorkerToolRouter:
    def __init__(self) -> None:
        self.file_tool = FileTool()
        self.data_tool = DataTool(self.file_tool._workspace)
        self.knowledge_tool = KnowledgeTool()
        self.document_tool = DocumentTool()
        self.project_tool = ProjectTool()

    def catalog(self) -> list[dict[str, str]]:
        return [{"name": tool.name, "description": tool.description} for tool in self._tools()]

    def select(self, goal: str) -> list[dict[str, str]]:
        lowered = goal.lower()
        selected = [{"name": "file_tool", "reason": "先读取真实科研工作区资料，确认可处理范围。"}]
        if any(word in lowered for word in ("数据", "实验", "csv", "xlsx", "excel", "表格")):
            selected.append({"name": "data_tool", "reason": "目标涉及实验或表格数据，需要先生成受控结构摘要。"})
        selected.append({"name": "knowledge_tool", "reason": "需要复用已索引论文的 RAG 证据，避免脱离资料生成结论。"})
        if any(word in goal for word in ("项目", "合作", "路线", "实验计划", "论文规划", "专利")):
            selected.append({"name": "project_tool", "reason": "目标包含研究或项目规划，需要形成待负责人确认的建议。"})
        selected.append({"name": "document_tool", "reason": "将可验证的工具结果整理为本地交付物。"})
        return selected

    def _tools(self) -> list[object]:
        return [self.file_tool, self.data_tool, self.knowledge_tool, self.document_tool, self.project_tool]
