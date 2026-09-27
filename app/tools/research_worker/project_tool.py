"""Human-review project assistance adapter for Research Worker."""

from app.tools.project_tool import ProjectTool as ExistingProjectTool
from app.tools.research_worker.base import Tool


class ProjectTool(Tool):
    name = "project_tool"
    description = "形成实验计划、技术路线或论文规划建议，等待负责人确认。"

    def execute(self, goal: str, evidence_count: int) -> dict[str, object]:
        proposal = {
            "research_goal": goal,
            "experiment_plan": "请基于已引用资料由负责人补充实验变量、评价指标和安全条件。",
            "technology_route": "以当前资料检索结果为输入，形成待复核的技术路线草案。",
            "paper_plan": "在获得可复现实验或验证数据后，再确认论文选题与投稿路径。",
            "evidence_count": evidence_count,
        }
        return ExistingProjectTool.prepare(proposal)
