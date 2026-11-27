from dataclasses import dataclass, field
from .nodes import IRNode


@dataclass
class RawStatement(IRNode):
    """Temporary escape hatch for syntax not yet represented by typed IR nodes."""
    source_sql: str = ""


@dataclass
class BlockStatement(IRNode):
    statements: list[IRNode] = field(default_factory=list)
