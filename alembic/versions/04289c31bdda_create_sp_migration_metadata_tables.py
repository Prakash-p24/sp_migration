"""create_sp_migration_metadata_tables

Revision ID: 04289c31bdda
Revises: 
Create Date: 2026-11-27 09:55:29.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '04289c31bdda'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create dialects, categories, mappings, and migration history."""
    # 1. rdbms_dialect table
    op.create_table(
        'rdbms_dialect',
        sa.Column('dialect_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('dialect_name', sa.String(length=50), nullable=False),
        sa.Column('dialect_code', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('dialect_id', name='pk_rdbms_dialect'),
        sa.UniqueConstraint('dialect_name', name='uq_rdbms_dialect_dialect_name'),
        sa.UniqueConstraint('dialect_code', name='uq_rdbms_dialect_dialect_code'),
    )

    # 2. conversion_category table
    op.create_table(
        'conversion_category',
        sa.Column('category_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('category_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('category_id', name='pk_conversion_category'),
        sa.UniqueConstraint('category_name', name='uq_conversion_category_category_name'),
    )

    # 3. conversion_mapping table
    op.create_table(
        'conversion_mapping',
        sa.Column('mapping_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('source_dialect_id', sa.BigInteger(), nullable=False),
        sa.Column('target_dialect_id', sa.BigInteger(), nullable=False),
        sa.Column('category_id', sa.BigInteger(), nullable=False),
        sa.Column('source_value', sa.Text(), nullable=False),
        sa.Column('target_value', sa.Text(), nullable=True),
        sa.Column('match_type', sa.String(length=20), server_default=sa.text("'EXACT'"), nullable=False),
        sa.Column('priority', sa.Integer(), server_default=sa.text('100'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['conversion_category.category_id'], name='fk_conversion_mapping_category_id'),
        sa.ForeignKeyConstraint(['source_dialect_id'], ['rdbms_dialect.dialect_id'], name='fk_conversion_mapping_source_dialect_id'),
        sa.ForeignKeyConstraint(['target_dialect_id'], ['rdbms_dialect.dialect_id'], name='fk_conversion_mapping_target_dialect_id'),
        sa.PrimaryKeyConstraint('mapping_id', name='pk_conversion_mapping'),
        sa.UniqueConstraint('source_dialect_id', 'target_dialect_id', 'category_id', 'source_value', name='uq_conversion_mapping_rule'),
    )
    op.create_index(
        'idx_mapping_lookup',
        'conversion_mapping',
        ['source_dialect_id', 'target_dialect_id', 'category_id', 'is_active', 'priority'],
        unique=False,
    )

    # 4. sp_migration_history table
    op.create_table(
        'sp_migration_history',
        sa.Column('migration_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('source_dialect_id', sa.BigInteger(), nullable=False),
        sa.Column('target_dialect_id', sa.BigInteger(), nullable=False),
        sa.Column('procedure_name', sa.String(length=255), nullable=False),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column('converted_code', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_dialect_id'], ['rdbms_dialect.dialect_id'], name='fk_sp_migration_history_source_dialect_id'),
        sa.ForeignKeyConstraint(['target_dialect_id'], ['rdbms_dialect.dialect_id'], name='fk_sp_migration_history_target_dialect_id'),
        sa.PrimaryKeyConstraint('migration_id', name='pk_sp_migration_history'),
    )


def downgrade() -> None:
    """Downgrade schema: drop tables in reverse order of foreign key dependencies."""
    op.drop_table('sp_migration_history')
    op.drop_index('idx_mapping_lookup', table_name='conversion_mapping')
    op.drop_table('conversion_mapping')
    op.drop_table('conversion_category')
    op.drop_table('rdbms_dialect')
