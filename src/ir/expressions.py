from dataclasses import dataclass
from .nodes import IRNode


@dataclass
class RawExpression(IRNode):
    source_text: str = ""
