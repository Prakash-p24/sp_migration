"""HTTP routes for stored-procedure migrations."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.migration_engine import MigrationEngine, MigrationNotImplementedError
from src.core.pipeline import MigrationPipeline

router = APIRouter(prefix="/api/v1", tags=["migrations"])
migration_engine = MigrationEngine(MigrationPipeline())


class MigrationRequest(BaseModel):
    source: Literal["mssql", "mysql"] = Field(description="Source SQL dialect")
    target: Literal["postgres"] = Field(description="Target SQL dialect")
    source_code: str = Field(min_length=1, description="Stored procedure SQL to migrate")


class MigrationResponse(BaseModel):
    source: str
    target: str
    status: Literal["completed"]
    converted_code: str


@router.post("/migrations", response_model=MigrationResponse)
def migrate_stored_procedure(request: MigrationRequest):
    """Convert a stored procedure from a supported source dialect to PostgreSQL."""
    try:
        converted_code = migration_engine.migrate_sql(
            request.source_code,
            source_dialect=request.source,
            target_dialect=request.target,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MigrationNotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return MigrationResponse(
        source=request.source,
        target=request.target,
        status="completed",
        converted_code=converted_code,
    )
