"""Apply database-loaded MSSQL-to-PostgreSQL data type mappings."""

import re


class MSSQLDataTypeConverter:
    def __init__(self, mappings: dict[str, str] | None = None):
        self.mappings = {
            " ".join(source.strip().upper().split()): target.strip()
            for source, target in (mappings or {}).items()
        }
        self.applied_mappings: list[dict[str, str]] = []

    def convert(self, data_type: str) -> str:
        """Map the base type using the DB result and retain source type arguments."""
        return self.convert_with_status(data_type)[0]

    def convert_with_status(self, data_type: str) -> tuple[str, bool]:
        normalized = data_type.strip()
        match = re.fullmatch(r"([A-Za-z_][\w ]*)\s*(?:\((.*)\))?", normalized)
        if not match:
            return normalized, False

        source_name = " ".join(match.group(1).upper().split())
        arguments = match.group(2)
        exact_name = " ".join(normalized.upper().split())
        target_name = self.mappings.get(exact_name) or self.mappings.get(source_name)
        if target_name is None:
            return normalized, False
        mapping = {"source": normalized, "target": target_name}
        if mapping not in self.applied_mappings:
            self.applied_mappings.append(mapping)

        # A mapping may specify a complete target declaration, e.g. NUMERIC(19,4).
        if "(" in target_name or not arguments:
            return target_name, True

        target_base = target_name.strip().upper()
        if target_base in {
            "CHAR",
            "CHARACTER",
            "VARCHAR",
            "CHARACTER VARYING",
            "NUMERIC",
            "DECIMAL",
            "TIME",
            "TIMESTAMP",
            "TIMESTAMP WITH TIME ZONE",
        }:
            if arguments.strip().upper() == "MAX":
                if target_base in {"VARCHAR", "CHARACTER VARYING"}:
                    return "TEXT", True
                return target_name, True
            return f"{target_name}({arguments})", True
        return target_name, True
