"""Tests for database models and metadata."""

import pytest
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from src.database.connection import Base
from src.database.models import (
    ConversionCategory,
    ConversionMapping,
    RdbmsDialect,
    SpMigrationHistory,
)


def test_models_registered_in_metadata():
    """Verify that all four models are properly registered in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "rdbms_dialect",
        "conversion_category",
        "conversion_mapping",
        "sp_migration_history",
    }
    assert expected.issubset(table_names)
    assert "conversion_handler" not in table_names


def test_rdbms_dialect_columns():
    table = Base.metadata.tables["rdbms_dialect"]
    assert isinstance(table.c.dialect_id.type, BigInteger)
    assert table.c.dialect_id.primary_key is True
    assert isinstance(table.c.dialect_name.type, String)
    assert table.c.dialect_name.nullable is False
    assert isinstance(table.c.dialect_code.type, String)
    assert table.c.dialect_code.nullable is False
    assert isinstance(table.c.is_active.type, Boolean)


def test_conversion_category_columns():
    table = Base.metadata.tables["conversion_category"]
    assert isinstance(table.c.category_id.type, BigInteger)
    assert table.c.category_id.primary_key is True
    assert isinstance(table.c.category_name.type, String)
    assert table.c.category_name.nullable is False
    assert isinstance(table.c.description.type, Text)
    assert table.c.description.nullable is True


def test_conversion_mapping_columns_and_constraints():
    table = Base.metadata.tables["conversion_mapping"]
    assert isinstance(table.c.mapping_id.type, BigInteger)
    assert table.c.mapping_id.primary_key is True
    assert isinstance(table.c.source_value.type, Text)
    assert table.c.source_value.nullable is False
    assert isinstance(table.c.metadata.type, JSONB)
    assert isinstance(table.c.priority.type, Integer)
    assert "handler_name" not in table.c

    # Check foreign keys
    fk_targets = {fk.target_fullname for fk in table.foreign_keys}
    assert "rdbms_dialect.dialect_id" in fk_targets
    assert "conversion_category.category_id" in fk_targets

    # Check index
    index_names = {idx.name for idx in table.indexes}
    assert "idx_mapping_lookup" in index_names


def test_conversion_mapping_instantiation_metadata_alias():
    """Verify that ConversionMapping handles both metadata and metadata_ in constructor."""
    mapping = ConversionMapping(
        source_dialect_id=1,
        target_dialect_id=2,
        category_id=1,
        source_value="INT",
        target_value="INTEGER",
        metadata={"note": "test"},
    )
    assert mapping.metadata_ == {"note": "test"}


def test_sp_migration_history_columns():
    table = Base.metadata.tables["sp_migration_history"]
    assert isinstance(table.c.migration_id.type, BigInteger)
    assert table.c.migration_id.primary_key is True
    assert isinstance(table.c.procedure_name.type, String)
    assert table.c.procedure_name.nullable is False
    assert isinstance(table.c.source_code.type, Text)
    assert table.c.source_code.nullable is False
    assert isinstance(table.c.issues.type, JSONB)

    # Check foreign keys
    fk_targets = {fk.target_fullname for fk in table.foreign_keys}
    assert "rdbms_dialect.dialect_id" in fk_targets
