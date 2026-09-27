"""Explicit tool registry for the autonomous Research Brain."""

from app.tools.data_analysis_tool import DataAnalysisTool
from app.tools.document_tool import DocumentTool
from app.tools.knowledge_tool import KnowledgeTool
from app.tools.project_tool import ProjectTool
from app.tools.workspace_file_tool import WorkspaceFileTool


class ResearchToolRouter:
    """Route named, allow-listed tools; no arbitrary function or shell dispatch."""

    def __init__(self) -> None:
        self.file_tool = WorkspaceFileTool()
        self.knowledge_tool = KnowledgeTool()
        self.data_tool = DataAnalysisTool(self.file_tool)
        self.document_tool = DocumentTool()
        self.project_tool = ProjectTool()

    def catalog(self) -> list[dict[str, str]]:
        return [
            {"id": "workspace_file", "name": "File Tool", "description": "扫描和读取受限科研工作区中的 PDF、DOCX、TXT、CSV、Excel。"},
            {"id": "knowledge_retrieval", "name": "Knowledge Tool", "description": "调用现有 RAG、FAISS 和 Retriever 检索团队知识库。"},
            {"id": "data_analysis", "name": "Data Analysis Tool", "description": "对 CSV/XLSX 实验数据生成结构摘要，不执行任意代码。"},
            {"id": "document_generation", "name": "Document Tool", "description": "基于已有证据生成本地 Markdown 或 Word 报告。"},
            {"id": "project_planning", "name": "Project Tool", "description": "生成待负责人确认的项目方案，不自动创建项目记录。"},
        ]
