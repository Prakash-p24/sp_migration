from src.parsers.base_parser import BaseParser


class PostgreSQLParser(BaseParser):
    """Optional parser adapter for validating generated PostgreSQL SQL.

    No PostgreSQL ANTLR grammar is included in this project yet. Consider using
    PostgreSQL PREPARE/EXPLAIN or a dedicated PostgreSQL parser for validation.
    """

    def parse(self, sql: str):
        raise NotImplementedError("PostgreSQL output parser is not configured.")
