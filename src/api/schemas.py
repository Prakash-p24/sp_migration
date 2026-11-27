"""Pydantic schemas for the migration API."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class MigrationRequest(BaseModel):
    """Validated request body for a stored-procedure migration."""

    source: Literal["mssql", "mysql"] = Field(description="Source SQL dialect")
    target: Literal["postgres"] = Field(description="Target SQL dialect")
    source_code: str = Field(
        min_length=1, description="Stored procedure SQL to migrate"
    )


class MigrationResponse(BaseModel):
    """Successful PostgreSQL procedure generation response."""

    source: str
    target: str
    status: Literal["completed"]
    message: str
    procedures: list[str]
    converted_code: str
    ir: dict[str, Any]
