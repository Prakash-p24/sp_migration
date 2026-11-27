"""Build the shared, recursive IR from MSSQL ANTLR parse trees."""

import re

from src.generated.mssql.TSqlParser import TSqlParser
from src.generated.mssql.TSqlParserVisitor import TSqlParserVisitor
from src.ir.enums import SelectIntent, StatementKind
from src.ir.expressions import RawExpression
from src.ir.nodes import SourceLocation
from src.ir.procedure import (
    Procedure,
    ProcedureHeader,
    ProcedureParameter,
    VariableDeclaration,
)
from src.ir.semantic import SelectIntentAnalyzer
from src.ir.statements import Statement, UnsupportedStatement


class MSSQLIRVisitor(TSqlParserVisitor):
    """Translate source syntax to common IR while preserving unknown syntax."""

    def visitTsql_file(self, ctx: TSqlParser.Tsql_fileContext) -> list[Procedure]:
        return [
            self.visitCreate_or_alter_procedure(node)
            for node in self._walk(ctx)
            if isinstance(node, TSqlParser.Create_or_alter_procedureContext)
        ]

    def visitCreate_or_alter_procedure(
        self, ctx: TSqlParser.Create_or_alter_procedureContext
    ) -> Procedure:
        name = ctx.procName
        schema = name.schema.getText() if name.schema else None
        procedure = Procedure(
            header=ProcedureHeader(
                procedure_name=name.procedure.getText(),
                schema=schema,
                source_dialect="mssql",
                target_dialect="postgres",
                procedure_type="PROCEDURE",
                location=self._location(ctx),
                original_sql=self._source_text(ctx),
                metadata={"source_operation": ctx.proc.text},
            ),
            parameters=[self.visitProcedure_param(param) for param in ctx.procedure_param()],
            location=self._location(ctx),
            original_sql=self._source_text(ctx),
            metadata={"source_language": "TSQL"},
        )
        for clause in ctx.sql_clauses():
            statement = self._build_clause(clause, procedure)
            if statement is not None:
                procedure.body.append(statement)
        procedure.exception_handlers = self._collect_exception_handlers(procedure.body)
        return procedure

    def visitProcedure_param(
        self, ctx: TSqlParser.Procedure_paramContext
    ) -> ProcedureParameter:
        return ProcedureParameter(
            name=ctx.LOCAL_ID().getText().lstrip("@"),
            data_type=ctx.data_type().getText(),
            mode="OUT" if ctx.OUT() or ctx.OUTPUT() else "IN",
            default_value=self._source_text(ctx.default_val)
            if ctx.default_val
            else None,
            location=self._location(ctx),
            original_sql=self._source_text(ctx),
        )

    def _build_clause(self, clause, procedure: Procedure) -> Statement | None:
        """Build one clause, dispatching through grammar wrappers as needed."""
        dml = clause.dml_clause()
        if dml:
            return self._build_dml(dml)

        other = clause.another_statement()
        if other:
            declaration = other.declare_statement()
            if declaration:
                declared = self._declarations(declaration)
                procedure.declarations.extend(declared)
                return Statement(
                    statement_type=StatementKind.DECLARE,
                    attributes={"declarations": declared},
                    location=self._location(clause),
                    original_sql=self._source_text(clause),
                )
            for method_name, kind in (
                ("execute_statement", StatementKind.CALL),
                ("cursor_statement", StatementKind.CURSOR),
                ("transaction_statement", StatementKind.TRANSACTION),
                ("set_statement", StatementKind.ASSIGNMENT),
            ):
                method = getattr(other, method_name, None)
                context = method() if method else None
                if context:
                    sql = self._source_text(context)
                    if kind == StatementKind.CALL and sql.lstrip().upper().startswith(
                        ("EXECUTE IMMEDIATE", "PREPARE", "DEALLOCATE")
                    ):
                        kind = StatementKind.DYNAMIC_SQL
                    if kind == StatementKind.CALL and "SP_EXECUTESQL" in sql.upper():
                        kind = StatementKind.DYNAMIC_SQL
                    return Statement(
                        statement_type=kind,
                        attributes={"source_sql": sql},
                        location=self._location(context),
                        original_sql=sql,
                        metadata={"source_dialect": "mssql"},
                    )
            return self._unsupported(clause, "another_statement")

        control = self._find_outer_control(clause)
        if control is None:
            if clause.ddl_clause():
                source_sql = self._source_text(clause.ddl_clause())
                normalized = source_sql.lstrip().upper()
                if normalized.startswith(("CREATE TABLE #", "DROP TABLE #")):
                    return Statement(
                        statement_type=StatementKind.TEMPORARY_OBJECT,
                        attributes={"source_sql": source_sql},
                        location=self._location(clause),
                        original_sql=source_sql,
                        metadata={"source_dialect": "mssql"},
                    )
            return self._unsupported(clause, "sql_clauses")
        return self._build_control(control, procedure)

    def _build_control(self, node, procedure: Procedure) -> Statement:
        if isinstance(node, TSqlParser.Block_statementContext):
            return Statement(
                statement_type=StatementKind.BLOCK,
                body=self._build_clauses(node.sql_clauses(), procedure),
                location=self._location(node),
                original_sql=self._source_text(node),
            )

        if isinstance(node, TSqlParser.If_statementContext):
            clauses = node.sql_clauses()
            return Statement(
                statement_type=StatementKind.IF,
                attributes={
                    "condition": self._source_text(node.search_condition()),
                    "condition_expression": self._raw_expression(
                        node.search_condition()
                    ),
                },
                body=self._build_clauses(clauses[:1], procedure),
                else_body=self._build_clauses(clauses[1:], procedure),
                location=self._location(node),
                original_sql=self._source_text(node),
            )

        if isinstance(node, TSqlParser.While_statementContext):
            clauses = node.sql_clauses()
            body = self._build_clauses(clauses, procedure)
            if node.BREAK():
                body.append(Statement(statement_type=StatementKind.BREAK))
            if node.CONTINUE():
                body.append(Statement(statement_type=StatementKind.CONTINUE))
            return Statement(
                statement_type=StatementKind.LOOP,
                attributes={
                    "loop_type": "WHILE",
                    "condition": self._source_text(node.search_condition()),
                    "condition_expression": self._raw_expression(
                        node.search_condition()
                    ),
                },
                body=body,
                location=self._location(node),
                original_sql=self._source_text(node),
            )

        if isinstance(node, TSqlParser.Try_catch_statementContext):
            try_clauses = []
            catch_clauses = []
            end_try = node.getToken(TSqlParser.END, 0)
            split_index = end_try.symbol.tokenIndex if end_try else -1
            for child in self._children(node):
                if isinstance(child, TSqlParser.Sql_clausesContext):
                    if child.start.tokenIndex < split_index:
                        try_clauses.append(child)
                    else:
                        catch_clauses.append(child)
            return Statement(
                statement_type=StatementKind.EXCEPTION,
                attributes={
                    "handler_type": "TRY_CATCH",
                    "catch_body": self._build_clauses(catch_clauses, procedure),
                },
                body=self._build_clauses(try_clauses, procedure),
                location=self._location(node),
                original_sql=self._source_text(node),
            )

        if isinstance(node, TSqlParser.Return_statementContext):
            return Statement(
                statement_type=StatementKind.RETURN,
                attributes={"value": self._source_text(node.expression())}
                if node.expression()
                else {},
                location=self._location(node),
                original_sql=self._source_text(node),
            )

        if isinstance(node, TSqlParser.Break_statementContext):
            return Statement(statement_type=StatementKind.BREAK, original_sql=self._source_text(node))
        if isinstance(node, TSqlParser.Continue_statementContext):
            return Statement(statement_type=StatementKind.CONTINUE, original_sql=self._source_text(node))
        if isinstance(node, TSqlParser.Goto_statementContext):
            return Statement(
                statement_type=StatementKind.GOTO,
                attributes={"target": self._source_text(node)},
                original_sql=self._source_text(node),
                location=self._location(node),
            )

        kind = StatementKind.EXCEPTION if isinstance(
            node,
            (TSqlParser.Throw_statementContext, TSqlParser.Raiseerror_statementContext),
        ) else StatementKind.OTHER
        return self._unsupported(node, type(node).__name__, kind=kind)

    def _build_dml(self, node) -> Statement:
        if node.select_statement_standalone():
            return self._select(node.select_statement_standalone())
        if node.update_statement():
            ctx = node.update_statement()
            assignments = {}
            assignment_expressions = {}
            for item in ctx.update_elem():
                text = self._source_text(item)
                if "=" in text:
                    target, value = text.split("=", 1)
                    assignments[target.strip()] = value.strip()
                    if item.expression():
                        assignment_expressions[target.strip()] = self._raw_expression(
                            item.expression()
                        )
            return Statement(
                statement_type=StatementKind.UPDATE,
                attributes={
                    "table": self._source_text(ctx.ddl_object())
                    if ctx.ddl_object()
                    else self._source_text(ctx.rowset_function_limited()),
                    "set": assignments,
                    "set_expressions": assignment_expressions,
                    **({"where": self._source_text(ctx.search_condition(0))}
                       if ctx.search_condition() else {}),
                    **({"where_expression": self._raw_expression(ctx.search_condition(0))}
                       if ctx.search_condition() else {}),
                },
                location=self._location(ctx),
                original_sql=self._source_text(ctx),
            )
        if node.insert_statement():
            ctx = node.insert_statement()
            return Statement(
                statement_type=StatementKind.INSERT,
                attributes={
                    "table": self._source_text(ctx.ddl_object())
                    if ctx.ddl_object()
                    else "",
                    "columns": self._source_text(ctx.insert_column_name_list())
                    if ctx.insert_column_name_list()
                    else None,
                    "values_or_query": self._source_text(ctx.insert_statement_value()),
                },
                location=self._location(ctx),
                original_sql=self._source_text(ctx),
            )
        if node.delete_statement():
            ctx = node.delete_statement()
            return Statement(
                statement_type=StatementKind.DELETE,
                attributes={
                    "table": self._source_text(ctx.delete_statement_from()),
                    **({"where": self._source_text(ctx.search_condition(0))}
                       if ctx.search_condition() else {}),
                },
                location=self._location(ctx),
                original_sql=self._source_text(ctx),
            )
        if node.merge_statement():
            ctx = node.merge_statement()
            return Statement(
                statement_type=StatementKind.MERGE,
                attributes={
                    "target": self._source_text(ctx.ddl_object()),
                    "source_and_actions": self._source_text(ctx),
                },
                location=self._location(ctx),
                original_sql=self._source_text(ctx),
            )
        return self._unsupported(node, "dml_clause")

    def _select(self, ctx) -> Statement:
        query = ctx.select_statement().query_expression().query_specification()
        elements = query.columns.selectElement
        assignment_targets = [element.LOCAL_ID().getText() for element in elements if element.LOCAL_ID()]
        intent = SelectIntentAnalyzer.analyze(
            has_variable_assignment=bool(assignment_targets),
            has_into_table=bool(query.into),
        )
        select_context = ctx.select_statement()
        order_by = []
        if select_context.select_order_by_clause():
            order_clause = select_context.select_order_by_clause().order_by_clause()
            if order_clause:
                order_by = [self._source_text(item) for item in order_clause.order_bys]
        attrs = {
            "columns": [self._column_reference(element) for element in elements],
            "distinct": bool(
                query.allOrDistinct
                and query.allOrDistinct.text.upper() == "DISTINCT"
            ),
            "from": self._table_reference(query.from_) if query.from_ else None,
            "joins": [],
            "where": self._source_text(query.where) if query.where else None,
            "group_by": [self._source_text(item) for item in query.groupBys],
            "having": self._source_text(query.having) if query.having else None,
            "order_by": order_by,
        }
        if query.top:
            top = query.top
            if top.top_count():
                count = top.top_count()
                attrs["top_limit"] = (
                    count.DECIMAL().getText()
                    if count.DECIMAL()
                    else self._source_text(count.expression())
                )
                attrs["top_percent"] = False
            elif top.top_percent():
                percent = top.top_percent()
                attrs["top_limit"] = (
                    percent.percent_constant.text
                    if percent.percent_constant
                    else self._source_text(percent.topper_expression)
                )
                attrs["top_percent"] = True
            attrs["top_with_ties"] = bool(top.TIES())
        if assignment_targets:
            attrs["assignment_targets"] = assignment_targets
        if query.into:
            attrs["into"] = self._source_text(query.into)
        return Statement(
            statement_type=StatementKind.SELECT,
            intent=intent.value,
            attributes=attrs,
            location=self._location(ctx),
            original_sql=self._source_text(ctx),
        )

    def _column_reference(self, ctx) -> dict:
        source = self._source_text(ctx).strip()
        if ctx.LOCAL_ID():
            return {
                "kind": "VARIABLE_ASSIGNMENT",
                "target": ctx.LOCAL_ID().getText().lstrip("@"),
                "expression": self._source_text(ctx.expression()).strip()
                if ctx.expression()
                else None,
            }

        alias = None
        if ctx.expression_elem():
            expression_elem = ctx.expression_elem()
            alias_context = expression_elem.as_column_alias()
            alias = self._source_text(alias_context).strip() if alias_context else None
            source = self._source_text(expression_elem.expressionAs).strip()

        identifier = r"(?:\[[^\]]+\]|[A-Za-z_][\w$]*)"
        match = re.fullmatch(
            rf"\s*(?P<first>{identifier})(?:\s*\.\s*(?P<second>{identifier}))?\s*",
            source,
        )
        if match:
            qualifier = match.group("first").strip("[]") if match.group("second") else None
            name = (match.group("second") or match.group("first")).strip("[]")
            return {"kind": "COLUMN", "name": name, "table": qualifier, "alias": alias}
        return {"kind": "EXPRESSION", "source_text": source, "alias": alias}

    def _table_reference(self, ctx) -> dict:
        source = self._source_text(ctx).strip()
        identifier = r"(?:\[[^\]]+\]|[A-Za-z_][\w$]*)"
        match = re.fullmatch(
            rf"\s*(?P<first>{identifier})(?:\s*\.\s*(?P<second>{identifier}))?"
            rf"(?:\s+(?:AS\s+)?(?P<alias>{identifier}))?\s*",
            source,
            flags=re.IGNORECASE,
        )
        if not match:
            return {"kind": "RAW", "source_sql": source}
        first = match.group("first").strip("[]")
        second = match.group("second")
        alias = match.group("alias")
        if second:
            schema, name = first, second.strip("[]")
        else:
            schema, name = None, first
        if alias:
            alias = alias.strip("[]")
        return {"kind": "TABLE", "name": name, "schema": schema, "alias": alias}

    def _build_clauses(self, clauses, procedure: Procedure) -> list[Statement]:
        result = []
        for clause in clauses:
            statement = self._build_clause(clause, procedure)
            if statement is not None:
                result.append(statement)
        return result

    @staticmethod
    def _collect_exception_handlers(statements: list[Statement]) -> list[Statement]:
        handlers: list[Statement] = []
        for statement in statements:
            if (
                statement.statement_type == StatementKind.EXCEPTION
                and statement.attributes.get("handler_type")
            ):
                handlers.append(statement)
            handlers.extend(
                MSSQLIRVisitor._collect_exception_handlers(statement.body)
            )
            handlers.extend(
                MSSQLIRVisitor._collect_exception_handlers(statement.else_body)
            )
            handlers.extend(
                MSSQLIRVisitor._collect_exception_handlers(
                    statement.attributes.get("catch_body", [])
                )
            )
        return handlers

    def _declarations(self, ctx) -> list:
        declarations = []
        for item in ctx.declare_local():
            declarations.append(
                VariableDeclaration(
                    name=item.LOCAL_ID().getText().lstrip("@"),
                    data_type=item.data_type().getText(),
                    initial_value=self._source_text(item.expression())
                    if item.expression()
                    else None,
                    location=self._location(item),
                    original_sql=self._source_text(item),
                )
            )
        if not declarations and ctx.LOCAL_ID() and ctx.data_type():
            declarations.append(
                VariableDeclaration(
                    name=ctx.LOCAL_ID().getText().lstrip("@"),
                    data_type=ctx.data_type().getText(),
                    location=self._location(ctx),
                    original_sql=self._source_text(ctx),
                )
            )
        if not declarations and ctx.LOCAL_ID():
            type_context = (
                ctx.table_type_definition()
                or ctx.table_name()
                or ctx.xml_type_definition()
            )
            if type_context:
                declarations.append(
                    VariableDeclaration(
                        name=ctx.LOCAL_ID().getText().lstrip("@"),
                        data_type=self._source_text(type_context),
                        location=self._location(ctx),
                        original_sql=self._source_text(ctx),
                        metadata={"declaration_kind": "COMPLEX"},
                    )
                )
        return declarations

    def _find_outer_control(self, clause):
        control_types = (
            TSqlParser.Block_statementContext,
            TSqlParser.If_statementContext,
            TSqlParser.While_statementContext,
            TSqlParser.Try_catch_statementContext,
            TSqlParser.Return_statementContext,
            TSqlParser.Break_statementContext,
            TSqlParser.Continue_statementContext,
            TSqlParser.Goto_statementContext,
            TSqlParser.Throw_statementContext,
            TSqlParser.Raiseerror_statementContext,
        )
        pending = list(reversed(self._children(clause)))
        while pending:
            node = pending.pop()
            if isinstance(node, control_types):
                return node
            pending.extend(reversed(self._children(node)))
        return None

    @staticmethod
    def _unsupported(ctx, parser_rule: str, kind=StatementKind.UNSUPPORTED):
        return UnsupportedStatement(
            statement_type=kind,
            parser_rule=parser_rule,
            attributes={"source_sql": MSSQLIRVisitor._source_text(ctx)},
            original_sql=MSSQLIRVisitor._source_text(ctx),
            location=MSSQLIRVisitor._location(ctx),
            metadata={"source_dialect": "mssql", "unsupported": True},
        )

    @classmethod
    def _raw_expression(cls, ctx):
        if ctx is None:
            return None
        text = cls._source_text(ctx)
        return RawExpression(
            source_text=text,
            location=cls._location(ctx),
            original_sql=text,
            metadata={"source_dialect": "mssql", "expression_unclassified": True},
        )

    @staticmethod
    def _children(node):
        return list(node.getChildren()) if hasattr(node, "getChildren") else []

    @classmethod
    def _walk(cls, node):
        pending = [node]
        while pending:
            current = pending.pop()
            yield current
            pending.extend(reversed(cls._children(current)))

    @staticmethod
    def _source_text(ctx) -> str:
        if ctx is None:
            return ""
        if ctx.start and ctx.stop:
            get_input_stream = getattr(ctx.start, "getInputStream", None)
            input_stream = get_input_stream() if get_input_stream else None
            if input_stream is not None:
                return input_stream.getText(ctx.start.start, ctx.stop.stop)
        return ctx.parser.getTokenStream().getText(ctx.start, ctx.stop)

    @staticmethod
    def _location(ctx) -> SourceLocation:
        token = getattr(ctx, "start", None)
        return SourceLocation(line=token.line, column=token.column) if token else None
