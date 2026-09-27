"""Prepare project outputs without silently creating project records."""


class ProjectTool:
    name = "project_planning"

    @staticmethod
    def prepare(project_plan: object) -> dict[str, object]:
        """Return a reviewable project proposal for later human confirmation."""
        return {
            "proposal": project_plan if isinstance(project_plan, dict) else {},
            "status": "待负责人确认后创建项目",
            "boundary_note": "该工具仅形成项目建议，不会自动创建项目、行动或成果记录。",
        }
