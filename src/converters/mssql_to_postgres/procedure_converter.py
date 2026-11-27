"""Convert common MSSQL procedure IR into PostgreSQL-target IR."""

from copy import deepcopy
from dataclasses import fields, is_dataclass
import re

from src.converters.mssql_to_postgres.datatype_converter import MSSQLDataTypeConverter
from src.converters.mssql_to_postgres.statement_converter import MSSQLStatementConverter
from src.database.metadata_reader import load_data_type_mappings, load_syntax_mappings
from src.ir.procedure import Procedure
from src.ir.statements import Statement, UnsupportedStatement
from src.mappings.function_mapping import MSSQL_TO_POSTGRES as FUNCTION_MAPPINGS
from src.mappings.operator_mapping import MSSQL_TO_POSTGRES as OPERATOR_MAPPINGS


class MSSQLProcedureConverter:
    def convert(
        self,
        node: Procedure,
        datatype_mappings: dict[str, str] | None = None,
    ) -> Procedure:
        """Load type rules once, then map all type-bearing nodes in one pass."""
        if datatype_mappings is None:
            datatype_mappings = load_data_type_mappings(
                node.header.source_dialect or "mssql",
                node.header.target_dialect or "postgres",
                self._collect_source_types(node),
            )

        syntax_constructs = {"TOP"} if self._contains_top(node.body) else set()
        syntax_mappings = load_syntax_mappings(
            node.header.source_dialect or "mssql",
            node.header.target_dialect or "postgres",
            syntax_constructs,
        )

        converted = deepcopy(node)
        datatype_converter = MSSQLDataTypeConverter(datatype_mappings)
        statement_converter = MSSQLStatementConverter(datatype_mappings)
        warnings: list[dict[str, str]] = []
        typed_nodes = [
            *converted.parameters,
            *(item for item in converted.declarations if hasattr(item, "data_type")),
        ]
        if typed_nodes and not datatype_mappings:
            warnings.append({"code": "NO_DATA_TYPE_MAPPINGS_FOUND"})

        for parameter in converted.parameters:
            source_type = parameter.data_type
            mapped, found = datatype_converter.convert_with_status(source_type)
            parameter.data_type = mapped
            if not found:
                warnings.append({
                    "code": "TYPE_MAPPING_NOT_FOUND",
                    "source_type": source_type,
                    "location": self._location_text(parameter.location),
                })
            if parameter.default_value:
                parameter.default_value = statement_converter.expression_converter._map_text(
                    parameter.default_value
                )

        for declaration in converted.declarations:
            if not hasattr(declaration, "data_type"):
                continue
            source_type = declaration.data_type
            mapped, found = datatype_converter.convert_with_status(source_type)
            declaration.data_type = mapped
            if not found:
                warnings.append({
                    "code": "TYPE_MAPPING_NOT_FOUND",
                    "source_type": source_type,
                    "location": self._location_text(declaration.location),
                })
            if getattr(declaration, "initial_value", None):
                declaration.initial_value = statement_converter.expression_converter._map_text(
                    declaration.initial_value
                )
            if getattr(declaration, "query", None):
                declaration.query = statement_converter.expression_converter._map_text(
                    declaration.query
                )

        converted.body = [statement_converter.convert(item) for item in node.body]
        converted.exception_handlers = [
            statement_converter.convert(item) for item in node.exception_handlers
        ]
        warnings.extend(self._unsupported_warnings(converted.body))
        warnings.extend(self._raw_expression_warnings(converted.body))
        converted.header.target_dialect = "postgres"
        expression_converter = statement_converter.expression_converter
        source_sql = node.original_sql or ""
        available_functions = {
            source: target
            for source, target in FUNCTION_MAPPINGS.items()
            if re.search(rf"\b{re.escape(source)}\s*\(", source_sql, re.IGNORECASE)
        }
        available_operators = {
            source: target
            for source, target in OPERATOR_MAPPINGS.items()
            if source in source_sql
        }
        applied_types = [
            *datatype_converter.applied_mappings,
            *expression_converter.datatype_converter.applied_mappings,
        ]
        applied_types = list({(item["source"], item["target"]): item for item in applied_types}.values())
        applied_mappings = {
            "data_types": applied_types,
            "functions": expression_converter.applied_function_mappings,
            "operators": expression_converter.applied_operator_mappings,
            "syntax_rules": ([{"source": key, "target": value} for key, value in syntax_mappings.items()]
                             if syntax_constructs else []),
        }
        changes = [
            {"category": category, **mapping}
            for category, mappings in applied_mappings.items()
            for mapping in mappings
        ]
        unsupported_features = [
            warning
            for warning in warnings
            if warning.get("code") in {
                "STATEMENT_NOT_MAPPED",
                "EXPRESSION_REQUIRES_REVIEW",
                "TYPE_MAPPING_NOT_FOUND",
                "NO_DATA_TYPE_MAPPINGS_FOUND",
            }
        ]
        validation_errors = []
        required_sections_present = all(
            value is not None
            for value in (
                converted.header,
                converted.parameters,
                converted.declarations,
                converted.body,
                converted.exception_handlers,
                converted.metadata,
            )
        )
        if not required_sections_present:
            validation_errors.append("One or more required procedure IR sections are missing.")
        if converted.header.target_dialect != "postgres":
            validation_errors.append("Target IR dialect is not PostgreSQL.")
        validation_status = "failed" if validation_errors else "passed"
        conversion_status = (
            "failed"
            if validation_errors
            else "partial"
            if warnings
            else "mapped"
        )
        converted.metadata = {
            "source": {
                "dialect": node.header.source_dialect,
                "language": node.metadata.get("source_language", "TSQL"),
                "original_sql": node.original_sql,
            },
            "target": {
                "dialect": "postgres",
                "language": "PLPGSQL",
                "procedure_type": converted.header.procedure_type,
            },
            "conversion": {
                "status": conversion_status,
                "pipeline_stage": "ir_conversion",
                "generator_executed": False,
                "message": (
                    "Source IR was successfully mapped to PostgreSQL-target IR. SQL generation has not been performed."
                    if conversion_status == "mapped"
                    else "Source IR was mapped where rules were available. Review the warnings before SQL generation."
                ),
            },
            "conversion_mappings": {
                "available": {
                    "data_types": datatype_mappings,
                    "functions": available_functions,
                    "operators": available_operators,
                    "syntax_rules": syntax_mappings,
                },
                "applied": applied_mappings,
            },
            "changes": changes,
            "validation": {
                "status": validation_status,
                "scope": "IR structure and mapping trace; generated SQL was not validated",
                "checks": [
                    {"name": "required_ir_sections", "status": "passed" if required_sections_present else "failed"},
                    {"name": "postgres_target_set", "status": "passed" if converted.header.target_dialect == "postgres" else "failed"},
                ],
                "errors": validation_errors,
            },
            "warnings": warnings,
            "unsupported_features": unsupported_features,
        }
        return converted

    @classmethod
    def _collect_source_types(cls, value) -> set[str]:
        """Collect data types represented in this procedure IR only."""
        found: set[str] = set()

        def visit(item):
            if isinstance(item, dict):
                for key, child in item.items():
                    if key == "data_type" and isinstance(child, str):
                        found.add(child)
                    visit(child)
            elif isinstance(item, (list, tuple)):
                for child in item:
                    visit(child)
            elif is_dataclass(item):
                for field_ in fields(item):
                    child = getattr(item, field_.name)
                    if field_.name == "data_type" and isinstance(child, str):
                        found.add(child)
                    visit(child)

        visit(value)
        return found

    @classmethod
    def _contains_top(cls, value) -> bool:
        if isinstance(value, dict):
            return "top_limit" in value or any(cls._contains_top(child) for child in value.values())
        if isinstance(value, (list, tuple)):
            return any(cls._contains_top(child) for child in value)
        if is_dataclass(value):
            return any(
                field_.name == "top_limit" and getattr(value, field_.name) is not None
                or cls._contains_top(getattr(value, field_.name))
                for field_ in fields(value)
            )
        return False

    @classmethod
    def _unsupported_warnings(cls, statements: list[Statement]) -> list[dict[str, str]]:
        warnings = []
        for statement in statements:
            if isinstance(statement, UnsupportedStatement):
                warnings.append({
                    "code": "STATEMENT_NOT_MAPPED",
                    "statement_type": statement.statement_type.value,
                    "parser_rule": statement.parser_rule or "unknown",
                    "location": cls._location_text(statement.location),
                })
            warnings.extend(cls._unsupported_warnings(statement.body))
            warnings.extend(cls._unsupported_warnings(statement.else_body))
            warnings.extend(
                cls._unsupported_warnings(statement.attributes.get("catch_body", []))
            )
        return warnings

    @classmethod
    def _raw_expression_warnings(cls, statements: list[Statement]) -> list[dict[str, str]]:
        warnings = []
        for statement in statements:
            warnings.extend(cls._find_raw_expressions(statement.attributes))
            warnings.extend(cls._raw_expression_warnings(statement.body))
            warnings.extend(cls._raw_expression_warnings(statement.else_body))
            warnings.extend(
                cls._raw_expression_warnings(statement.attributes.get("catch_body", []))
            )
        return warnings

    @classmethod
    def _find_raw_expressions(cls, value) -> list[dict[str, str]]:
        from src.ir.expressions import RawExpression

        if isinstance(value, RawExpression) and value.metadata.get("expression_unclassified"):
            return [{
                "code": "EXPRESSION_REQUIRES_REVIEW",
                "source_text": value.source_text,
                "location": cls._location_text(value.location),
            }]
        if isinstance(value, dict):
            if value.get("kind") == "EXPRESSION":
                return [{
                    "code": "EXPRESSION_REQUIRES_REVIEW",
                    "source_text": str(value.get("source_text", "")),
                    "location": "unknown",
                }]
            return [warning for item in value.values() for warning in cls._find_raw_expressions(item)]
        if isinstance(value, (list, tuple)):
            return [warning for item in value for warning in cls._find_raw_expressions(item)]
        if is_dataclass(value):
            return [
                warning
                for item in fields(value)
                for warning in cls._find_raw_expressions(getattr(value, item.name))
            ]
        return []

    @staticmethod
    def _location_text(location) -> str:
        if location is None:
            return "unknown"
        return f"{location.line}:{location.column}"
