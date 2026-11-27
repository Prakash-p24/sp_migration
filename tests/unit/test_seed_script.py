"""Tests for seed_mssql_postgres script logic and data integrity."""

import pytest
from unittest.mock import MagicMock
from scripts.seed_mssql_postgres import (
    CATEGORIES,
    DIALECTS,
    MAPPINGS,
    seed_dialects,
    seed_categories,
    seed_mappings,
)


def test_seed_data_counts():
    """Verify that expected rules and categories are defined."""
    assert len(DIALECTS) >= 2
    assert len(CATEGORIES) == 56
    assert len(MAPPINGS) == 453


def test_categories_unique():
    """Ensure category names are unique."""
    cat_names = [c[0] for c in CATEGORIES]
    assert len(cat_names) == len(set(cat_names))


def test_mapping_categories_exist():
    """Verify that every mapping refers to a valid defined category."""
    valid_categories = {c[0] for c in CATEGORIES}
    for mapping in MAPPINGS:
        cat_name = mapping[0]
        assert cat_name in valid_categories, f"Invalid category: {cat_name}"


def test_seed_dialects_compiles():
    """Test seed_dialects logic with a mock session."""
    mock_session = MagicMock()
    seed_dialects(mock_session)
    assert mock_session.execute.called


def test_seed_categories_compiles():
    """Test seed_categories logic with a mock session."""
    mock_session = MagicMock()
    seed_categories(mock_session)
    assert mock_session.execute.called
