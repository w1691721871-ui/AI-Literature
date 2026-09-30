"""P21 orchestration façade; it reuses existing data services instead of a new AI black box."""

from app.services.fde_solution_service import FDESolutionService


class FDESolutionAgent:
    def __init__(self, service: FDESolutionService | None = None) -> None:
        self.service = service or FDESolutionService()

    def understand_requirements(self, solution_project_id: str) -> dict[str, object]:
        return self.service.analyze(solution_project_id)

    def prepare_solution(self, solution_project_id: str) -> dict[str, object]:
        return self.service.blueprint(solution_project_id)
