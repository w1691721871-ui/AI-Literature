"""Minimal common contract for all bounded Research Worker tools."""

from abc import ABC, abstractmethod


class Tool(ABC):
    """Allow-listed tool contract; implementations never dispatch arbitrary code."""

    name: str
    description: str

    @abstractmethod
    def execute(self, *args, **kwargs) -> dict[str, object]:
        """Run one bounded, research-specific operation."""
