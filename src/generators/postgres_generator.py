"""Generate PostgreSQL procedure SQL from PostgreSQL-target procedure IR."""

import re
from collections.abc import Iterable

from src.generators.base_generator import BaseGenerator
from src.ir.enums import SelectIntent, StatementKind
from src.ir.procedure import (
    CursorDeclaration,
    Procedure,
    ProcedureParameter,
    VariableDeclaration,
)
from src.ir.statements import Statement, UnsupportedStatement


class PostgreSQLGenerationError(ValueError):
    """Raised when IR contains syntax that cannot be safely rendered yet."""


class PostgreSQLGenerator(BaseGenerator):
    """Render the supported common IR subset as a PL/pgSQL procedure."""

    def generate(self, node: Procedure) -> str:
        if not isinstance(node, Procedure):
            raise PostgreSQLGenerationError("PostgreSQLGenerator expects a Procedure IR node.")
        if node.header.target_dialect.lower() != "postgres":
            raise PostgreSQLGenerationError("The input IR is not targeted at PostgreSQL.")
        self._syntax_rules = (
            node.metadata.get("conversion_mappings", {}).get("available", {}).get("syntax_rules", {})
        )
        conversion_warnings = node.metadata.get("warnings", [])
        blocking_warnings = [
            warning
            for warning in conversion_warnings
            if warning.get("code") in {
                "TYPE_MAPPING_NOT_FOUND",
                "NO_DATA_TYPE_MAPPINGS_FOUND",
                "STATEMENT_NOT_MAPPED",
                "EXPRESSION_REQUIRES_REVIEW",
            }
        ]
        if blocking_warnings:
            raise PostgreSQLGenerationError(
                "Cannot safely generate SQL while conversion warnings remain: "
                + ", ".join(sorted({item["code"] for item in blocking_warnings}))
            )
        node.parameters = [
            parameter
            for parameter in node.parameters
            if parameter.metadata.get("generated_by") != "postgres_generator"
        ]
        result_cursors = self._allocate_result_cursors(node)
        self.generated_result_cursors = result_cursors
        for name in result_cursors:
            node.parameters.append(
                ProcedureParameter(
                    name=name,
                    data_type="refcursor",
                    mode="INOUT",
                    metadata={
                        "generated_by": "postgres_generator",
                        "reason": "return a source SELECT result set",
                    },
                )
            )
        self._result_cursors = iter(result_cursors)

        parameters = [self._render_parameter(item) for item in node.parameters]
        signature = ",\n    ".join(parameters)
        procedure_name = self._qualified_name(node.header.schema, node.header.procedure_name)

        lines = [f"CREATE OR REPLACE PROCEDURE {procedure_name}("]
        if signature:
            lines.append(f"    {signature}")
        lines.extend([")", "LANGUAGE plpgsql", "AS $sp_migration$"])
        declarations = self._render_declarations(node, indent=1)
        if declarations:
            lines.append("DECLARE")
            lines.extend(declarations)
        lines.append("BEGIN")

        # A single source-level procedure block can serve as PL/pgSQL's required
        # outer block. Keep nested BLOCK nodes rendered normally inside it.
        body_statements = node.body
        if len(node.body) == 1 and node.body[0].statement_type == StatementKind.BLOCK:
            body_statements = node.body[0].body

        body_lines = self._render_statements(body_statements, indent=1)
        if body_lines:
            lines.extend(body_lines)
        else:
            lines.append("    NULL;")
        lines.extend(["END;", "$sp_migration$;"])
        return "\n".join(lines)

    def _render_parameter(self, parameter) -> str:
        mode = parameter.mode.upper()
        if mode not in {"IN", "OUT", "INOUT"}:
            raise PostgreSQLGenerationError(
                f"Unsupported parameter mode {parameter.mode!r} for {parameter.name}."
            )
        if not parameter.data_type:
            raise PostgreSQLGenerationError(
                f"Parameter {parameter.name} has no converted PostgreSQL data type."
            )
        rendered = f"{mode} {self._quote(parameter.name)} {parameter.data_type}"
        if parameter.default_value:
            if mode == "OUT":
                raise PostgreSQLGenerationError(
                    f"OUT parameter {parameter.name} cannot have a default value in PostgreSQL."
                )
            rendered += f" DEFAULT {self._fragment(parameter.default_value)}"
        return rendered

    def _render_declarations(self, node: Procedure, indent: int) -> list[str]:
        declarations = []
        for item in node.declarations:
            if isinstance(item, VariableDeclaration):
                if not item.data_type:
                    raise PostgreSQLGenerationError(
                        f"Variable {item.name} has no converted PostgreSQL data type."
                    )
                line = f"{self._quote(item.name)} {item.data_type}"
                if item.initial_value is not None:
                    line += f" := {self._fragment(item.initial_value)}"
                declarations.append("    " * indent + line + ";")
            elif isinstance(item, CursorDeclaration):
                declarations.append("    " * indent + f"{self._quote(item.name)} refcursor;")
            else:
                raise PostgreSQLGenerationError(
                    f"Unsupported declaration node: {type(item).__name__}."
                )
        return declarations

    def _render_statements(self, statements: Iterable[Statement], indent: int) -> list[str]:
        output: list[str] = []
        for statement in statements:
            output.extend(self._render_statement(statement, indent))
        return output

    def _render_statement(self, statement: Statement, indent: int) -> list[str]:
        if isinstance(statement, UnsupportedStatement):
            rule = statement.parser_rule or statement.statement_type.value
            raise PostgreSQLGenerationError(
                f"Cannot generate PostgreSQL for unsupported MSSQL syntax ({rule}) "
                f"at {self._location(statement)}."
            )

        pad = "    " * indent
        attrs = statement.attributes
        kind = statement.statement_type

        if kind == StatementKind.BLOCK:
            inner = self._render_statements(statement.body, indent + 1)
            return [pad + "BEGIN", *(inner or ["    " * (indent + 1) + "NULL;"]), pad + "END;"]
        if kind == StatementKind.DECLARE:
            # Variable declarations are emitted in the procedure DECLARE section.
            return []
        if kind == StatementKind.SELECT:
            sql = self._render_select(statement)
            return [pad + sql.replace("\n", "\n" + pad) + ";"]
        if kind == StatementKind.UPDATE:
            table = self._render_table(attrs.get("table"))
            assignments = attrs.get("set", {})
            if not assignments:
                raise PostgreSQLGenerationError("UPDATE IR has no SET assignments.")
            set_clause = ", ".join(
                f"{self._identifier_path(key)} = {self._fragment(str(value))}"
                for key, value in assignments.items()
            )
            sql = f"UPDATE {table} SET {set_clause}"
            if attrs.get("where"):
                sql += f" WHERE {self._fragment(str(attrs['where']))}"
            return [pad + sql + ";"]
        if kind == StatementKind.DELETE:
            sql = f"DELETE FROM {self._render_table(attrs.get('table'))}"
            if attrs.get("where"):
                sql += f" WHERE {self._fragment(str(attrs['where']))}"
            return [pad + sql + ";"]
        if kind == StatementKind.INSERT:
            table = self._render_table(attrs.get("table"))
            columns = attrs.get("columns")
            values = attrs.get("values_or_query")
            if not values:
                raise PostgreSQLGenerationError("INSERT IR is missing values or a query.")
            columns_sql = self._render_insert_columns(str(columns)) if columns else ""
            return [pad + f"INSERT INTO {table}{(' ' + columns_sql) if columns_sql else ''} {self._fragment(str(values))};"]
        if kind == StatementKind.IF:
            condition = attrs.get("condition")
            if not condition:
                raise PostgreSQLGenerationError("IF IR has no condition.")
            result = [pad + f"IF {self._fragment(str(condition))} THEN"]
            result.extend(self._render_statements(statement.body, indent + 1) or ["    " * (indent + 1) + "NULL;"])
            if statement.else_body:
                result.append(pad + "ELSE")
                result.extend(self._render_statements(statement.else_body, indent + 1))
            result.append(pad + "END IF;")
            return result
        if kind == StatementKind.LOOP:
            if attrs.get("loop_type") != "WHILE":
                raise PostgreSQLGenerationError(
                    f"Unsupported loop type {attrs.get('loop_type')!r}."
                )
            result = [pad + f"WHILE {self._fragment(str(attrs.get('condition', 'TRUE')))} LOOP"]
            result.extend(self._render_statements(statement.body, indent + 1) or ["    " * (indent + 1) + "NULL;"])
            result.append(pad + "END LOOP;")
            return result
        if kind == StatementKind.EXCEPTION and attrs.get("handler_type") == "TRY_CATCH":
            result = [pad + "BEGIN"]
            result.extend(self._render_statements(statement.body, indent + 1) or ["    " * (indent + 1) + "NULL;"])
            result.append(pad + "EXCEPTION WHEN OTHERS THEN")
            catch_body = attrs.get("catch_body", [])
            result.extend(self._render_statements(catch_body, indent + 1) or ["    " * (indent + 1) + "NULL;"])
            result.append(pad + "END;")
            return result
        if kind == StatementKind.ASSIGNMENT:
            sql = str(attrs.get("source_sql", "")).strip().rstrip(";")
            match = re.fullmatch(r"SET\s+(@?[\w$]+)\s*=\s*(.+)", sql, re.IGNORECASE | re.DOTALL)
            if not match:
                raise PostgreSQLGenerationError(f"Cannot translate SET statement: {sql}")
            return [pad + f"{self._quote(match.group(1).lstrip('@'))} := {self._fragment(match.group(2))};"]
        if kind == StatementKind.CALL:
            return [pad + self._render_call(str(attrs.get("source_sql", ""))) + ";"]
        if kind == StatementKind.TRANSACTION:
            return [pad + self._render_transaction(str(attrs.get("source_sql", ""))) + ";"]
        if kind == StatementKind.RETURN:
            if attrs.get("value"):
                raise PostgreSQLGenerationError(
                    "A PostgreSQL procedure cannot return a scalar value; map it to an OUT parameter first."
                )
            return [pad + "RETURN;"]
        if kind in {StatementKind.BREAK, StatementKind.CONTINUE}:
            return [pad + ("EXIT;" if kind == StatementKind.BREAK else "CONTINUE;")]
        if kind == StatementKind.TEMPORARY_OBJECT:
            return [pad + self._render_temp_object(str(attrs.get("source_sql", ""))) + ";"]
        if kind in {StatementKind.CURSOR, StatementKind.DYNAMIC_SQL, StatementKind.GOTO, StatementKind.MERGE, StatementKind.OTHER, StatementKind.HANDLER}:
            raise PostgreSQLGenerationError(
                f"PostgreSQL rendering for {kind.value} has not been implemented."
            )
        raise PostgreSQLGenerationError(f"Unknown IR statement type: {kind!r}.")

    def _render_select(self, statement: Statement) -> str:
        attrs = statement.attributes
        original_sql = statement.original_sql or ""
        if re.search(r"\b(UNION|EXCEPT|INTERSECT|OPTION)\b", original_sql, re.IGNORECASE):
            raise PostgreSQLGenerationError(
                "SELECT contains MSSQL clauses not represented in the converted IR."
            )
        if attrs.get("top_percent") or attrs.get("top_with_ties"):
            raise PostgreSQLGenerationError(
                "TOP PERCENT and TOP WITH TIES need additional ordering semantics and are not yet generated."
            )
        columns = attrs.get("columns", [])
        if not columns:
            raise PostgreSQLGenerationError("SELECT IR has no columns.")
        rendered_columns = ", ".join(self._render_column(item) for item in columns)
        sql = "SELECT " + ("DISTINCT " if attrs.get("distinct") else "") + rendered_columns

        intent = statement.intent or attrs.get("intent")
        if intent == SelectIntent.VARIABLE_ASSIGNMENT.value:
            assignments = [item for item in columns if item.get("kind") == "VARIABLE_ASSIGNMENT"]
            if len(assignments) != 1:
                raise PostgreSQLGenerationError("SELECT variable assignment needs one target.")
            assignment = assignments[0]
            sql = "SELECT " + ("DISTINCT " if attrs.get("distinct") else "")
            sql += self._fragment(str(assignment.get("expression") or ""))
            sql += f" INTO {self._quote(str(assignment['target']))}"
        elif intent == SelectIntent.INTO_TABLE.value or attrs.get("into"):
            raise PostgreSQLGenerationError(
                "SELECT INTO table needs explicit PostgreSQL CREATE TABLE AS conversion."
            )
        elif intent == SelectIntent.RESULT_SET.value:
            try:
                cursor_name = next(self._result_cursors)
            except StopIteration as exc:
                raise PostgreSQLGenerationError("No result cursor was allocated for SELECT.") from exc
            sql = f"OPEN {self._quote(cursor_name)} FOR\n    {sql}"

        from_clause = attrs.get("from")
        if from_clause:
            sql += "\n    FROM " + self._render_table(from_clause)
        if attrs.get("joins"):
            raise PostgreSQLGenerationError("JOIN nodes are not yet represented by the generator.")
        if attrs.get("where"):
            sql += "\n    WHERE " + self._fragment(str(attrs["where"]))
        if attrs.get("group_by"):
            sql += "\n    GROUP BY " + ", ".join(self._fragment(str(item)) for item in attrs["group_by"])
        if attrs.get("having"):
            sql += "\n    HAVING " + self._fragment(str(attrs["having"]))
        if attrs.get("order_by"):
            sql += "\n    ORDER BY " + ", ".join(self._fragment(str(item)) for item in attrs["order_by"])
        if attrs.get("top_limit") is not None:
            row_limit_keyword = self._syntax_rules.get("TOP") or self._syntax_rules.get("top")
            if not row_limit_keyword:
                raise PostgreSQLGenerationError(
                    "No active database syntax mapping was found for MSSQL TOP."
                )
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_ ]*", row_limit_keyword):
                raise PostgreSQLGenerationError(
                    "The database syntax mapping for TOP contains an invalid target keyword."
                )
            limit = self._fragment(str(attrs["top_limit"]))
            if not re.fullmatch(r"(?:\d+|\"[A-Za-z_][\w$]*\")", limit):
                raise PostgreSQLGenerationError(
                    "TOP count must be a numeric literal or a simple PL/pgSQL variable."
                )
            sql += f"\n    {row_limit_keyword} {limit}"
        return sql

    def _allocate_result_cursors(self, node: Procedure) -> list[str]:
        used = {parameter.name.lower() for parameter in node.parameters}
        used.update(
            item.name.lower()
            for item in node.declarations
            if hasattr(item, "name") and item.name
        )
        result = []
        for index, statement in enumerate(self._walk_statements(node.body), start=1):
            if statement.statement_type == StatementKind.SELECT and (
                statement.intent or statement.attributes.get("intent")
            ) == SelectIntent.RESULT_SET.value:
                name = f"_migration_result_{index}"
                while name.lower() in used:
                    name += "_"
                used.add(name.lower())
                result.append(name)
        return result

    def _walk_statements(self, statements):
        for statement in statements:
            yield statement
            yield from self._walk_statements(statement.body)
            yield from self._walk_statements(statement.else_body)
            yield from self._walk_statements(statement.attributes.get("catch_body", []))
            yield from self._walk_statements(statement.attributes.get("catch_body", []))

    def _render_column(self, column) -> str:
        kind = column.get("kind")
        if kind == "COLUMN":
            name = self._identifier_path(column.get("name", ""))
            if column.get("table"):
                name = self._identifier_path(column["table"]) + "." + name
            if column.get("alias"):
                name += " AS " + self._quote(column["alias"])
            return name
        if kind == "VARIABLE_ASSIGNMENT":
            return self._fragment(str(column.get("expression") or ""))
        if kind == "EXPRESSION":
            return self._fragment(str(column.get("source_text", "")))
        if kind == "STAR":
            return "*"
        raise PostgreSQLGenerationError(f"Unsupported SELECT column node: {kind!r}.")

    def _render_table(self, table) -> str:
        if isinstance(table, dict):
            if table.get("kind") == "TABLE":
                name = self._qualified_name(table.get("schema"), table.get("name", ""))
                if table.get("alias"):
                    name += " AS " + self._quote(table["alias"])
                return name
            if table.get("kind") == "RAW":
                return self._fragment(str(table.get("source_sql", "")))
        if isinstance(table, str):
            return self._identifier_path(table)
        raise PostgreSQLGenerationError("Table reference is missing or malformed in IR.")

    def _render_insert_columns(self, columns: str) -> str:
        values = columns.strip()
        if values.startswith("(") and values.endswith(")"):
            names = [item.strip() for item in values[1:-1].split(",")]
            return "(" + ", ".join(self._identifier_path(item) for item in names) + ")"
        return self._fragment(values)

    def _render_call(self, source_sql: str) -> str:
        match = re.fullmatch(
            r"\s*EXEC(?:UTE)?\s+([\w.\[\]]+)\s*(.*?)\s*;?\s*",
            source_sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            raise PostgreSQLGenerationError(f"Cannot translate EXEC statement: {source_sql}")
        procedure = self._identifier_path(match.group(1))
        raw_args = match.group(2).strip()
        args = []
        if raw_args:
            for value in raw_args.split(","):
                value = re.sub(r"^\s*@?\w+\s*=\s*", "", value).strip()
                args.append(self._fragment(value))
        return f"CALL {procedure}({', '.join(args)})"

    def _render_transaction(self, source_sql: str) -> str:
        normalized = re.sub(r"\s+", " ", source_sql.strip().rstrip(";")).upper()
        match = re.fullmatch(r"(?:BEGIN|COMMIT|ROLLBACK)(?: TRAN(?:SACTION)?)?(?: (\w+))?", normalized)
        if not match:
            raise PostgreSQLGenerationError(f"Cannot translate transaction statement: {source_sql}")
        if normalized.startswith("BEGIN"):
            return "-- Transaction scope is controlled by the PostgreSQL CALL context"
        if normalized.startswith("COMMIT"):
            return "COMMIT"
        return "ROLLBACK" + (f" TO SAVEPOINT {self._quote(match.group(1))}" if match.group(1) else "")

    def _render_temp_object(self, source_sql: str) -> str:
        sql = self._fragment(source_sql)
        sql = re.sub(r"\bCREATE\s+TABLE\s+#", "CREATE TEMP TABLE ", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\bDROP\s+TABLE\s+#", "DROP TABLE IF EXISTS ", sql, flags=re.IGNORECASE)
        if sql == source_sql:
            raise PostgreSQLGenerationError(f"Cannot translate temporary object statement: {source_sql}")
        return sql.rstrip(";")

    def _fragment(self, sql: str) -> str:
        """Translate MSSQL variable and bracketed identifier syntax in fragments."""
        pieces = re.split(r"('(?:''|[^'])*')", sql)
        for index in range(0, len(pieces), 2):
            part = pieces[index]
            part = re.sub(r"\[([^\]]+)\]", lambda m: self._quote(m.group(1)), part)
            part = re.sub(r"@([A-Za-z_][\w$]*)", lambda m: self._quote(m.group(1)), part)
            pieces[index] = part
        return "".join(pieces).strip()

    @staticmethod
    def _quote(identifier: str) -> str:
        clean = identifier.strip().strip("[]\"")
        if not clean:
            raise PostgreSQLGenerationError("Cannot generate an empty SQL identifier.")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", clean):
            raise PostgreSQLGenerationError(
                f"Identifier {identifier!r} cannot be emitted as an unquoted PostgreSQL identifier."
            )
        # PostgreSQL folds unquoted identifiers to lowercase. Doing that
        # explicitly preserves predictable references to MSSQL mixed-case names.
        return clean.lower()

    @classmethod
    def _identifier_path(cls, name: str) -> str:
        parts = re.findall(r"\[([^\]]+)\]|([^\.\[\]]+)", name.strip())
        values = [(left or right).strip() for left, right in parts]
        if not values:
            raise PostgreSQLGenerationError("SQL identifier is missing in IR.")
        return ".".join(cls._quote(part) for part in values)

    @classmethod
    def _qualified_name(cls, schema: str | None, name: str) -> str:
        if schema:
            return f"{cls._identifier_path(schema)}.{cls._identifier_path(name)}"
        return cls._identifier_path(name)

    @staticmethod
    def _location(statement: Statement) -> str:
        if statement.location is None:
            return "unknown location"
        return f"line {statement.location.line}, column {statement.location.column}"
