"""Coordinates parser, IR visitor, converter, generator and validators."""

from src.core.migration_engine import MigrationNotImplementedError
from src.converters.mssql_to_postgres.procedure_converter import MSSQLProcedureConverter
from src.generators.postgres_generator import PostgreSQLGenerator
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
        postgres_ir = MSSQLProcedureConverter().convert(procedures[0])
        generator = PostgreSQLGenerator()
        converted_code = generator.generate(postgres_ir)
        postgres_ir.metadata["conversion"]["pipeline_stage"] = "sql_generation"
        postgres_ir.metadata["conversion"]["generator_executed"] = True
        postgres_ir.metadata["conversion"]["message"] = (
            "Source IR was mapped to PostgreSQL-target IR and PostgreSQL procedure SQL was generated. "
            "Generated SQL was not independently parsed or executed."
        )
        if generator.generated_result_cursors:
            postgres_ir.metadata["target"]["result_set_strategy"] = (
                "INOUT refcursor parameters; caller fetches each cursor in a transaction"
            )
            postgres_ir.metadata["changes"].append(
                {
                    "category": "result_set_strategy",
                    "source": "SELECT result set",
                    "target": "INOUT refcursor parameter",
                }
            )
        procedure_names = [
            f"{postgres_ir.header.schema}.{postgres_ir.header.procedure_name}"
            if postgres_ir.header.schema
            else postgres_ir.header.procedure_name
        ]

        return {
            "source": source,
            "target": target,
            "status": "completed",
            "message": "PostgreSQL procedure SQL generated; syntax validation has not been performed.",
            "procedures": procedure_names,
            "converted_code": converted_code,
            "ir": to_dict(postgres_ir),
        }
