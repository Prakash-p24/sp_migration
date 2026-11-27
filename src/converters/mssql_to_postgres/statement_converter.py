"""Convert common statement nodes into PostgreSQL-target IR nodes."""

from copy import deepcopy

from src.converters.mssql_to_postgres.expression_converter import MSSQLExpressionConverter
from src.ir.statements import Statement, UnsupportedStatement


class MSSQLStatementConverter:
    def __init__(self, datatype_mappings: dict[str, str] | None = None):
        self.expression_converter = MSSQLExpressionConverter(datatype_mappings)

    def convert(self, node: Statement) -> Statement:
        """Convert known expressions recursively and retain statement ordering."""
        converted = deepcopy(node)
        if isinstance(converted, UnsupportedStatement):
            converted.metadata = {
                **converted.metadata,
                "conversion_status": "unsupported",
            }
            converted.attributes = deepcopy(node.attributes)
        else:
            converted.attributes = {
                key: self._convert_attribute(value)
                for key, value in node.attributes.items()
            }
        converted.body = [self.convert(item) for item in node.body]
        converted.else_body = [self.convert(item) for item in node.else_body]
        return converted

    def _convert_attribute(self, value):
        if isinstance(value, Statement):
            return self.convert(value)
        if isinstance(value, list):
            return [self._convert_attribute(item) for item in value]
        if isinstance(value, dict):
            return {key: self._convert_attribute(item) for key, item in value.items()}
        return self.expression_converter.convert(value)
