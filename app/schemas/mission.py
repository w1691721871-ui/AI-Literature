"""Public contracts for the AI Mission Center."""

from pydantic import BaseModel, Field


class AIMissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    mission_type: str = Field(default="RESEARCH", min_length=1, max_length=80)
    goal: str = Field(default="", max_length=8_000)
