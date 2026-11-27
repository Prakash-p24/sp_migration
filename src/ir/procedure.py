from dataclasses import dataclass, field
from .nodes import IRNode


@dataclass
class ProcedureParameter(IRNode):
    name: str = ""
    data_type: str = ""
    mode: str = "IN"
    default_value: str | None = None


@dataclass
class Procedure(IRNode):
    name: str = ""
    schema: str | None = None
    parameters: list[ProcedureParameter] = field(default_factory=list)
    declarations: list[IRNode] = field(default_factory=list)
    body: list[IRNode] = field(default_factory=list)
