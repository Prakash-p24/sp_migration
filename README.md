# Stored Procedure Migration

This project contains the application-owned components for migrating stored
procedures from MSSQL or MySQL to PostgreSQL. The source-to-target architecture
is organized around parsing, a shared intermediate representation (IR),
dialect-specific converters, PostgreSQL generation, and validation.

## Current implementation status

- MSSQL/T-SQL has an ANTLR grammar and a parser adapter.
- MySQL parsing and both dialects' IR visitors, conversion stages, and SQL
  generation are not implemented yet.
- The migration endpoint and engine are wired, but the pipeline and several
  analyzers/validators remain scaffolds. The service does not claim to perform
  SQL conversion until those stages are implemented.

The MSSQL parser can be used directly:

```python
from src.parsers.mssql_parser import MSSQLParser

parse_tree = MSSQLParser().parse("SELECT 1;")
```

Parsing checks syntax only; it does not translate a stored procedure or prove
semantic equivalence.

## Project layout

```text
config/                 Migration configuration
docs/                   Architecture, conversion rules, and testing guidance
scripts/                Parser-generation scripts
src/
  api/                  Reusable FastAPI routers and request/response schemas
  analyzers/            Migration analysis
  converters/           MSSQL/MySQL-to-PostgreSQL conversion stages
  core/                 Migration engine, pipeline, and component registry
  database/             Source routine and metadata database utilities
  generated/             Generated ANTLR modules (protected; do not edit)
  generators/            PostgreSQL SQL generation
  grammar/               ANTLR grammar sources (protected; do not edit)
  ir/                    Dialect-neutral intermediate representation
  mappings/              Dialect mapping tables
  parsers/               Source parser adapters
  utils/                 Shared application utilities
  validators/            Syntax, compatibility, and output validation
  visitors/              Parse-tree-to-IR visitors
tests/                  Unit, integration, regression, and fixture data
```

## Run the service

```powershell
poetry run uvicorn src.main:app --reload
```

OpenAPI documentation is available at `http://localhost:8000/docs`.

The migration request endpoint is `POST /api/v1/migrations`:

```json
{
  "source": "mssql",
  "target": "postgres",
  "source_code": "CREATE PROCEDURE sp_test AS BEGIN SELECT 1; END"
}
```

It accepts `mssql` or `mysql` as the source and `postgres` as the target.
The endpoint is wired to the migration engine, but the end-to-end conversion
stages are still scaffolds, so valid migration requests currently receive HTTP
`501 Not Implemented` with an explanatory message. Invalid dialects receive
HTTP `422`.

The migration routes live in `src.api.routes` and are included by `src.main`.
Another FastAPI application can reuse them with
`app.include_router(migration_router)`. The router owns the `/api/v1` prefix.

## Run tests

```powershell
poetry run pytest
```

## Parser generation

ANTLR grammar sources and generated parser files are intentionally left
unchanged by application refactors. The scripts under `scripts/` describe the
generation workflow; run them only when intentionally updating grammar
artifacts.


