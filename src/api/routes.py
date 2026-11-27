"""HTTP routes for stored-procedure migrations."""

from fastapi import APIRouter, HTTPException

from src.core.migration_engine import MigrationEngine, MigrationNotImplementedError
from src.core.pipeline import MigrationPipeline
from src.api.schemas import MigrationRequest, MigrationResponse

router = APIRouter(prefix="/api/v1", tags=["migrations"])
migration_engine = MigrationEngine(MigrationPipeline())


@router.post("/migrations", response_model=MigrationResponse)
def migrate_stored_procedure(request: MigrationRequest):
    """Parse a stored procedure from a supported source dialect."""
    try:
        result = migration_engine.migrate_sql(
            request.source_code,
            source_dialect=request.source,
            target_dialect=request.target,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MigrationNotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return MigrationResponse(**result)
