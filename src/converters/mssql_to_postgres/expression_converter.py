"""MSSQL expression IR to PostgreSQL-target IR mappings."""

import re
from copy import deepcopy
from dataclasses import fields, is_dataclass

from src.ir.expressions import (
    AggregateExpression,
    BinaryExpression,
    BooleanExpression,
    CaseExpression,
    CastExpression,
    ExistsExpression,
    FunctionCall,
    InExpression,
    RawExpression,
    SubqueryExpression,
    UnaryExpression,
    WindowExpression,
)
from src.ir.procedure import VariableDeclaration
from src.mappings.function_mapping import MSSQL_TO_POSTGRES as FUNCTION_MAPPING
from src.mappings.operator_mapping import MSSQL_TO_POSTGRES as OPERATOR_MAPPING
from src.converters.mssql_to_postgres.datatype_converter import MSSQLDataTypeConverter


class MSSQLExpressionConverter:
    """Apply known function/operator mappings recursively to expression IR."""

    def __init__(self, datatype_mappings: dict[str, str] | None = None):
        self.datatype_converter = MSSQLDataTypeConverter(datatype_mappings)
        self.applied_function_mappings: list[dict[str, str]] = []
        self.applied_operator_mappings: list[dict[str, str]] = []

    def convert(self, node):
        if isinstance(node, VariableDeclaration):
            converted = deepcopy(node)
            mapped, _ = self.datatype_converter.convert_with_status(node.data_type)
            converted.data_type = mapped
            if node.initial_value:
                converted.initial_value = self._map_text(node.initial_value)
            return converted
        if isinstance(node, RawExpression):
            converted = deepcopy(node)
            converted.source_text = self._map_text(node.source_text)
            return converted
        if isinstance(node, FunctionCall):
            converted = deepcopy(node)
            mapped_name = FUNCTION_MAPPING.get(node.name.upper(), node.name)
            if mapped_name != node.name and "(" not in mapped_name:
                self._record(self.applied_function_mappings, node.name, mapped_name)
            if "(" in mapped_name:
                self._record(self.applied_function_mappings, node.name, mapped_name)
                return RawExpression(
                    source_text=mapped_name,
                    location=node.location,
                    original_sql=node.original_sql,
                    metadata=dict(node.metadata),
                )
            converted.name = mapped_name
            converted.arguments = [self.convert(item) for item in node.arguments]
            return converted
        if isinstance(node, BinaryExpression):
            converted = deepcopy(node)
            converted.operator = OPERATOR_MAPPING.get(node.operator, node.operator)
            converted.left = self.convert(node.left) if node.left else None
            converted.right = self.convert(node.right) if node.right else None
            return converted
        if isinstance(node, (UnaryExpression, CastExpression)):
            converted = deepcopy(node)
            for item in fields(node):
                value = getattr(node, item.name)
                if is_dataclass(value):
                    setattr(converted, item.name, self.convert(value))
                elif isinstance(value, (list, dict)):
                    setattr(converted, item.name, self.convert(value))
            if isinstance(converted, CastExpression):
                converted.data_type = self.datatype_converter.convert(node.data_type)
            return converted
        if isinstance(
            node,
            (
                BooleanExpression,
                CaseExpression,
                ExistsExpression,
                InExpression,
                SubqueryExpression,
                WindowExpression,
                AggregateExpression,
            ),
        ):
            converted = deepcopy(node)
            for item in fields(node):
                value = getattr(node, item.name)
                setattr(converted, item.name, self.convert(value))
            return converted
        if isinstance(node, list):
            return [self.convert(item) for item in node]
        if isinstance(node, dict):
            return {key: self.convert(value) for key, value in node.items()}
        if isinstance(node, str):
            return self._map_text(node)
        if is_dataclass(node):
            return deepcopy(node)
        return node

    def _map_text(self, text: str) -> str:
        result = text
        for source, target in FUNCTION_MAPPING.items():
            if source in {"GETDATE", "GETUTCDATE"}:
                result, count = re.subn(
                    rf"\b{source}\s*\(\s*\)", target, result, flags=re.IGNORECASE
                )
            else:
                result, count = re.subn(
                    rf"\b{source}\s*\(",
                    f"{target}(",
                    result,
                    flags=re.IGNORECASE,
                )
            if count:
                self._record(self.applied_function_mappings, source, target)
        for source, target in OPERATOR_MAPPING.items():
            result, count = re.subn(re.escape(source), target, result)
            if count:
                self._record(self.applied_operator_mappings, source, target)
        return result

    @staticmethod
    def _record(collection: list[dict[str, str]], source: str, target: str) -> None:
        mapping = {"source": source, "target": target}
        if mapping not in collection:
            collection.append(mapping)
