"""Pydantic contracts for the human-confirmed research decision loop."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ActionStatus = Literal["待执行", "进行中", "已完成", "已取消"]
DecisionStatus = Literal["待确认", "已采纳", "已修改", "已拒绝"]
OutcomeType = Literal["论文", "专利", "技术报告", "实验成果"]
OutcomeStatus = Literal["规划中", "进行中", "已完成", "已提交", "已归档"]
KnowledgeStatus = Literal["未沉淀", "待整理", "已沉淀"]


class EvidenceReference(BaseModel):
    """A compact pointer to existing evidence, never a copied source excerpt."""

    evidence_id: str = ""
    source: str = ""
    chapter: str = ""
    agent: str = ""
    score: float | None = None
    # Keep v1.1 clients compatible while they migrate to the clearer fields.
    title: str = ""
    detail: str = ""


class ResearchActionCreate(BaseModel):
    project_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    status: ActionStatus = "待执行"
    source_agent: str = Field(min_length=1, max_length=100)
    source_context: str = Field(min_length=1, max_length=8_000)
    rationale: str = Field(default="", max_length=4_000)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)


class ResearchActionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: ActionStatus | None = None


class ResearchActionResponse(BaseModel):
    id: str
    project_id: str | None
    title: str
    description: str
    status: ActionStatus
    source_agent: str
    source_context: str
    rationale: str
    evidence_refs: list[EvidenceReference]
    created_at: datetime
    updated_at: datetime


class ResearchDecisionCreate(BaseModel):
    action_id: str
    decision: DecisionStatus
    decided_by: str = Field(default="科研负责人", min_length=1, max_length=100)
    note: str = Field(default="", max_length=2_000)


class ResearchDecisionResponse(BaseModel):
    id: str
    action_id: str
    project_id: str | None
    action_title: str
    decision: DecisionStatus
    decided_by: str
    decided_at: datetime | None
    note: str
    created_at: datetime
    updated_at: datetime


class ResearchOutcomeCreate(BaseModel):
    outcome_type: OutcomeType
    title: str = Field(min_length=1, max_length=300)
    status: OutcomeStatus = "规划中"
    description: str = Field(default="", max_length=8_000)
    source_action_id: str | None = None


class ResearchOutcomeUpdate(BaseModel):
    outcome_type: OutcomeType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: OutcomeStatus | None = None
    description: str | None = Field(default=None, max_length=8_000)
    source_action_id: str | None = None


class KnowledgeStatusUpdate(BaseModel):
    knowledge_status: KnowledgeStatus


class ResearchOutcomeResponse(BaseModel):
    id: str
    project_id: str
    outcome_type: OutcomeType
    title: str
    status: OutcomeStatus
    description: str
    knowledge_status: KnowledgeStatus
    source_action_id: str | None
    created_at: datetime
    updated_at: datetime
