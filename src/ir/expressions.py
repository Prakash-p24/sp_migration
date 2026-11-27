from dataclasses import dataclass, field

from src.ir.enums import ExpressionKind
from .nodes import IRNode


@dataclass
class RawExpression(IRNode):
    source_text: str = ""
    kind: ExpressionKind = ExpressionKind.RAW


@dataclass
class ColumnReference(IRNode):
    name: str = ""
    qualifier: str | None = None
    kind: ExpressionKind = ExpressionKind.COLUMN


@dataclass
class VariableReference(IRNode):
    name: str = ""
    kind: ExpressionKind = ExpressionKind.VARIABLE


@dataclass
class Literal(IRNode):
    value: str = ""
    literal_type: str | None = None
    kind: ExpressionKind = ExpressionKind.LITERAL


@dataclass
class UnaryExpression(IRNode):
    operator: str = ""
    operand: IRNode | None = None
    kind: ExpressionKind = ExpressionKind.UNARY


@dataclass
class BinaryExpression(IRNode):
    operator: str = ""
    left: IRNode | None = None
    right: IRNode | None = None
    kind: ExpressionKind = ExpressionKind.BINARY


@dataclass
class FunctionCall(IRNode):
    name: str = ""
    arguments: list[IRNode] = field(default_factory=list)
    kind: ExpressionKind = ExpressionKind.FUNCTION_CALL


@dataclass
class CaseExpression(IRNode):
    operand: IRNode | None = None
    branches: list[dict[str, IRNode | None]] = field(default_factory=list)
    else_expression: IRNode | None = None
    kind: ExpressionKind = ExpressionKind.CASE


@dataclass
class CastExpression(IRNode):
    expression: IRNode | None = None
    data_type: str = ""
    kind: ExpressionKind = ExpressionKind.CAST


@dataclass
class SubqueryExpression(IRNode):
    query: IRNode | None = None
    kind: ExpressionKind = ExpressionKind.SUBQUERY


@dataclass
class ExistsExpression(IRNode):
    query: IRNode | None = None
    negated: bool = False
    kind: ExpressionKind = ExpressionKind.EXISTS


@dataclass
class InExpression(IRNode):
    expression: IRNode | None = None
    values: list[IRNode] = field(default_factory=list)
    negated: bool = False
    kind: ExpressionKind = ExpressionKind.IN


@dataclass
class BetweenExpression(IRNode):
    expression: IRNode | None = None
    lower: IRNode | None = None
    upper: IRNode | None = None
    negated: bool = False
    kind: ExpressionKind = ExpressionKind.BETWEEN


@dataclass
class BooleanExpression(IRNode):
    operator: str = ""
    operands: list[IRNode] = field(default_factory=list)
    kind: ExpressionKind = ExpressionKind.BOOLEAN


@dataclass
class WindowExpression(IRNode):
    function: IRNode | None = None
    partition_by: list[IRNode] = field(default_factory=list)
    order_by: list[IRNode] = field(default_factory=list)
    frame: str | None = None
    kind: ExpressionKind = ExpressionKind.WINDOW


@dataclass
class AggregateExpression(IRNode):
    name: str = ""
    arguments: list[IRNode] = field(default_factory=list)
    distinct: bool = False
    kind: ExpressionKind = ExpressionKind.AGGREGATE
