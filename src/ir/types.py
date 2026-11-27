from dataclasses import dataclass
from .nodes import IRNode


@dataclass
class DataType(IRNode):
    name: str = ""
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
