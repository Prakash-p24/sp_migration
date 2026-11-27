from src.parsers.base_parser import BaseParser


class MySQLParser(BaseParser):
    """Placeholder adapter. Implement after adding and generating MySQL grammar."""

    def parse(self, sql: str):
        raise NotImplementedError("MySQL grammar and generated parser are not implemented yet.")
