"""Common dialect-neutral models used by source builders and converters."""

from src.ir.procedure import Procedure, ProcedureHeader, ProcedureParameter
from src.ir.statements import Statement, UnsupportedStatement

__all__ = [
    "Procedure",
    "ProcedureHeader",
    "ProcedureParameter",
    "Statement",
    "UnsupportedStatement",
]
