from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceLocation:
    line: int | None = None
    column: int | None = None
    source_name: str | None = None


@dataclass
class IRNode:
    """Base class for dialect-neutral intermediate representation nodes."""
    location: SourceLocation | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
