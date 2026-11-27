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

### Run with Docker Compose

Compose reads database settings from a local `.env` file. Create it from the
example, then replace the placeholder credentials and database name with your
PostgreSQL connection details:

```powershell
Copy-Item .env.example .env
```

Then start the service:

```powershell
docker compose up --build -d
```

The `.env` file is ignored by Git. For PostgreSQL running on the same Windows
machine, `host.docker.internal` can be used as the database host from inside
the container.

## Database migrations and seeding

### 1. Apply database migrations

When running with Docker, migrations run automatically on container startup via `docker-entrypoint.sh`.

To apply migrations manually or when running locally:

```powershell
# Inside Docker (manual run)
docker exec -it sp-migration alembic upgrade head

# Or locally using Poetry
poetry run alembic upgrade head
```

### 2. Seed conversion mappings

Populate supported dialects, categories, and conversion mapping rules into PostgreSQL:

```powershell
# Using Docker (recommended)
docker exec -it sp-migration python scripts/seed_mssql_postgres.py

# Or locally using Poetry
poetry run python scripts/seed_mssql_postgres.py
```

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

File
└── Batch
    └── Procedure: dbo.GetCustomers