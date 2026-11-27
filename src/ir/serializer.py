"""JSON-compatible serialization for common IR nodes."""

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from src.ir.procedure import Procedure, ProcedureHeader
from src.ir.statements import Statement


def to_dict(value: Any) -> Any:
    """Convert IR dataclasses and enums to a clean, JSON-compatible structure."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, tuple):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_dict(item) for key, item in value.items()}
    if isinstance(value, Procedure):
        result = {
            "ir_version": "1.0",
            "header": to_dict(value.header),
            "parameters": to_dict(value.parameters),
            "declarations": to_dict(value.declarations),
            "body": {"statements": to_dict(value.body)},
            "exception_handlers": to_dict(value.exception_handlers),
            "metadata": to_dict(value.metadata),
        }
        if value.original_sql:
            result["metadata"]["original_sql"] = value.original_sql
        return result
    if isinstance(value, ProcedureHeader):
        return {
            "procedure_name": value.procedure_name,
            "schema": value.schema,
            "source_dialect": value.source_dialect,
            "target_dialect": value.target_dialect,
            "procedure_type": value.procedure_type,
        }
    if is_dataclass(value):
        result = {}
        for item in fields(value):
            item_value = getattr(value, item.name)
            if isinstance(value, Statement) and item.name == "statement_type":
                result["node_type"] = to_dict(item_value)
                continue
            if item.name == "attributes":
                result.update(to_dict(item_value))
                continue
            if isinstance(value, Statement) and item.name == "body":
                if item_value:
                    result["statements"] = to_dict(item_value)
                continue
            if isinstance(value, Statement) and item.name == "else_body":
                if item_value:
                    result["else_statements"] = to_dict(item_value)
                continue
            if item.name in {"location", "original_sql", "metadata"}:
                if item.name == "location" and item_value is not None:
                    result["source_location"] = to_dict(item_value)
                elif (
                    item.name == "original_sql"
                    and item_value
                    and not (
                        isinstance(value, Statement)
                        and value.statement_type.value == "BLOCK"
                    )
                ):
                    result["original_sql"] = item_value
                elif item.name == "metadata" and item_value:
                    result["metadata"] = to_dict(item_value)
                continue
            if item_value is not None:
                if item_value == {}:
                    continue
                result[item.name] = to_dict(item_value)
        return result
    return value
