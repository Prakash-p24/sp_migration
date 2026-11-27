"""Read conversion metadata required by the migration pipeline."""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import aliased


def load_data_type_mappings(
    source_dialect: str,
    target_dialect: str,
    source_types: set[str] | list[str] | tuple[str, ...],
) -> dict[str, str]:
    """Load only DATA_TYPE rules needed by this procedure, in one query.

    The returned keys are normalized source type names. Priority ordering makes
    the selected target deterministic if legacy data contains duplicate rules.
    """
    from src.database.connection import SessionLocal
    from src.database.models import ConversionCategory, ConversionMapping, RdbmsDialect

    source_model = aliased(RdbmsDialect)
    target_model = aliased(RdbmsDialect)
    source_code = source_dialect.strip().upper()
    target_code = target_dialect.strip().upper()
    source_codes = {source_code}
    target_codes = {target_code}
    if source_code in {"MSSQL", "SQLSERVER", "TSQL"}:
        source_codes.update({"MSSQL", "SQLSERVER", "TSQL"})
    if target_code in {"POSTGRES", "POSTGRESQL", "PG"}:
        target_codes.update({"POSTGRES", "POSTGRESQL", "PG"})

    lookup_types: set[str] = set()
    for source_type in source_types:
        normalized = " ".join(source_type.strip().upper().split())
        if not normalized:
            continue
        lookup_types.add(normalized)
        base_match = re.match(r"^([A-Z_][A-Z0-9_ ]*)\s*\(", normalized)
        if base_match:
            lookup_types.add(" ".join(base_match.group(1).split()))
    if not lookup_types:
        return {}

    statement = (
        select(ConversionMapping.source_value, ConversionMapping.target_value)
        .join(
            ConversionCategory,
            ConversionCategory.category_id == ConversionMapping.category_id,
        )
        .join(
            source_model,
            source_model.dialect_id == ConversionMapping.source_dialect_id,
        )
        .join(
            target_model,
            target_model.dialect_id == ConversionMapping.target_dialect_id,
        )
        .where(
            ConversionMapping.is_active.is_(True),
            ConversionMapping.target_value.is_not(None),
            func.upper(ConversionCategory.category_name) == "DATA_TYPE",
            func.upper(source_model.dialect_code).in_(source_codes),
            func.upper(target_model.dialect_code).in_(target_codes),
            func.upper(ConversionMapping.source_value).in_(lookup_types),
            source_model.is_active.is_(True),
            target_model.is_active.is_(True),
        )
        .order_by(ConversionMapping.priority.asc(), ConversionMapping.mapping_id.asc())
    )

    with SessionLocal() as session:
        rows = session.execute(statement).all()

    mappings: dict[str, str] = {}
    for source_value, target_value in rows:
        normalized = " ".join(source_value.strip().upper().split())
        mappings.setdefault(normalized, target_value.strip())
    return mappings


def load_syntax_mappings(
    source_dialect: str,
    target_dialect: str,
    constructs: set[str] | list[str] | tuple[str, ...],
) -> dict[str, str]:
    """Load only syntax rules needed by the supplied procedure from metadata."""
    from src.database.connection import SessionLocal
    from src.database.models import ConversionCategory, ConversionMapping, RdbmsDialect

    requested = {item.strip().upper() for item in constructs if item.strip()}
    if not requested:
        return {}

    source_model = aliased(RdbmsDialect)
    target_model = aliased(RdbmsDialect)
    source_codes = {source_dialect.strip().upper()}
    target_codes = {target_dialect.strip().upper()}
    if source_codes & {"MSSQL", "SQLSERVER", "TSQL"}:
        source_codes.update({"MSSQL", "SQLSERVER", "TSQL"})
    if target_codes & {"POSTGRES", "POSTGRESQL", "PG"}:
        target_codes.update({"POSTGRES", "POSTGRESQL", "PG"})

    statement = (
        select(ConversionMapping.source_value, ConversionMapping.target_value)
        .join(ConversionCategory, ConversionCategory.category_id == ConversionMapping.category_id)
        .join(source_model, source_model.dialect_id == ConversionMapping.source_dialect_id)
        .join(target_model, target_model.dialect_id == ConversionMapping.target_dialect_id)
        .where(
            ConversionMapping.is_active.is_(True),
            ConversionMapping.target_value.is_not(None),
            func.upper(ConversionCategory.category_name) == "SYNTAX",
            func.upper(source_model.dialect_code).in_(source_codes),
            func.upper(target_model.dialect_code).in_(target_codes),
            func.upper(ConversionMapping.source_value).in_(requested),
            source_model.is_active.is_(True),
            target_model.is_active.is_(True),
        )
        .order_by(ConversionMapping.priority.asc(), ConversionMapping.mapping_id.asc())
    )
    with SessionLocal() as session:
        rows = session.execute(statement).all()

    mappings: dict[str, str] = {}
    for source_value, target_value in rows:
        mappings.setdefault(source_value.strip().upper(), target_value.strip())
    return mappings
