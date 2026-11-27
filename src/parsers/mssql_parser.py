from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from src.generated.mssql.TSqlLexer import TSqlLexer
from src.generated.mssql.TSqlParser import TSqlParser
from src.parsers.base_parser import BaseParser


class CollectingErrorListener(ErrorListener):
    def __init__(self):
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append({"line": line, "column": column, "message": msg})


class MSSQLParser(BaseParser):
    """Adapter around the generated ANTLR T-SQL lexer and parser."""

    def parse(self, sql: str):
        errors = CollectingErrorListener()
        lexer = TSqlLexer(InputStream(sql))
        lexer.removeErrorListeners()
        lexer.addErrorListener(errors)
        tokens = CommonTokenStream(lexer)
        parser = TSqlParser(tokens)
        parser.removeErrorListeners()
        parser.addErrorListener(errors)
        tree = parser.tsql_file()
        if errors.errors:
            raise ValueError(f"T-SQL parsing failed: {errors.errors}")
        return tree
