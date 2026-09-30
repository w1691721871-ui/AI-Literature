"""Safe input contracts for P20 product-experience metadata."""

from typing import Literal

from pydantic import BaseModel


class OnboardingStepComplete(BaseModel):
    step: Literal["welcome", "research", "workflow", "computer"]
