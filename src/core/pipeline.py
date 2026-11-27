"""Coordinates parser, IR visitor, converter, generator and validators."""

from src.core.migration_engine import MigrationNotImplementedError
from src.parsers.mssql_parser import MSSQLParser


class MigrationPipeline:
    def run(self, source_sql: str, source_dialect: str, target_dialect: str = "postgres"):
        source = source_dialect.strip().lower()
        target = target_dialect.strip().lower()
        if source not in {"mssql", "mysql"}:
            raise ValueError("Unsupported source dialect. Supported values: mssql, mysql.")
        if target != "postgres":
            raise ValueError("Unsupported target dialect. Supported value: postgres.")
        if source == "mysql":
            raise MigrationNotImplementedError(
                "MySQL parsing is not implemented yet because the project does not "
                "have a MySQL grammar."
            )

        parser = MSSQLParser()
        tree = parser.parse(source_sql)
        procedure_names = parser.get_procedure_names(tree)
        if not procedure_names:
            raise ValueError(
                "The SQL parsed successfully, but it does not contain a "
                "CREATE, ALTER, or CREATE OR ALTER procedure."
            )

        return {
            "source": source,
            "target": target,
            "status": "parsed",
            "message": "T-SQL syntax is valid. SQL conversion has not been performed.",
            "procedures": procedure_names,
        }
