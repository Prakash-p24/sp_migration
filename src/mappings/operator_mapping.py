"""Central operator mapping tables."""

# SQL Server operators that do not have PostgreSQL spellings.
MSSQL_TO_POSTGRES = {
    "!<": ">=",
    "!>": "<=",
}

MYSQL_TO_POSTGRES = {}
