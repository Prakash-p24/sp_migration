"""Coordinates parser, IR visitor, converter, generator and validators."""

from src.core.migration_engine import MigrationNotImplementedError


class MigrationPipeline:
    def run(self, source_sql: str, source_dialect: str, target_dialect: str = "postgres"):
        source = source_dialect.strip().lower()
        target = target_dialect.strip().lower()
        if source not in {"mssql", "mysql"}:
            raise ValueError("Unsupported source dialect. Supported values: mssql, mysql.")
        if target != "postgres":
            raise ValueError("Unsupported target dialect. Supported value: postgres.")
        raise MigrationNotImplementedError(
            f"The {source}-to-{target} conversion pipeline is not implemented yet. "
            "The project currently has parser/converter scaffolds, but cannot produce "
            "a PostgreSQL stored procedure."
        )
