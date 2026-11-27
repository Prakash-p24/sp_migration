"""Reusable recursive statement nodes for procedure bodies."""

from dataclasses import dataclass, field
from typing import Any

from src.ir.enums import StatementKind
from src.ir.nodes import IRNode


@dataclass
class Statement(IRNode):
    """A normalized statement with extensible attributes and nested bodies."""

    statement_type: StatementKind = StatementKind.OTHER
    intent: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    body: list["Statement"] = field(default_factory=list)
    else_body: list["Statement"] = field(default_factory=list)


@dataclass
class UnsupportedStatement(Statement):
    """Unmapped source syntax retained so the builder never silently drops it."""

    statement_type: StatementKind = StatementKind.UNSUPPORTED
    parser_rule: str | None = None


@dataclass
class RawStatement(UnsupportedStatement):
    """Compatibility node for callers of the previous raw SQL model."""

    source_sql: str = ""


@dataclass
class BlockStatement(Statement):
    """Compatibility node; new builders use Statement with kind BLOCK."""

    statement_type: StatementKind = StatementKind.BLOCK
    statements: list[Statement] = field(default_factory=list)
