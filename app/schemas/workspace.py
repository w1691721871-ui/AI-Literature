"""Public request models for the lightweight workspace product layer."""

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    member_roles: list[str] = Field(default_factory=lambda: ["实验室负责人", "学生/研究人员", "企业合作方"])


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    task_type: str = Field(pattern="^(文献分析|数据分析|企业需求分析|技术路线规划)$")
    worker_run_id: str = ""
    project_id: str | None = None
    decision_id: str | None = None
    evidence_refs: list[dict[str, object]] = Field(default_factory=list)


class DeliveryExportRequest(BaseModel):
    worker_run_id: str = Field(min_length=1)
