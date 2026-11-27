from abc import ABC, abstractmethod
from typing import Any


class BaseParser(ABC):
    """Common interface for source-dialect parser adapters."""

    @abstractmethod
    def parse(self, sql: str) -> Any:
        """Parse SQL and return the dialect's ANTLR parse tree."""
        raise NotImplementedError
