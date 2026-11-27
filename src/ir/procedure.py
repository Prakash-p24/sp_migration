from dataclasses import dataclass, field
from typing import Any

from src.ir.nodes import IRNode, SourceLocation
from src.ir.statements import Statement

@dataclass
class ProcedureHeader:
    procedure_name: str = ""
    schema: str | None = None
    source_dialect: str = ""
    target_dialect: str = ""
    procedure_type: str = "PROCEDURE"
    location: SourceLocation | None = None
    original_sql: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcedureParameter:
    name: str
    data_type: str
    mode: str = "IN"
    default_value: str | None = None
    data_type_metadata: dict[str, Any] = field(default_factory=dict)
    location: SourceLocation | None = None
    original_sql: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VariableDeclaration:
    name: str
    data_type: str
    initial_value: str | None = None
    location: SourceLocation | None = None
    original_sql: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CursorDeclaration:
    name: str
    query: str | None = None
    options: list[str] = field(default_factory=list)
    location: SourceLocation | None = None
    original_sql: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Procedure(IRNode):
    header: ProcedureHeader = field(default_factory=ProcedureHeader)
    parameters: list[ProcedureParameter] = field(default_factory=list)
    declarations: list[IRNode] = field(default_factory=list)
    body: list[Statement] = field(default_factory=list)
    exception_handlers: list[Statement] = field(default_factory=list)
    metadata: dict[str, str] = field(
        default_factory=lambda: {"source_language": "TSQL"}
    )
