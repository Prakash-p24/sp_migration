"""Coordinates parser, IR visitor, converter, generator and validators."""

from src.core.migration_engine import MigrationNotImplementedError
from src.ir.serializer import to_dict
from src.parsers.mssql_parser import MSSQLParser
from src.visitors.mssql_ir_visitor import MSSQLIRVisitor


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
        procedures = MSSQLIRVisitor().visit(tree)
        if not procedures:
            raise ValueError(
                "The SQL parsed successfully, but it does not contain a "
                "CREATE, ALTER, or CREATE OR ALTER procedure."
            )
        if len(procedures) > 1:
            raise ValueError("Submit one stored procedure per migration request.")
        procedure_names = [
            f"{procedure.header.schema}.{procedure.header.procedure_name}"
            if procedure.header.schema
            else procedure.header.procedure_name
            for procedure in procedures
        ]

        return {
            "source": source,
            "target": target,
            "status": "parsed",
            "message": "T-SQL parsed into the migration IR. SQL conversion has not been performed.",
            "procedures": procedure_names,
            "ir": to_dict(procedures[0]),
        }
