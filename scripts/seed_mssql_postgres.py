import os
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

# Ensure project root is in sys.path when executed directly as a script
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import (
    ConversionCategory,
    ConversionMapping,
    RdbmsDialect,
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# =========================================================
# DIALECTS
# =========================================================

DIALECTS = [
    ("Microsoft SQL Server", "MSSQL", True),
    ("PostgreSQL", "POSTGRES", True),
    ("MySQL", "MYSQL", True),
]

# =========================================================
# CATEGORIES (56 Distinct Categories Covering Levels 1-4)
# =========================================================

CATEGORIES = [
    ('DATA_TYPE', 'Data type conversion rules'),
    ('FUNCTION', 'Built-in function conversion rules'),
    ('SYNTAX', 'SQL syntax transformation rules'),
    ('SYSTEM_VARIABLE', 'System variable conversion rules'),
    ('BATCH', 'Batch processing conversion rules'),
    ('OUTPUT', 'Output and messaging conversion rules'),
    ('EXPRESSION', 'SQL expression conversion rules'),
    ('CONSTRAINT', 'Constraint conversion rules'),
    ('INDEX', 'Index conversion rules'),
    ('DDL', 'DDL transformation rules'),
    ('PROCEDURE', 'Stored procedure conversion'),
    ('CONTROL_FLOW', 'Control flow conversion'),
    ('CURSOR', 'Cursor conversion'),
    ('DYNAMIC_SQL', 'Dynamic SQL conversion'),
    ('TRANSACTION', 'Transaction conversion'),
    ('ERROR_HANDLING', 'Error and exception conversion'),
    ('TRIGGER', 'Trigger conversion'),
    ('TEMP_TABLE', 'Temporary table conversion'),
    ('CTE', 'Recursive CTE conversion'),
    ('WINDOW', 'Window function conversion'),
    ('SECURITY', 'Security and permission conversion'),
    ('SEQUENCE', 'Sequence conversion'),
    ('LOCKING', 'Locking and isolation conversion'),
    ('QUERY_HINT', 'Query hint conversion'),
    ('BULK', 'Bulk data conversion'),
    ('PERCENTILE', 'Statistical function conversion'),
    ('XML', 'XML conversion'),
    ('JSON', 'Advanced JSON conversion'),
    ('CROSS_DATABASE', 'Cross database conversion'),
    ('PROCEDURE_RESULT', 'Procedure result handling'),
    ('TABLE_VALUED', 'Table valued expression conversion'),
    ('DDL_ADVANCED', 'Advanced DDL conversion'),
    ('SPECIAL', 'SQL Server special construct conversion'),
    ('AGGREGATE', 'Aggregate functions and aggregate semantic differences'),
    ('OPERATOR', 'Operators and operator semantic differences'),
    ('DATA_TYPE_ADVANCED', 'Advanced and SQL Server-specific data types'),
    ('COLLATION', 'Collation and case/accent sensitivity'),
    ('DATE_TIME', 'Date and time constructs and semantic rewrites'),
    ('IDENTIFIER', 'Object and identifier resolution'),
    ('SCHEMA', 'Schema-level operations'),
    ('TABLE', 'Table and table-definition operations'),
    ('VIEW', 'View operations and definition semantics'),
    ('FUNCTION_CONVERSION', 'Functions requiring specialized conversion handlers'),
    ('PRIVILEGE', 'Privileges, grants, and ownership'),
    ('EXTENSION', 'PostgreSQL extension requirements'),
    ('COMPATIBILITY', 'Version and compatibility-level considerations'),
    ('SEQUENCE_ADVANCED', 'Sequence and identity behavior'),
    ('PERFORMANCE', 'Performance features and query plan differences'),
    ('DATA_MIGRATION', 'Data migration and validation tasks'),
    ('ASSEMBLY', 'CLR assembly and SQL Server CLR features'),
    ('FULL_TEXT', 'Full-text search features'),
    ('SPATIAL', 'Spatial types and operations'),
    ('SYNONYM', 'Synonym resolution and replacement'),
    ('AGENT_JOB', 'SQL Server Agent jobs and schedules'),
    ('SERVICE', 'Service Broker and messaging services'),
    ('REPLICATION', 'Replication and change-data capture features'),
]

# =========================================================
# MAPPINGS (Deduplicated, Enhanced, and Optimized)
# Format:
# (category, source, target, match_type, handler_name, priority, metadata)
# Total Unique Rules: 453
# =========================================================

MAPPINGS = [
    ('DATA_TYPE', 'INT', 'INTEGER', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'TINYINT', 'SMALLINT', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'BIT', 'BOOLEAN', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'NVARCHAR', 'VARCHAR', 'PATTERN', None, 100, {}),
    ('DATA_TYPE', 'NCHAR', 'CHAR', 'PATTERN', None, 100, {}),
    ('DATA_TYPE', 'NTEXT', 'TEXT', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'DATETIME', 'TIMESTAMP', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'DATETIME2', 'TIMESTAMP', 'PATTERN', None, 100, {}),
    ('DATA_TYPE', 'SMALLDATETIME', 'TIMESTAMP', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'DATETIMEOFFSET', 'TIMESTAMP WITH TIME ZONE', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'UNIQUEIDENTIFIER', 'UUID', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'MONEY', 'NUMERIC(19,4)', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'SMALLMONEY', 'NUMERIC(10,4)', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'FLOAT', 'DOUBLE PRECISION', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'BINARY', 'BYTEA', 'PATTERN', None, 100, {}),
    ('DATA_TYPE', 'VARBINARY', 'BYTEA', 'PATTERN', None, 100, {}),
    ('DATA_TYPE', 'IMAGE', 'BYTEA', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'SQL_VARIANT', 'TEXT', 'EXACT', 'sql_variant_handler', 80, {'note': 'Fallback conversion; verify data type semantics'}),
    ('FUNCTION', 'GETDATE()', 'CURRENT_TIMESTAMP', 'EXACT', None, 100, {}),
    ('FUNCTION', 'GETUTCDATE()', "timezone('UTC', CURRENT_TIMESTAMP)", 'EXACT', 'utc_datetime_handler', 90, {}),
    ('FUNCTION', 'ISNULL()', 'COALESCE()', 'PATTERN', None, 100, {}),
    ('FUNCTION', 'LEN()', 'LENGTH()', 'PATTERN', 'len_handler', 90, {'note': 'SQL Server LEN ignores trailing spaces'}),
    ('FUNCTION', 'NEWID()', 'gen_random_uuid()', 'EXACT', None, 100, {}),
    ('FUNCTION', 'SUSER_NAME()', 'CURRENT_USER', 'EXACT', None, 100, {}),
    ('FUNCTION', 'CHAR()', 'CHR()', 'PATTERN', None, 100, {}),
    ('FUNCTION', 'CEILING()', 'CEIL()', 'EXACT', None, 100, {}),
    ('FUNCTION', 'REPLICATE()', 'REPEAT()', 'PATTERN', 'replicate_handler', 90, {'note': 'Argument-compatible conversion'}),
    ('FUNCTION', 'SQUARE()', 'POWER(value, 2)', 'PATTERN', 'square_handler', 90, {}),
    ('FUNCTION', 'LOG()', 'LN()', 'PATTERN', 'log_handler', 90, {'note': 'SQL Server LOG defaults to natural logarithm'}),
    ('FUNCTION', 'LOG10()', 'LOG(10, value)', 'PATTERN', 'log10_handler', 90, {}),
    ('FUNCTION', 'CHARINDEX()', 'POSITION()', 'PATTERN', 'charindex_handler', 90, {'note': 'Arguments must be reordered'}),
    ('FUNCTION', 'FORMAT()', 'TO_CHAR()', 'PATTERN', 'format_handler', 80, {'note': 'Format pattern translation required'}),
    ('FUNCTION', 'STR()', 'CAST(value AS TEXT)', 'PATTERN', 'str_handler', 80, {}),
    ('SYNTAX', 'TOP', 'LIMIT', 'PATTERN', 'top_handler', 90, {'note': 'Structural query transformation'}),
    ('SYNTAX', 'OUTPUT INSERTED', 'RETURNING', 'PATTERN', 'output_inserted_handler', 90, {}),
    ('SYNTAX', 'OUTPUT DELETED', 'RETURNING', 'PATTERN', 'output_deleted_handler', 90, {}),
    ('SYNTAX', 'WITH (NOLOCK)', '', 'PATTERN', 'nolock_handler', 90, {'note': 'Remove SQL Server locking hint'}),
    ('SYNTAX', 'WITH (UPDLOCK)', 'FOR UPDATE', 'PATTERN', 'updlock_handler', 80, {}),
    ('SYNTAX', 'WITH (ROWLOCK)', '', 'PATTERN', 'rowlock_handler', 80, {'note': 'Remove or review SQL Server row locking hint'}),
    ('SYNTAX', 'CROSS APPLY', 'CROSS JOIN LATERAL', 'EXACT', None, 100, {}),
    ('SYNTAX', 'OUTER APPLY', 'LEFT JOIN LATERAL', 'EXACT', None, 100, {}),
    ('SYNTAX', 'ALTER VIEW', 'CREATE OR REPLACE VIEW', 'PATTERN', 'alter_view_handler', 90, {}),
    ('SYNTAX', '[identifier]', '"identifier"', 'PATTERN', 'identifier_handler', 90, {}),
    ('SYSTEM_VARIABLE', '@@IDENTITY', 'LASTVAL()', 'EXACT', 'identity_handler', 80, {'note': 'Not always equivalent; prefer INSERT RETURNING'}),
    ('SYSTEM_VARIABLE', 'SCOPE_IDENTITY()', 'RETURNING', 'EXACT', 'scope_identity_handler', 90, {}),
    ('SYSTEM_VARIABLE', '@@ROWCOUNT', 'GET DIAGNOSTICS', 'EXACT', 'rowcount_handler', 90, {}),
    ('SYSTEM_VARIABLE', '@@VERSION', 'VERSION()', 'EXACT', None, 100, {}),
    ('SYSTEM_VARIABLE', '@@SPID', 'pg_backend_pid()', 'EXACT', None, 100, {}),
    ('BATCH', 'GO', '', 'EXACT', 'go_handler', 100, {'note': 'SQL Server batch separator; split batches'}),
    ('OUTPUT', 'PRINT', 'RAISE NOTICE', 'PATTERN', 'print_handler', 90, {}),
    ('DATA_TYPE', 'VARCHAR(MAX)', 'TEXT', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'NVARCHAR(MAX)', 'TEXT', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'VARBINARY(MAX)', 'BYTEA', 'EXACT', None, 100, {}),
    ('DATA_TYPE', 'TIMESTAMP', 'BYTEA', 'EXACT', 'rowversion_handler', 90, {'note': 'MSSQL TIMESTAMP is rowversion, not date/time'}),
    ('DATA_TYPE', 'XML', 'XML', 'EXACT', 'xml_handler', 90, {}),
    ('DATA_TYPE', 'GEOGRAPHY', 'GEOGRAPHY', 'EXACT', 'spatial_type_handler', 80, {}),
    ('DATA_TYPE', 'GEOMETRY', 'GEOMETRY', 'EXACT', 'spatial_type_handler', 80, {}),
    ('FUNCTION', 'DATEADD()', 'date + interval', 'PATTERN', 'dateadd_handler', 90, {}),
    ('FUNCTION', 'DATEDIFF()', 'date/time difference', 'PATTERN', 'datediff_handler', 90, {}),
    ('FUNCTION', 'DATEDIFF_BIG()', 'date/time difference', 'PATTERN', 'datediff_big_handler', 90, {}),
    ('FUNCTION', 'DATEPART()', 'EXTRACT()', 'PATTERN', 'datepart_handler', 90, {}),
    ('FUNCTION', 'DATENAME()', 'TO_CHAR()', 'PATTERN', 'datename_handler', 90, {}),
    ('FUNCTION', 'EOMONTH()', 'month end date expression', 'PATTERN', 'eomonth_handler', 90, {}),
    ('FUNCTION', 'DATEFROMPARTS()', 'MAKE_DATE()', 'PATTERN', 'datefromparts_handler', 90, {}),
    ('FUNCTION', 'TIMEFROMPARTS()', 'MAKE_TIME()', 'PATTERN', 'timefromparts_handler', 90, {}),
    ('FUNCTION', 'ISDATE()', 'date validation', 'PATTERN', 'isdate_handler', 80, {}),
    ('FUNCTION', 'TRY_CONVERT()', 'safe cast', 'PATTERN', 'try_convert_handler', 90, {}),
    ('FUNCTION', 'TRY_CAST()', 'safe cast', 'PATTERN', 'try_cast_handler', 90, {}),
    ('FUNCTION', 'IIF()', 'CASE WHEN', 'PATTERN', 'iif_handler', 100, {}),
    ('FUNCTION', 'CHOOSE()', 'CASE', 'PATTERN', 'choose_handler', 90, {}),
    ('FUNCTION', 'QUOTENAME()', 'identifier quoting', 'PATTERN', 'quotename_handler', 90, {}),
    ('FUNCTION', 'PATINDEX()', 'regex matching', 'PATTERN', 'patindex_handler', 90, {}),
    ('FUNCTION', 'STUFF()', 'substring replacement', 'PATTERN', 'stuff_handler', 90, {}),
    ('FUNCTION', 'LEFT()', 'LEFT()', 'PATTERN', None, 100, {}),
    ('FUNCTION', 'RIGHT()', 'RIGHT()', 'PATTERN', None, 100, {}),
    ('FUNCTION', 'SUBSTRING()', 'SUBSTRING()', 'PATTERN', None, 100, {}),
    ('FUNCTION', 'TRIM()', 'TRIM()', 'PATTERN', None, 100, {}),
    ('FUNCTION', 'STRING_AGG()', 'STRING_AGG()', 'PATTERN', 'string_agg_handler', 90, {}),
    ('FUNCTION', 'STRING_SPLIT()', 'STRING_TO_ARRAY()', 'PATTERN', 'string_split_handler', 90, {}),
    ('FUNCTION', 'CONCAT_WS()', 'CONCAT_WS()', 'PATTERN', None, 100, {}),
    ('FUNCTION', 'JSON_VALUE()', 'JSON extraction', 'PATTERN', 'json_value_handler', 90, {}),
    ('FUNCTION', 'JSON_QUERY()', 'JSON extraction', 'PATTERN', 'json_query_handler', 90, {}),
    ('FUNCTION', 'JSON_MODIFY()', 'JSON update expression', 'PATTERN', 'json_modify_handler', 90, {}),
    ('FUNCTION', 'OPENJSON()', 'JSON expansion', 'PATTERN', 'openjson_handler', 90, {}),
    ('FUNCTION', 'HASHBYTES()', 'digest()', 'PATTERN', 'hashbytes_handler', 90, {}),
    ('FUNCTION', 'NEWSEQUENTIALID()', 'UUID generation', 'PATTERN', 'newsequentialid_handler', 80, {}),
    ('SYNTAX', 'OFFSET FETCH', 'OFFSET LIMIT', 'PATTERN', 'pagination_handler', 100, {}),
    ('SYNTAX', 'MERGE', 'INSERT ON CONFLICT / conditional DML', 'PATTERN', 'merge_handler', 90, {}),
    ('SYNTAX', 'EXEC', 'CALL / dynamic SQL', 'PATTERN', 'exec_handler', 90, {}),
    ('SYNTAX', 'EXEC sp_executesql', 'dynamic SQL', 'PATTERN', 'sp_executesql_handler', 90, {}),
    ('SYNTAX', 'PIVOT', 'conditional aggregation', 'PATTERN', 'pivot_handler', 90, {}),
    ('SYNTAX', 'UNPIVOT', 'LATERAL VALUES / UNION ALL', 'PATTERN', 'unpivot_handler', 90, {}),
    ('SYNTAX', 'WITH CTE AS', 'WITH CTE AS', 'PATTERN', 'cte_handler', 100, {}),
    ('SYNTAX', '#temp_table', 'TEMP TABLE', 'PATTERN', 'temp_table_handler', 90, {}),
    ('SYNTAX', '@table_variable', 'temporary table / equivalent', 'PATTERN', 'table_variable_handler', 80, {}),
    ('SYNTAX', 'FOR XML PATH', 'XML aggregation', 'PATTERN', 'for_xml_handler', 90, {}),
    ('SYSTEM_VARIABLE', '@@TRANCOUNT', 'transaction state', 'EXACT', 'trancount_handler', 80, {}),
    ('SYSTEM_VARIABLE', '@@ERROR', 'exception handling', 'EXACT', 'error_handler', 80, {}),
    ('SYSTEM_VARIABLE', '@@LANGUAGE', 'session locale/configuration', 'EXACT', 'language_handler', 80, {}),
    ('SYSTEM_VARIABLE', '@@DATEFIRST', 'week configuration', 'EXACT', 'datefirst_handler', 80, {}),
    ('SYSTEM_VARIABLE', '@@NESTLEVEL', 'call depth strategy', 'EXACT', 'nestlevel_handler', 80, {}),
    ('SYSTEM_VARIABLE', 'SESSION_CONTEXT()', 'current_setting()', 'PATTERN', 'session_context_handler', 90, {}),
    ('EXPRESSION', 'STRING CONCATENATION (+)', '||', 'PATTERN', 'string_concat_handler', 90, {}),
    ('EXPRESSION', 'CAST()', 'CAST()', 'PATTERN', 'cast_handler', 100, {}),
    ('EXPRESSION', 'CONVERT()', 'CAST() / TO_CHAR()', 'PATTERN', 'convert_handler', 90, {}),
    ('EXPRESSION', 'CASE', 'CASE', 'PATTERN', 'case_handler', 100, {}),
    ('EXPRESSION', 'NOT IN', 'NOT IN with NULL review', 'PATTERN', 'null_semantics_handler', 90, {}),
    ('CONSTRAINT', 'DEFAULT GETDATE()', 'DEFAULT CURRENT_TIMESTAMP', 'PATTERN', 'default_handler', 90, {}),
    ('CONSTRAINT', 'DEFAULT NEWID()', 'DEFAULT gen_random_uuid()', 'PATTERN', 'default_handler', 90, {}),
    ('CONSTRAINT', 'IDENTITY(seed, increment)', 'GENERATED AS IDENTITY', 'PATTERN', 'identity_handler', 90, {}),
    ('CONSTRAINT', 'ON DELETE CASCADE', 'ON DELETE CASCADE', 'EXACT', None, 100, {}),
    ('CONSTRAINT', 'ON UPDATE CASCADE', 'ON UPDATE CASCADE', 'EXACT', None, 100, {}),
    ('INDEX', 'CLUSTERED INDEX', 'index without clustered property', 'PATTERN', 'index_handler', 80, {}),
    ('INDEX', 'NONCLUSTERED INDEX', 'CREATE INDEX', 'PATTERN', 'index_handler', 90, {}),
    ('INDEX', 'INCLUDE (columns)', 'covering index strategy', 'PATTERN', 'include_index_handler', 90, {}),
    ('INDEX', 'FILTERED INDEX WHERE', 'partial index', 'PATTERN', 'filtered_index_handler', 90, {}),
    ('DDL', 'ALTER COLUMN', 'ALTER COLUMN', 'PATTERN', 'alter_column_handler', 90, {}),
    ('DDL', 'DROP COLUMN', 'DROP COLUMN', 'PATTERN', 'drop_column_handler', 90, {}),
    ('DDL', 'ADD CONSTRAINT', 'ADD CONSTRAINT', 'PATTERN', 'constraint_handler', 90, {}),
    ('PROCEDURE', 'CREATE PROCEDURE', 'CREATE PROCEDURE', 'CONTEXT', 'procedure_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PROCEDURE', 'ALTER PROCEDURE', 'CREATE OR REPLACE PROCEDURE', 'PATTERN', 'alter_procedure_handler', 100, {}),
    ('PROCEDURE', 'EXEC procedure_name', 'CALL procedure_name', 'PATTERN', 'procedure_call_handler', 100, {}),
    ('PROCEDURE', 'OUTPUT parameter', 'OUT or INOUT parameter', 'CONTEXT', 'procedure_output_parameter_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PROCEDURE', 'RETURN integer', 'procedure return-code strategy', 'PATTERN', 'procedure_return_handler', 90, {}),
    ('PROCEDURE', 'DEFAULT parameter', 'DEFAULT parameter', 'PATTERN', 'procedure_default_handler', 90, {}),
    ('PROCEDURE', 'multiple result sets', 'refcursor/output strategy', 'PATTERN', 'procedure_result_handler', 90, {}),
    ('PROCEDURE', 'named parameters', 'named procedure arguments', 'PATTERN', 'named_argument_handler', 90, {}),
    ('PROCEDURE', 'WITH RECOMPILE', 'remove / deployment-time tuning review', 'CONTEXT', 'recompile_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PROCEDURE', 'WITH ENCRYPTION', 'unsupported/review', 'PATTERN', 'procedure_encryption_handler', 70, {}),
    ('CONTROL_FLOW', 'IF...ELSE', 'IF...ELSE', 'PATTERN', 'if_handler', 100, {}),
    ('CONTROL_FLOW', 'WHILE', 'WHILE ... LOOP', 'CONTEXT', 'while_conversion', 40, {'level': 4, 'auto_convert': False}),
    ('CONTROL_FLOW', 'BREAK', 'EXIT', 'CONTEXT', 'break_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CONTROL_FLOW', 'CONTINUE', 'CONTINUE', 'CONTEXT', 'continue_conversion', 30, {'level': 4, 'auto_convert': False}),
    ('CONTROL_FLOW', 'RETURN', 'RETURN; (procedure exit)', 'CONTEXT', 'return_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Review value-returning SQL Server procedure RETURN status; PostgreSQL procedure RETURN exits without returning a value.'}),
    ('CONTROL_FLOW', 'GOTO label', 'block/loop rewrite', 'CONTEXT', 'goto_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CONTROL_FLOW', 'WAITFOR DELAY', 'pg_sleep(seconds)', 'CONTEXT', 'waitfor_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CONTROL_FLOW', 'WAITFOR TIME', 'scheduled wait strategy', 'PATTERN', 'waitfor_time_handler', 70, {}),
    ('CURSOR', 'DECLARE CURSOR', 'DECLARE cursor', 'CONTEXT', 'cursor_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CURSOR', 'CURSOR FOR SELECT', 'cursor query', 'PATTERN', 'cursor_query_handler', 100, {}),
    ('CURSOR', 'OPEN cursor', 'OPEN cursor', 'PATTERN', 'cursor_open_handler', 100, {}),
    ('CURSOR', 'FETCH NEXT', 'FETCH', 'CONTEXT', 'cursor_fetch_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CURSOR', '@@FETCH_STATUS', 'fetch status variable', 'PATTERN', 'fetch_status_handler', 100, {}),
    ('CURSOR', 'CLOSE cursor', 'CLOSE cursor', 'CONTEXT', 'cursor_close_conversion', 40, {'level': 4, 'auto_convert': False}),
    ('CURSOR', 'DEALLOCATE cursor', 'CLOSE / cleanup cursor', 'CONTEXT', 'cursor_deallocate_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CURSOR', 'LOCAL FAST_FORWARD', 'cursor options conversion', 'PATTERN', 'cursor_options_handler', 90, {}),
    ('CURSOR', 'SCROLL cursor', 'scroll cursor', 'PATTERN', 'scroll_cursor_handler', 80, {}),
    ('CURSOR', 'CURSOR FOR UPDATE', 'cursor FOR UPDATE', 'PATTERN', 'cursor_update_handler', 90, {}),
    ('DYNAMIC_SQL', 'EXEC(@sql)', 'EXECUTE sql', 'PATTERN', 'dynamic_exec_handler', 100, {}),
    ('DYNAMIC_SQL', 'sp_executesql', 'EXECUTE USING', 'PATTERN', 'sp_executesql_handler', 100, {}),
    ('DYNAMIC_SQL', 'dynamic parameters', 'USING parameters', 'PATTERN', 'dynamic_parameter_handler', 100, {}),
    ('DYNAMIC_SQL', 'dynamic identifiers', "format('%I', identifier)", 'PATTERN', 'dynamic_identifier_handler', 90, {}),
    ('DYNAMIC_SQL', 'dynamic literals', "format('%L', value)", 'PATTERN', 'dynamic_literal_handler', 90, {}),
    ('DYNAMIC_SQL', 'dynamic SQL concatenation', 'safe format/parameterization', 'PATTERN', 'dynamic_concat_handler', 100, {}),
    ('DYNAMIC_SQL', 'dynamic ORDER BY', 'validated identifier formatting', 'PATTERN', 'dynamic_order_handler', 90, {}),
    ('TRANSACTION', 'BEGIN TRANSACTION', 'BEGIN', 'CONTEXT', 'transaction_begin_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TRANSACTION', 'COMMIT TRANSACTION', 'COMMIT', 'CONTEXT', 'transaction_commit_conversion', 40, {'level': 4, 'auto_convert': False}),
    ('TRANSACTION', 'ROLLBACK TRANSACTION', 'ROLLBACK', 'CONTEXT', 'transaction_rollback_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TRANSACTION', 'SAVE TRANSACTION', 'SAVEPOINT', 'CONTEXT', 'savepoint_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TRANSACTION', 'ROLLBACK TO SAVEPOINT', 'ROLLBACK TO SAVEPOINT', 'PATTERN', 'rollback_savepoint_handler', 90, {}),
    ('TRANSACTION', 'nested transaction', 'savepoint-based rewrite', 'CONTEXT', 'nested_transaction_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL does not implement SQL Server nested transactions identically.'}),
    ('TRANSACTION', 'distributed transaction', 'distributed transaction review', 'PATTERN', 'distributed_transaction_handler', 70, {}),
    ('TRANSACTION', 'implicit transaction mode', 'transaction mode review', 'PATTERN', 'implicit_transaction_handler', 80, {}),
    ('ERROR_HANDLING', 'TRY...CATCH', 'BEGIN...EXCEPTION', 'PATTERN', 'try_catch_handler', 100, {}),
    ('ERROR_HANDLING', 'THROW', 'RAISE', 'CONTEXT', 'throw_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('ERROR_HANDLING', 'RAISERROR', 'RAISE', 'CONTEXT', 'raiserror_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Severity, state, formatting, and NOWAIT behavior are not one-to-one.'}),
    ('ERROR_HANDLING', 'ERROR_MESSAGE()', 'SQLERRM', 'CONTEXT', 'error_message_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('ERROR_HANDLING', 'ERROR_NUMBER()', 'SQLSTATE / exception diagnostics', 'CONTEXT', 'error_number_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('ERROR_HANDLING', 'ERROR_LINE()', 'diagnostics / source tracking', 'CONTEXT', 'error_line_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('ERROR_HANDLING', 'ERROR_PROCEDURE()', 'context tracking', 'PATTERN', 'error_procedure_handler', 90, {}),
    ('ERROR_HANDLING', 'XACT_STATE()', 'transaction state strategy', 'PATTERN', 'xact_state_handler', 90, {}),
    ('ERROR_HANDLING', 'SET XACT_ABORT ON', 'exception/transaction handling', 'PATTERN', 'xact_abort_handler', 90, {}),
    ('ERROR_HANDLING', 'SET XACT_ABORT OFF', 'exception/transaction handling', 'PATTERN', 'xact_abort_handler', 90, {}),
    ('TRIGGER', 'AFTER INSERT', 'AFTER INSERT', 'PATTERN', 'after_insert_trigger_handler', 100, {}),
    ('TRIGGER', 'AFTER UPDATE', 'AFTER UPDATE', 'PATTERN', 'after_update_trigger_handler', 100, {}),
    ('TRIGGER', 'AFTER DELETE', 'AFTER DELETE', 'PATTERN', 'after_delete_trigger_handler', 100, {}),
    ('TRIGGER', 'INSTEAD OF', 'INSTEAD OF', 'PATTERN', 'instead_of_trigger_handler', 100, {}),
    ('TRIGGER', 'INSERTED', 'NEW', 'PATTERN', 'inserted_handler', 100, {}),
    ('TRIGGER', 'DELETED', 'OLD', 'PATTERN', 'deleted_handler', 100, {}),
    ('TRIGGER', 'multi-row trigger', 'set-based trigger logic', 'PATTERN', 'multirow_trigger_handler', 100, {}),
    ('TRIGGER', 'DISABLE TRIGGER', 'ALTER TABLE DISABLE TRIGGER', 'PATTERN', 'trigger_state_handler', 90, {}),
    ('TRIGGER', 'ENABLE TRIGGER', 'ALTER TABLE ENABLE TRIGGER', 'PATTERN', 'trigger_state_handler', 90, {}),
    ('TRIGGER', 'nested triggers', 'nested trigger behavior review', 'PATTERN', 'nested_trigger_handler', 80, {}),
    ('TRIGGER', 'recursive trigger', 'recursive trigger strategy', 'PATTERN', 'recursive_trigger_handler', 80, {}),
    ('TRIGGER', 'TRIGGER_NESTLEVEL()', 'trigger depth strategy', 'PATTERN', 'trigger_nestlevel_handler', 80, {}),
    ('TEMP_TABLE', '#local_temp', 'TEMP TABLE', 'PATTERN', 'local_temp_handler', 100, {}),
    ('TEMP_TABLE', '##global_temp', 'session/shared persistence strategy', 'PATTERN', 'global_temp_handler', 80, {}),
    ('TEMP_TABLE', 'temp table index', 'temporary index', 'PATTERN', 'temp_index_handler', 90, {}),
    ('TEMP_TABLE', 'temp table scope', 'session/transaction lifecycle', 'PATTERN', 'temp_scope_handler', 90, {}),
    ('TEMP_TABLE', 'temp table DROP', 'DROP TABLE IF EXISTS', 'PATTERN', 'temp_drop_handler', 100, {}),
    ('TEMP_TABLE', 'temp table SELECT INTO', 'CREATE TEMP TABLE AS', 'PATTERN', 'temp_select_into_handler', 90, {}),
    ('TEMP_TABLE', 'temp table constraints', 'temporary table constraints', 'PATTERN', 'temp_constraint_handler', 90, {}),
    ('CTE', 'recursive CTE', 'WITH RECURSIVE', 'CONTEXT', 'recursive_cte_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CTE', 'MAXRECURSION', 'recursion termination logic', 'PATTERN', 'maxrecursion_handler', 90, {}),
    ('CTE', 'recursive hierarchy traversal', 'recursive query', 'PATTERN', 'hierarchy_handler', 100, {}),
    ('CTE', 'recursive cycle detection', 'cycle detection strategy', 'PATTERN', 'recursive_cycle_handler', 90, {}),
    ('WINDOW', 'OVER(PARTITION BY)', 'OVER(PARTITION BY)', 'PATTERN', 'partition_handler', 100, {}),
    ('WINDOW', 'ROWS BETWEEN', 'ROWS BETWEEN', 'PATTERN', 'window_frame_handler', 100, {}),
    ('WINDOW', 'RANK()', 'RANK()', 'EXACT', None, 100, {}),
    ('WINDOW', 'DENSE_RANK()', 'DENSE_RANK()', 'EXACT', None, 100, {}),
    ('WINDOW', 'NTILE()', 'NTILE()', 'PATTERN', None, 100, {}),
    ('WINDOW', 'LAG()', 'LAG()', 'PATTERN', None, 100, {}),
    ('WINDOW', 'LEAD()', 'LEAD()', 'PATTERN', None, 100, {}),
    ('WINDOW', 'WITH TIES', 'tie preserving logic', 'PATTERN', 'ties_handler', 90, {}),
    ('WINDOW', 'GROUPING SETS', 'GROUPING SETS', 'PATTERN', 'grouping_sets_handler', 100, {}),
    ('WINDOW', 'ROLLUP', 'ROLLUP', 'PATTERN', None, 100, {}),
    ('WINDOW', 'CUBE', 'CUBE', 'PATTERN', None, 100, {}),
    ('WINDOW', 'window named definition', 'WINDOW clause', 'PATTERN', 'named_window_handler', 90, {}),
    ('SECURITY', 'GRANT EXECUTE', 'GRANT EXECUTE', 'PATTERN', 'grant_handler', 100, {}),
    ('SECURITY', 'GRANT SELECT', 'GRANT SELECT', 'PATTERN', None, 100, {}),
    ('SECURITY', 'DENY', 'REVOKE/privilege strategy', 'PATTERN', 'deny_handler', 90, {}),
    ('SECURITY', 'REVOKE', 'REVOKE', 'PATTERN', None, 100, {}),
    ('SECURITY', 'EXECUTE AS', 'role switching strategy', 'PATTERN', 'execute_as_handler', 90, {}),
    ('SECURITY', 'USER WITHOUT LOGIN', 'role strategy', 'PATTERN', 'user_without_login_handler', 80, {}),
    ('SECURITY', 'ownership chaining', 'explicit grants / security-definer review', 'CONTEXT', 'ownership_chain_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SECURITY', 'application role', 'role strategy', 'PATTERN', 'application_role_handler', 80, {}),
    ('SEQUENCE', 'CREATE SEQUENCE', 'CREATE SEQUENCE', 'PATTERN', 'sequence_handler', 100, {}),
    ('SEQUENCE', 'NEXT VALUE FOR', 'nextval()', 'PATTERN', 'next_value_handler', 100, {}),
    ('SEQUENCE', 'IDENT_CURRENT()', 'sequence lookup strategy', 'PATTERN', 'ident_current_handler', 90, {}),
    ('SEQUENCE', 'sp_sequence_get_range', 'sequence range strategy', 'PATTERN', 'sequence_range_handler', 80, {}),
    ('SEQUENCE', 'ALTER SEQUENCE', 'ALTER SEQUENCE', 'PATTERN', 'alter_sequence_handler', 90, {}),
    ('LOCKING', 'TABLOCK', 'table locking strategy', 'PATTERN', 'tablock_handler', 80, {}),
    ('LOCKING', 'HOLDLOCK', 'transaction/locking strategy', 'PATTERN', 'holdlock_handler', 80, {}),
    ('LOCKING', 'SERIALIZABLE', 'SERIALIZABLE', 'PATTERN', 'isolation_handler', 100, {}),
    ('LOCKING', 'READ UNCOMMITTED', 'READ COMMITTED limitation', 'PATTERN', 'read_uncommitted_handler', 80, {}),
    ('LOCKING', 'READ COMMITTED', 'READ COMMITTED', 'PATTERN', 'isolation_handler', 100, {}),
    ('LOCKING', 'REPEATABLE READ', 'REPEATABLE READ', 'PATTERN', 'isolation_handler', 100, {}),
    ('LOCKING', 'SNAPSHOT isolation', 'REPEATABLE READ strategy', 'PATTERN', 'snapshot_handler', 80, {}),
    ('LOCKING', 'DEADLOCK_PRIORITY', 'deadlock strategy', 'PATTERN', 'deadlock_priority_handler', 70, {}),
    ('QUERY_HINT', 'OPTION(RECOMPILE)', 'remove/review', 'PATTERN', 'query_hint_handler', 80, {}),
    ('QUERY_HINT', 'OPTION(OPTIMIZE FOR)', 'remove/review', 'PATTERN', 'optimize_for_handler', 80, {}),
    ('QUERY_HINT', 'OPTION(MAXDOP)', 'remove/review', 'PATTERN', 'maxdop_handler', 80, {}),
    ('QUERY_HINT', 'FORCESEEK', 'remove/review', 'PATTERN', 'forceseek_handler', 70, {}),
    ('QUERY_HINT', 'FORCEPLAN', 'remove/review', 'PATTERN', 'forceplan_handler', 70, {}),
    ('QUERY_HINT', 'USE HINT', 'remove/review', 'PATTERN', 'use_hint_handler', 70, {}),
    ('BULK', 'BULK INSERT', 'COPY / staging-based load', 'CONTEXT', 'bulk_insert_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('BULK', 'OPENROWSET', 'external/import strategy', 'PATTERN', 'openrowset_handler', 90, {}),
    ('BULK', 'BCP', 'COPY or external migration utility', 'CONTEXT', 'bcp_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('BULK', 'bulk error file', 'COPY error handling strategy', 'PATTERN', 'bulk_error_handler', 80, {}),
    ('BULK', 'bulk identity preservation', 'identity override strategy', 'PATTERN', 'bulk_identity_handler', 80, {}),
    ('PERCENTILE', 'PERCENTILE_CONT()', 'PERCENTILE_CONT()', 'PATTERN', None, 100, {}),
    ('PERCENTILE', 'PERCENTILE_DISC()', 'PERCENTILE_DISC()', 'PATTERN', None, 100, {}),
    ('PERCENTILE', 'APPROX_COUNT_DISTINCT()', 'approximate distinct strategy', 'PATTERN', 'approx_count_handler', 80, {}),
    ('PERCENTILE', 'STDEV()', 'STDDEV()', 'PATTERN', 'stdev_handler', 90, {}),
    ('PERCENTILE', 'STDEVP()', 'population standard deviation', 'PATTERN', 'stdevp_handler', 90, {}),
    ('PERCENTILE', 'VAR()', 'VAR_SAMP()', 'PATTERN', 'variance_handler', 90, {}),
    ('PERCENTILE', 'VARP()', 'VAR_POP()', 'PATTERN', 'variance_population_handler', 90, {}),
    ('XML', 'XML.value()', 'XPath extraction', 'PATTERN', 'xml_value_handler', 100, {}),
    ('XML', 'XML.nodes()', 'XML set expansion', 'PATTERN', 'xml_nodes_handler', 100, {}),
    ('XML', 'XML.query()', 'XPath query', 'PATTERN', 'xml_query_handler', 100, {}),
    ('XML', 'XML.exist()', 'XPath existence', 'PATTERN', 'xml_exist_handler', 100, {}),
    ('XML', 'XML.modify()', 'XML modification strategy', 'PATTERN', 'xml_modify_handler', 90, {}),
    ('XML', 'FOR XML PATH', 'XML aggregation', 'PATTERN', 'for_xml_handler', 90, {}),
    ('XML', 'FOR XML AUTO', 'XML aggregation', 'PATTERN', 'for_xml_auto_handler', 90, {}),
    ('XML', 'FOR XML EXPLICIT', 'XML construction strategy', 'PATTERN', 'for_xml_explicit_handler', 80, {}),
    ('JSON', 'FOR JSON PATH', 'JSON aggregation', 'PATTERN', 'for_json_handler', 100, {}),
    ('JSON', 'FOR JSON AUTO', 'JSON aggregation', 'PATTERN', 'for_json_auto_handler', 90, {}),
    ('JSON', 'FOR JSON ROOT', 'rooted JSON output', 'PATTERN', 'for_json_root_handler', 90, {}),
    ('JSON', 'FOR JSON INCLUDE_NULL_VALUES', 'include null values', 'PATTERN', 'json_null_handler', 90, {}),
    ('JSON', 'FOR JSON WITHOUT_ARRAY_WRAPPER', 'single JSON object', 'PATTERN', 'json_wrapper_handler', 90, {}),
    ('JSON', 'nested JSON PATH', 'nested jsonb_build_object', 'PATTERN', 'json_nested_handler', 100, {}),
    ('JSON', 'JSON_QUERY nested array', 'jsonb nested extraction', 'PATTERN', 'json_nested_array_handler', 90, {}),
    ('JSON', 'JSON validation', 'json/jsonb validation', 'PATTERN', 'json_validation_handler', 90, {}),
    ('CROSS_DATABASE', 'database.schema.table', 'schema.table strategy', 'PATTERN', 'cross_database_handler', 90, {}),
    ('CROSS_DATABASE', 'USE database', 'connection/schema strategy', 'PATTERN', 'use_database_handler', 90, {}),
    ('CROSS_DATABASE', 'DB_NAME()', 'database name lookup', 'PATTERN', 'db_name_handler', 90, {}),
    ('CROSS_DATABASE', 'linked server', 'foreign data wrapper strategy', 'PATTERN', 'linked_server_handler', 70, {}),
    ('CROSS_DATABASE', 'four part name', 'foreign data/schema strategy', 'PATTERN', 'four_part_name_handler', 80, {}),
    ('PROCEDURE_RESULT', 'SELECT result inside procedure', 'procedure result/refcursor strategy', 'PATTERN', 'procedure_select_handler', 100, {}),
    ('PROCEDURE_RESULT', 'multiple SELECT results', 'multiple refcursor strategy', 'PATTERN', 'multiple_result_handler', 90, {}),
    ('PROCEDURE_RESULT', 'OUTPUT result parameter', 'OUT/INOUT parameter', 'PATTERN', 'output_result_handler', 100, {}),
    ('PROCEDURE_RESULT', 'return status code', 'OUT status parameter', 'PATTERN', 'return_status_handler', 90, {}),
    ('PROCEDURE_RESULT', 'result set metadata', 'explicit cursor/result contract', 'PATTERN', 'result_metadata_handler', 80, {}),
    ('TABLE_VALUED', 'inline table valued function', 'RETURNS TABLE', 'PATTERN', 'inline_tvf_handler', 100, {}),
    ('TABLE_VALUED', 'multi statement table valued function', 'RETURNS SETOF/RETURNS TABLE', 'PATTERN', 'multi_tvf_handler', 90, {}),
    ('TABLE_VALUED', 'CROSS APPLY TVF', 'CROSS JOIN LATERAL', 'PATTERN', 'cross_apply_tvf_handler', 100, {}),
    ('TABLE_VALUED', 'OUTER APPLY TVF', 'LEFT JOIN LATERAL', 'PATTERN', 'outer_apply_tvf_handler', 100, {}),
    ('TABLE_VALUED', 'TVF default parameter', 'function parameter defaults', 'PATTERN', 'tvf_default_handler', 90, {}),
    ('DDL_ADVANCED', 'CREATE SCHEMA AUTHORIZATION', 'CREATE SCHEMA', 'PATTERN', 'create_schema_handler', 90, {}),
    ('DDL_ADVANCED', 'CREATE DATABASE options', 'CREATE DATABASE options review', 'PATTERN', 'create_database_handler', 80, {}),
    ('DDL_ADVANCED', 'ALTER TABLE SWITCH', 'partition/data movement strategy', 'PATTERN', 'table_switch_handler', 70, {}),
    ('DDL_ADVANCED', 'partition scheme', 'partition strategy', 'PATTERN', 'partition_scheme_handler', 80, {}),
    ('DDL_ADVANCED', 'partition function', 'partition strategy', 'PATTERN', 'partition_function_handler', 80, {}),
    ('DDL_ADVANCED', 'computed column PERSISTED', 'generated column', 'PATTERN', 'computed_column_handler', 90, {}),
    ('DDL_ADVANCED', 'SPARSE column', 'nullable/storage strategy', 'PATTERN', 'sparse_column_handler', 70, {}),
    ('DDL_ADVANCED', 'WITH CHECK OPTION', 'WITH CHECK OPTION', 'PATTERN', 'view_check_option_handler', 90, {}),
    ('DDL_ADVANCED', 'schema-bound view', 'view dependency strategy', 'PATTERN', 'schemabinding_handler', 80, {}),
    ('DDL_ADVANCED', 'DROP IF EXISTS', 'DROP IF EXISTS', 'PATTERN', 'drop_if_exists_handler', 100, {}),
    ('SPECIAL', 'IDENTITY_INSERT ON', 'identity override strategy', 'PATTERN', 'identity_insert_handler', 90, {}),
    ('SPECIAL', 'SET NOCOUNT ON', 'remove/review', 'PATTERN', 'nocount_handler', 100, {}),
    ('SPECIAL', 'SET ANSI_NULLS', 'standard NULL semantics', 'PATTERN', 'ansi_nulls_handler', 90, {}),
    ('SPECIAL', 'SET QUOTED_IDENTIFIER', 'identifier quoting strategy', 'PATTERN', 'quoted_identifier_handler', 90, {}),
    ('SPECIAL', 'SET DATEFORMAT', 'date parsing configuration', 'PATTERN', 'dateformat_handler', 80, {}),
    ('SPECIAL', 'SET LANGUAGE', 'locale configuration', 'PATTERN', 'set_language_handler', 80, {}),
    ('SPECIAL', 'SQL_VARIANT_PROPERTY()', 'type metadata strategy', 'PATTERN', 'sql_variant_property_handler', 70, {}),
    ('SPECIAL', 'CONTEXT_INFO()', 'session setting strategy', 'PATTERN', 'context_info_handler', 80, {}),
    ('SPECIAL', 'SESSION_CONTEXT set', 'set_config/current_setting', 'PATTERN', 'session_context_set_handler', 90, {}),
    ('SPECIAL', 'SYSTEM_USER', 'CURRENT_USER', 'PATTERN', 'system_user_handler', 100, {}),
    ('SPECIAL', 'HOST_NAME()', 'client/session metadata', 'PATTERN', 'host_name_handler', 80, {}),
    ('SPECIAL', 'APP_NAME()', 'application/session metadata', 'PATTERN', 'app_name_handler', 80, {}),
    ('DATA_TYPE_ADVANCED', 'ROWVERSION', 'BYTEA', 'EXACT', 'rowversion_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'SQL Server ROWVERSION is an automatically generated binary concurrency token; PostgreSQL BYTEA alone does not reproduce its generation semantics.'}),
    ('DATA_TYPE_ADVANCED', 'TIMESTAMP', 'BYTEA', 'CONTEXT', 'rowversion_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'In SQL Server TIMESTAMP is a synonym for ROWVERSION, not a date/time value. Resolve based on source schema/context.'}),
    ('DATA_TYPE_ADVANCED', 'HIERARCHYID', 'ltree OR recursive adjacency representation', 'CONTEXT', 'hierarchyid_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'postgres_extension': 'ltree (optional)', 'semantic_difference': 'Requires hierarchy representation and query rewrite; not a direct type substitution.'}),
    ('DATA_TYPE_ADVANCED', 'GEOGRAPHY', 'PostGIS geography', 'CONTEXT', 'spatial_type_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'postgres_extension': 'postgis', 'semantic_difference': 'Spatial reference, coordinate order, and supported methods must be verified.'}),
    ('DATA_TYPE_ADVANCED', 'GEOMETRY', 'PostGIS geometry', 'CONTEXT', 'spatial_type_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'postgres_extension': 'postgis', 'semantic_difference': 'Spatial reference and geometry subtype constraints must be preserved.'}),
    ('DATA_TYPE_ADVANCED', 'SQL_VARIANT', 'JSONB OR typed columns', 'CONTEXT', 'sql_variant_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'SQL_VARIANT can hold multiple supported SQL types; JSONB or a typed design needs application-specific rules.'}),
    ('DATA_TYPE_ADVANCED', 'IMAGE', 'BYTEA', 'EXACT', 'deprecated_binary_type_conversion', 30, {'level': 4, 'auto_convert': True, 'requires_review': True, 'semantic_difference': 'Legacy IMAGE is binary data; BYTEA is the PostgreSQL binary type.'}),
    ('DATA_TYPE_ADVANCED', 'NTEXT', 'TEXT', 'EXACT', 'legacy_text_type_conversion', 30, {'level': 4, 'auto_convert': True, 'requires_review': True, 'semantic_difference': 'Check Unicode and collation behavior.'}),
    ('DATA_TYPE_ADVANCED', 'NCHAR', 'CHAR', 'CONTEXT', 'unicode_char_type_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Preserve length and Unicode behavior; PostgreSQL CHAR has different padding/collation details.'}),
    ('DATA_TYPE_ADVANCED', 'NVARCHAR', 'VARCHAR', 'CONTEXT', 'unicode_varchar_type_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL text types support Unicode; preserve length constraints and collation requirements.'}),
    ('DATA_TYPE_ADVANCED', 'MONEY', 'NUMERIC(19,4)', 'EXACT', 'money_type_conversion', 30, {'level': 4, 'auto_convert': True, 'requires_review': True, 'semantic_difference': 'Verify rounding, range, and application expectations.'}),
    ('DATA_TYPE_ADVANCED', 'SMALLMONEY', 'NUMERIC(10,4)', 'EXACT', 'money_type_conversion', 30, {'level': 4, 'auto_convert': True, 'requires_review': True, 'semantic_difference': 'Verify range and rounding behavior.'}),
    ('DATA_TYPE_ADVANCED', 'XML', 'XML', 'EXACT', 'xml_type_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL XML exists, but SQL Server XML methods, schema collections, and indexing need rewrites.'}),
    ('DATA_TYPE_ADVANCED', 'VARBINARY(MAX)', 'BYTEA', 'EXACT', 'binary_type_conversion', 30, {'level': 4, 'auto_convert': True, 'requires_review': False}),
    ('DATA_TYPE_ADVANCED', 'DATETIMEOFFSET', 'TIMESTAMP WITH TIME ZONE', 'EXACT', 'datetimeoffset_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Verify offset preservation versus PostgreSQL timestamptz normalization.'}),
    ('DATA_TYPE_ADVANCED', 'DATETIME2', 'TIMESTAMP', 'CONTEXT', 'datetime_precision_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Preserve fractional-second precision.'}),
    ('DATA_TYPE_ADVANCED', 'DATETIME', 'TIMESTAMP', 'CONTEXT', 'datetime_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'SQL Server datetime range and rounding differ from PostgreSQL timestamp.'}),
    ('DATA_TYPE_ADVANCED', 'SMALLDATETIME', 'TIMESTAMP(0)', 'CONTEXT', 'smalldatetime_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'SQL Server rounds to minute; preserve this behavior if required.'}),
    ('AGGREGATE', 'COUNT_BIG', 'COUNT', 'EXACT', 'count_big_conversion', 30, {'level': 4, 'auto_convert': True}),
    ('AGGREGATE', 'STRING_AGG', 'string_agg', 'CONTEXT', 'string_agg_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Check ordering, separator, NULL handling, and source compatibility.'}),
    ('AGGREGATE', 'STDEV', 'stddev_samp', 'EXACT', 'aggregate_sample_conversion', 30, {'level': 4, 'auto_convert': True}),
    ('AGGREGATE', 'STDEVP', 'stddev_pop', 'EXACT', 'aggregate_population_conversion', 30, {'level': 4, 'auto_convert': True}),
    ('AGGREGATE', 'VAR', 'var_samp', 'EXACT', 'aggregate_sample_conversion', 30, {'level': 4, 'auto_convert': True}),
    ('AGGREGATE', 'VARP', 'var_pop', 'EXACT', 'aggregate_population_conversion', 30, {'level': 4, 'auto_convert': True}),
    ('AGGREGATE', 'CHECKSUM_AGG', 'custom aggregate / review', 'CONTEXT', 'checksum_agg_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'No equivalent checksum aggregate; define validation-specific replacement.'}),
    ('OPERATOR', '! =', '<>', 'EXACT', 'operator_spacing_normalizer', 40, {'level': 4, 'auto_convert': True}),
    ('OPERATOR', '+=', 'x := x + value', 'CONTEXT', 'compound_assignment_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'T-SQL compound assignment must be rewritten as an assignment expression/statement.'}),
    ('OPERATOR', '-=', 'x := x - value', 'CONTEXT', 'compound_assignment_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('OPERATOR', '*=', 'x := x * value', 'CONTEXT', 'compound_assignment_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('OPERATOR', '/=', 'x := x / value', 'CONTEXT', 'compound_assignment_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('OPERATOR', '%', '%', 'EXACT', 'modulo_operator_conversion', 40, {'level': 4, 'auto_convert': True}),
    ('OPERATOR', 'ISNULL predicate', 'IS NULL', 'CONTEXT', 'null_predicate_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATE_TIME', 'SYSDATETIME()', 'CURRENT_TIMESTAMP', 'CONTEXT', 'sysdatetime_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Review precision and local-time semantics.'}),
    ('DATE_TIME', 'SYSUTCDATETIME()', "CURRENT_TIMESTAMP AT TIME ZONE 'UTC'", 'CONTEXT', 'sysutcdatetime_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Use appropriate timestamptz semantics; expression type and session timezone matter.'}),
    ('DATE_TIME', 'GETDATE()', 'CURRENT_TIMESTAMP', 'EXACT', 'getdate_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATE_TIME', 'GETUTCDATE()', "CURRENT_TIMESTAMP AT TIME ZONE 'UTC'", 'CONTEXT', 'getutcdate_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATE_TIME', 'DATEADD', 'date/time arithmetic', 'CONTEXT', 'dateadd_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Rewrite datepart/value/date arguments; PostgreSQL intervals and dynamic dateparts need structural handling.'}),
    ('DATE_TIME', 'DATEDIFF', 'date/time subtraction or date_part', 'CONTEXT', 'datediff_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'SQL Server counts datepart boundaries; naive timestamp subtraction may not match.'}),
    ('DATE_TIME', 'DATEPART', 'EXTRACT', 'CONTEXT', 'datepart_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATE_TIME', 'DATENAME', 'to_char / EXTRACT', 'CONTEXT', 'datename_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATE_TIME', 'EOMONTH', "date_trunc('month', date) + interval '1 month - 1 day'", 'CONTEXT', 'eomonth_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATE_TIME', 'DAY', 'EXTRACT(DAY FROM date)', 'CONTEXT', 'day_conversion', 40, {'level': 4, 'auto_convert': False}),
    ('DATE_TIME', 'MONTH', 'EXTRACT(MONTH FROM date)', 'CONTEXT', 'month_conversion', 40, {'level': 4, 'auto_convert': False}),
    ('DATE_TIME', 'YEAR', 'EXTRACT(YEAR FROM date)', 'CONTEXT', 'year_conversion', 40, {'level': 4, 'auto_convert': False}),
    ('DATE_TIME', 'TIMEFROMPARTS', 'make_time', 'CONTEXT', 'timefromparts_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATE_TIME', 'DATEFROMPARTS', 'make_date', 'CONTEXT', 'datefromparts_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATE_TIME', 'DATETIMEFROMPARTS', 'make_timestamp', 'CONTEXT', 'datetimefromparts_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('IDENTIFIER', 'QUOTENAME', 'quote_ident', 'CONTEXT', 'quotename_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Dynamic identifier quoting must be performed safely and not confused with value parameterization.'}),
    ('IDENTIFIER', 'OBJECT_ID', 'catalog lookup', 'CONTEXT', 'object_id_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('IDENTIFIER', 'OBJECT_NAME', 'catalog lookup', 'CONTEXT', 'object_name_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('IDENTIFIER', 'SCHEMA_NAME', 'schema lookup', 'CONTEXT', 'schema_name_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('IDENTIFIER', 'COL_LENGTH', 'catalog lookup', 'CONTEXT', 'col_length_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SCHEMA', 'CREATE SCHEMA', 'CREATE SCHEMA', 'CONTEXT', 'create_schema_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SCHEMA', 'ALTER SCHEMA ... TRANSFER', 'ALTER TABLE SET SCHEMA / object move', 'CONTEXT', 'schema_transfer_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TABLE', 'CREATE TABLE', 'CREATE TABLE', 'CONTEXT', 'create_table_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TABLE', 'ALTER TABLE ... ADD', 'ALTER TABLE ADD COLUMN', 'CONTEXT', 'alter_table_add_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TABLE', 'ALTER TABLE ... ALTER COLUMN', 'ALTER TABLE ALTER COLUMN', 'CONTEXT', 'alter_column_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TABLE', 'ALTER TABLE ... DROP COLUMN', 'ALTER TABLE DROP COLUMN', 'CONTEXT', 'drop_column_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TABLE', 'sp_rename table/column', 'ALTER TABLE ... RENAME', 'CONTEXT', 'sp_rename_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TABLE', 'IDENTITY(seed, increment)', 'GENERATED ... AS IDENTITY', 'CONTEXT', 'identity_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Preserve seed, increment, restart behavior, and identity mode.'}),
    ('TABLE', 'computed column', 'generated column or trigger', 'CONTEXT', 'computed_column_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL generated-column restrictions and expression support differ.'}),
    ('VIEW', 'CREATE VIEW', 'CREATE VIEW', 'CONTEXT', 'create_view_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('VIEW', 'WITH SCHEMABINDING', 'remove / dependency enforcement rewrite', 'CONTEXT', 'schemabinding_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('VIEW', 'indexed view', 'materialized view or index redesign', 'CONTEXT', 'indexed_view_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SYNONYM', 'CREATE SYNONYM', 'view or search_path / application mapping', 'CONTEXT', 'synonym_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CONSTRAINT', 'PRIMARY KEY', 'PRIMARY KEY', 'EXACT', 'constraint_conversion', 40, {'level': 4, 'auto_convert': True}),
    ('CONSTRAINT', 'FOREIGN KEY', 'FOREIGN KEY', 'CONTEXT', 'foreign_key_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Review cascade actions, deferrability, and validation state.'}),
    ('CONSTRAINT', 'CHECK constraint', 'CHECK constraint', 'CONTEXT', 'check_constraint_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CONSTRAINT', 'DEFAULT constraint', 'DEFAULT expression', 'CONTEXT', 'default_constraint_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CONSTRAINT', 'UNIQUE constraint', 'UNIQUE constraint', 'CONTEXT', 'unique_constraint_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('INDEX', 'CREATE CLUSTERED INDEX', 'CREATE INDEX', 'CONTEXT', 'clustered_index_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL does not have SQL Server clustered-index storage semantics.'}),
    ('INDEX', 'CREATE NONCLUSTERED INDEX', 'CREATE INDEX', 'CONTEXT', 'nonclustered_index_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('INDEX', 'INCLUDE columns', 'covering index columns / index-only scan consideration', 'CONTEXT', 'include_index_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('INDEX', 'filtered index', 'partial index WHERE', 'CONTEXT', 'filtered_index_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DDL_ADVANCED', 'partition scheme/function', 'PARTITION BY', 'CONTEXT', 'partition_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Partition boundaries, partition key, and maintenance strategy must be redesigned.'}),
    ('DDL_ADVANCED', 'FILEGROUP', 'tablespace', 'CONTEXT', 'filegroup_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DDL_ADVANCED', 'DATA_COMPRESSION', 'table/index storage parameters', 'CONTEXT', 'compression_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DDL_ADVANCED', 'temporal table SYSTEM_VERSIONING', 'trigger/history table or application temporal design', 'CONTEXT', 'temporal_table_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DDL_ADVANCED', 'ledger table', 'audit architecture / append-only controls', 'CONTEXT', 'ledger_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PROCEDURE_RESULT', 'SELECT result set from procedure', 'REFCURSOR or explicit result contract', 'CONTEXT', 'procedure_resultset_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Keep PostgreSQL procedure; caller opens/fetches cursor or uses agreed OUT/INOUT contract. Do not convert procedure to function.'}),
    ('PROCEDURE_RESULT', 'multiple result sets', 'multiple REFCURSOR outputs or staged result contract', 'CONTEXT', 'multiple_resultset_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Define result ordering, cursor names, caller transaction, and fetch behavior.'}),
    ('PROCEDURE', 'RETURN integer status', 'OUT parameter / procedure status contract', 'CONTEXT', 'procedure_return_status_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PROCEDURE', 'EXEC procedure with named arguments', 'CALL procedure with named arguments', 'CONTEXT', 'procedure_call_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PROCEDURE', 'INSERT EXEC', 'CALL plus staging/refcursor processing', 'CONTEXT', 'insert_exec_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PROCEDURE', 'EXECUTE AS', 'SECURITY DEFINER or role-based design', 'CONTEXT', 'execute_as_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CONTROL_FLOW', 'IF ... ELSE', 'IF ... THEN ... ELSE ... END IF', 'CONTEXT', 'if_else_conversion', 40, {'level': 4, 'auto_convert': False}),
    ('CONTROL_FLOW', 'DECLARE @variable', 'DECLARE variable', 'CONTEXT', 'variable_declaration_conversion', 40, {'level': 4, 'auto_convert': False}),
    ('TEMP_TABLE', 'table variable @table', 'temporary table or array/composite type', 'CONTEXT', 'table_variable_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Choose temp-table lifecycle, indexes, transaction behavior, and scope.'}),
    ('WINDOW', 'PERCENTILE_CONT', 'percentile_cont', 'CONTEXT', 'percentile_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('WINDOW', 'PERCENTILE_DISC', 'percentile_disc', 'CONTEXT', 'percentile_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('WINDOW', 'FIRST_VALUE', 'first_value', 'CONTEXT', 'window_function_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('WINDOW', 'LAST_VALUE', 'last_value', 'CONTEXT', 'window_function_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Window frame defaults may differ; preserve explicit frame semantics.'}),
    ('TRANSACTION', 'SET XACT_ABORT ON', 'exception/transaction policy', 'CONTEXT', 'xact_abort_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('TRANSACTION', 'SET TRANSACTION ISOLATION LEVEL', 'SET TRANSACTION ISOLATION LEVEL', 'CONTEXT', 'isolation_level_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('ERROR_HANDLING', 'TRY ... CATCH', 'BEGIN ... EXCEPTION', 'CONTEXT', 'try_catch_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PRIVILEGE', 'GRANT SELECT/INSERT/UPDATE/DELETE', 'GRANT privileges', 'CONTEXT', 'grant_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('PRIVILEGE', 'DENY', 'REVOKE or role design', 'CONTEXT', 'deny_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL has no SQL Server DENY equivalent with the same precedence model.'}),
    ('PRIVILEGE', 'GRANT EXECUTE', 'GRANT EXECUTE', 'CONTEXT', 'execute_privilege_conversion', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SECURITY', 'row-level security policy', 'CREATE POLICY', 'CONTEXT', 'rls_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SECURITY', 'dynamic masking', 'view / expression / privilege strategy', 'CONTEXT', 'dynamic_masking_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SECURITY', 'certificate / asymmetric key', 'PostgreSQL cryptographic facilities / external KMS', 'CONTEXT', 'key_management_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('EXTENSION', 'PostGIS spatial requirement', 'CREATE EXTENSION postgis', 'CONTEXT', 'extension_requirement', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('EXTENSION', 'ltree hierarchy requirement', 'CREATE EXTENSION ltree', 'CONTEXT', 'extension_requirement', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('EXTENSION', 'pgcrypto encryption/hash requirement', 'CREATE EXTENSION pgcrypto', 'CONTEXT', 'extension_requirement', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('COMPATIBILITY', 'SQL Server compatibility level', 'PostgreSQL version capability checks', 'CONTEXT', 'compatibility_level_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('COMPATIBILITY', 'SQL Server feature not supported in target PG', 'unsupported-feature report', 'CONTEXT', 'unsupported_feature_detection', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SEQUENCE_ADVANCED', 'IDENT_CURRENT', 'sequence catalog lookup', 'CONTEXT', 'ident_current_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Sequence ownership and concurrent usage make a simple last-value expression unsafe.'}),
    ('SEQUENCE_ADVANCED', 'DBCC CHECKIDENT', 'ALTER SEQUENCE RESTART / setval', 'CONTEXT', 'checkident_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATA_MIGRATION', 'SQL Server row count validation', 'PostgreSQL row count validation', 'CONTEXT', 'row_count_validation', 40, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATA_MIGRATION', 'checksum validation', 'hash/checksum validation with type normalization', 'CONTEXT', 'checksum_validation', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATA_MIGRATION', 'identity seed validation', 'sequence state validation', 'CONTEXT', 'identity_sequence_validation', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATA_MIGRATION', 'constraint validation', 'constraint and index validation', 'CONTEXT', 'constraint_validation', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATA_MIGRATION', 'date/time validation', 'timezone and precision validation', 'CONTEXT', 'datetime_validation', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('DATA_MIGRATION', 'source-target comparison', 'source/target reconciliation report', 'CONTEXT', 'data_reconciliation', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('ASSEMBLY', 'CREATE ASSEMBLY', 'native PostgreSQL code / extension / external service', 'CONTEXT', 'clr_assembly_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('ASSEMBLY', 'CLR stored procedure/function', 'PL/pgSQL procedure or external service', 'CONTEXT', 'clr_routine_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('FULL_TEXT', 'CONTAINS', 'tsquery/@@', 'CONTEXT', 'fulltext_contains_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('FULL_TEXT', 'FREETEXT', 'to_tsvector / plainto_tsquery', 'CONTEXT', 'freetext_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('FULL_TEXT', 'CONTAINSTABLE', 'full-text query plus ranked result rewrite', 'CONTEXT', 'containstable_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SPATIAL', 'STDistance', 'ST_Distance', 'CONTEXT', 'spatial_method_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'postgres_extension': 'postgis'}),
    ('SPATIAL', 'STIntersects', 'ST_Intersects', 'CONTEXT', 'spatial_method_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'postgres_extension': 'postgis'}),
    ('SPATIAL', 'STContains', 'ST_Contains', 'CONTEXT', 'spatial_method_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'postgres_extension': 'postgis'}),
    ('SPATIAL', 'STWithin', 'ST_Within', 'CONTEXT', 'spatial_method_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True, 'postgres_extension': 'postgis'}),
    ('AGENT_JOB', 'SQL Server Agent job', 'pg_cron / external scheduler / orchestration', 'CONTEXT', 'agent_job_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('AGENT_JOB', 'job schedule', 'cron schedule or scheduler configuration', 'CONTEXT', 'job_schedule_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SERVICE', 'Service Broker', 'PostgreSQL queue / external messaging system', 'CONTEXT', 'service_broker_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SERVICE', 'Database Mail', 'external mail service / application integration', 'CONTEXT', 'database_mail_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('REPLICATION', 'CDC', 'logical decoding / CDC platform', 'CONTEXT', 'cdc_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('REPLICATION', 'Change Tracking', 'audit table / trigger / logical change tracking', 'CONTEXT', 'change_tracking_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('REPLICATION', 'SQL Server replication', 'PostgreSQL replication architecture / migration tooling', 'CONTEXT', 'replication_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CROSS_DATABASE', 'OPENQUERY', 'FDW / dblink / ETL rewrite', 'CONTEXT', 'openquery_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('CROSS_DATABASE', 'OPENROWSET', 'foreign table / external ETL / import rewrite', 'CONTEXT', 'openrowset_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SPECIAL', 'PIVOT', 'conditional aggregation / tablefunc', 'CONTEXT', 'pivot_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SPECIAL', 'UNPIVOT', 'VALUES / UNION ALL / unnest rewrite', 'CONTEXT', 'unpivot_conversion', 20, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SPECIAL', 'CROSS APPLY', 'CROSS JOIN LATERAL', 'CONTEXT', 'cross_apply_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SPECIAL', 'OUTER APPLY', 'LEFT JOIN LATERAL', 'CONTEXT', 'outer_apply_conversion', 30, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('SPECIAL', 'MERGE', 'INSERT/UPDATE/DELETE rewrite or PostgreSQL MERGE', 'CONTEXT', 'merge_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Check target PostgreSQL version, matched/unmatched logic, concurrency, and output behavior.'}),
    ('SPECIAL', 'WITH ENCRYPTION', 'unsupported; external protection / access controls', 'CONTEXT', 'procedure_encryption_conversion', 10, {'level': 4, 'auto_convert': False, 'requires_review': True}),
    ('COLLATION', 'COLLATE Latin1_General_CI_AS', 'COLLATE "default" / icu collation', 'PATTERN', 'collation_handler', 80, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL default collation is database or column-level; case-insensitive collations require ICU collations, citext, or LOWER().'}),
    ('COLLATION', 'DATABASE_DEFAULT', 'COLLATE "default"', 'PATTERN', 'collation_handler', 90, {'level': 4, 'auto_convert': True, 'requires_review': False, 'semantic_difference': 'Explicit collation override resolving to database default collation.'}),
    ('COLLATION', 'CI_AS / CS_AS sensitivity', 'citext / LOWER() / COLLATE', 'CONTEXT', 'collation_sensitivity_handler', 80, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'SQL Server case/accent sensitivity differences require citext extension, expression indexes, or ILIKE.'}),
    ('FUNCTION_CONVERSION', 'CHECKSUM()', 'md5() / hashtext()', 'PATTERN', 'checksum_handler', 80, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'SQL Server CHECKSUM returns a 32-bit int hash; PostgreSQL does not have direct equivalent, use hashtext() or md5().'}),
    ('FUNCTION_CONVERSION', 'BINARY_CHECKSUM()', 'md5() / hashtext()', 'PATTERN', 'binary_checksum_handler', 80, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Binary-level hash; use md5() or digest() via pgcrypto.'}),
    ('FUNCTION_CONVERSION', 'PARSE()', 'TO_DATE() / TO_TIMESTAMP() / CAST', 'PATTERN', 'parse_handler', 80, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PARSE uses culture info; translate culture format to PostgreSQL to_date/to_timestamp format.'}),
    ('FUNCTION_CONVERSION', 'TRY_PARSE()', 'safe parse / regex validation', 'PATTERN', 'try_parse_handler', 80, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Culture-aware try-parse; rewrite with regex validation or safe cast wrapper.'}),
    ('FUNCTION_CONVERSION', 'SERVERPROPERTY()', 'current_setting() / version()', 'PATTERN', 'serverproperty_handler', 80, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Server metadata lookup; map specific property names to PostgreSQL SHOW / current_setting().'}),
    ('FUNCTION_CONVERSION', 'ERROR_SEVERITY()', 'diagnostic context', 'PATTERN', 'error_severity_handler', 80, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL exceptions have log levels (NOTICE, WARNING, EXCEPTION) rather than integer severities.'}),
    ('FUNCTION_CONVERSION', 'ERROR_STATE()', 'SQLSTATE', 'PATTERN', 'error_state_handler', 90, {'level': 4, 'auto_convert': True, 'requires_review': False, 'semantic_difference': 'Maps to PostgreSQL SQLSTATE exception code.'}),
    ('PERFORMANCE', 'FORCE ORDER', 'join_collapse_limit = 1', 'PATTERN', 'performance_hint_handler', 70, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL planner respects FROM order when join_collapse_limit = 1.'}),
    ('PERFORMANCE', 'LOOP / MERGE / HASH JOIN hints', 'enable_nestloop / enable_mergejoin / enable_hashjoin', 'PATTERN', 'join_hint_handler', 70, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Session or query-level planner method flags.'}),
    ('PERFORMANCE', 'OPTIMIZE FOR UNKNOWN', 'generic query plan', 'PATTERN', 'optimize_hint_handler', 70, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Prevents parameter sniffing; in PostgreSQL, use PREPARE or plan_cache_mode = force_generic_plan.'}),
    ('TABLE_VALUED', 'Table-Valued Parameter (TVP)', 'composite type array / temporary table / JSONB', 'CONTEXT', 'tvp_handler', 90, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Pass TVPs as array of composite type (my_type[]), JSONB, or stage in a temp table.'}),
    ('TABLE_VALUED', 'CREATE TYPE ... AS TABLE', 'CREATE TYPE ... AS (composite type)', 'CONTEXT', 'table_type_handler', 90, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'Table types become PostgreSQL composite types or schemas for staging tables.'}),
    ('SYNTAX', 'OUTPUT INTO @table', 'RETURNING ... INTO / staging CTE', 'PATTERN', 'output_into_handler', 90, {'level': 4, 'auto_convert': False, 'requires_review': True, 'semantic_difference': 'PostgreSQL uses RETURNING col INTO var or WITH inserted AS (...) INSERT INTO target.'}),
]

# =========================================================
# HIGH-PERFORMANCE SEEDING FUNCTIONS (SQLAlchemy Models)
# =========================================================

def seed_dialects(session: Session) -> None:
    """Seed or verify supported RDBMS dialects in batch."""
    records = [
        {
            "dialect_name": name,
            "dialect_code": code,
            "is_active": is_active,
        }
        for name, code, is_active in DIALECTS
    ]
    stmt = (
        insert(RdbmsDialect)
        .values(records)
        .on_conflict_do_nothing(index_elements=["dialect_code"])
    )
    session.execute(stmt)


def seed_categories(session: Session) -> None:
    """Seed or verify conversion categories in batch."""
    records = [
        {
            "category_name": cat_name,
            "description": desc,
        }
        for cat_name, desc in CATEGORIES
    ]
    stmt = (
        insert(ConversionCategory)
        .values(records)
        .on_conflict_do_nothing(index_elements=["category_name"])
    )
    session.execute(stmt)


def get_dialect_ids(session: Session) -> Tuple[int, int]:
    """Fetch dialect code to ID map."""
    rows = session.execute(
        select(RdbmsDialect.dialect_code, RdbmsDialect.dialect_id)
    ).all()
    dialect_map = dict(rows)
    for code in ("MSSQL", "POSTGRES"):
        if code not in dialect_map:
            raise ValueError(f"Dialect not found in database: {code}")
    return dialect_map["MSSQL"], dialect_map["POSTGRES"]


def get_category_map(session: Session) -> Dict[str, int]:
    """Pre-fetch all category names to IDs to eliminate N+1 lookups."""
    rows = session.execute(
        select(ConversionCategory.category_name, ConversionCategory.category_id)
    ).all()
    return dict(rows)


def seed_mappings(
    session: Session, source_dialect_id: int, target_dialect_id: int
) -> int:
    """
    Batch insert all conversion mappings using SQLAlchemy insert with conflict safety.
    """
    category_map = get_category_map(session)

    records = []
    for mapping in MAPPINGS:
        (
            category_name,
            source_value,
            target_value,
            match_type,
            handler_name,
            priority,
            metadata,
        ) = mapping

        category_id = category_map.get(category_name)
        if not category_id:
            raise ValueError(
                f"Category '{category_name}' not found in conversion_category table."
            )

        meta = dict(metadata) if isinstance(metadata, dict) else {}
        if handler_name and "handler_name" not in meta:
            meta["handler_name"] = handler_name

        records.append({
            "source_dialect_id": source_dialect_id,
            "target_dialect_id": target_dialect_id,
            "category_id": category_id,
            "source_value": source_value,
            "target_value": target_value,
            "match_type": match_type,
            "priority": priority,
            "metadata": meta,
            "is_active": True,
        })

    if not records:
        return 0

    stmt = (
        insert(ConversionMapping.__table__)
        .values(records)
        .on_conflict_do_nothing(
            index_elements=[
                "source_dialect_id",
                "target_dialect_id",
                "category_id",
                "source_value",
            ]
        )
        .returning(ConversionMapping.mapping_id)
    )

    result = session.execute(stmt)
    inserted_rows = result.all()
    return len(inserted_rows)


# =========================================================
# MAIN EXECUTION
# =========================================================

def main():
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL not found. Please configure it in your .env file."
        )

    print("=" * 65)
    print("Starting Optimized MSSQL -> PostgreSQL Comprehensive Seeder")
    print(f"Total Unique Mappings to Process: {len(MAPPINGS)}")
    print(f"Total Categories: {len(CATEGORIES)}")
    print("=" * 65)

    start_time = time.perf_counter()

    try:
        with SessionLocal() as session:
            with session.begin():
                # 1. Batch seed dialects
                seed_dialects(session)
                print("[1/3] Dialects verified.")

                # 2. Batch seed categories
                seed_categories(session)
                print("[2/3] Categories verified.")

                # 3. Retrieve cached dialect IDs
                source_id, target_id = get_dialect_ids(session)

                # 4. Batch seed deduplicated mappings
                inserted_count = seed_mappings(session, source_id, target_id)
                print("[3/3] Conversion mappings processed.")

            elapsed = time.perf_counter() - start_time
            skipped_count = len(MAPPINGS) - inserted_count

            print("-" * 65)
            print(f"Seed completed successfully in {elapsed:.2f}s.")
            print(f"Total Mapping Rules Defined: {len(MAPPINGS)}")
            print(f"New Mappings Inserted:       {inserted_count}")
            print(f"Skipped (Already Existing):  {skipped_count}")
            print("=" * 65)

    except Exception as error:
        print(f"\n[ERROR] Seeding failed: {error}")
        raise


if __name__ == "__main__":
    main()
