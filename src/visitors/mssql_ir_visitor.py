"""Build the common IR from the generated T-SQL parse tree.

Implement incrementally using generated TSqlParserVisitor methods. Keep generated
ANTLR files unmodified; this module is application-owned code.
"""
from src.generated.mssql.TSqlParserVisitor import TSqlParserVisitor


class MSSQLIRVisitor(TSqlParserVisitor):
    pass
