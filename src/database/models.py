"""SQLAlchemy models for stored-procedure migration metadata."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.connection import Base


class RdbmsDialect(Base):
    """Database dialect definition (e.g., MSSQL, MySQL, PostgreSQL)."""

    __tablename__ = "rdbms_dialect"

    dialect_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    dialect_name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    dialect_code: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa.text("true")
    )

    # Relationships
    source_mappings: Mapped[List["ConversionMapping"]] = relationship(
        "ConversionMapping",
        foreign_keys="[ConversionMapping.source_dialect_id]",
        back_populates="source_dialect",
    )
    target_mappings: Mapped[List["ConversionMapping"]] = relationship(
        "ConversionMapping",
        foreign_keys="[ConversionMapping.target_dialect_id]",
        back_populates="target_dialect",
    )
    source_migrations: Mapped[List["SpMigrationHistory"]] = relationship(
        "SpMigrationHistory",
        foreign_keys="[SpMigrationHistory.source_dialect_id]",
        back_populates="source_dialect",
    )
    target_migrations: Mapped[List["SpMigrationHistory"]] = relationship(
        "SpMigrationHistory",
        foreign_keys="[SpMigrationHistory.target_dialect_id]",
        back_populates="target_dialect",
    )

    def __repr__(self) -> str:
        return (
            f"<RdbmsDialect(id={self.dialect_id}, code='{self.dialect_code}', "
            f"name='{self.dialect_name}')>"
        )


class ConversionCategory(Base):
    """Categories classifying translation rules (DATA_TYPE, FUNCTION, etc.)."""

    __tablename__ = "conversion_category"

    category_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    category_name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    mappings: Mapped[List["ConversionMapping"]] = relationship(
        "ConversionMapping", back_populates="category"
    )

    def __repr__(self) -> str:
        return (
            f"<ConversionCategory(id={self.category_id}, "
            f"name='{self.category_name}')>"
        )


class ConversionMapping(Base):
    """Rule mapping a source dialect construct to a target dialect construct."""

    __tablename__ = "conversion_mapping"

    mapping_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    source_dialect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rdbms_dialect.dialect_id"), nullable=False
    )
    target_dialect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rdbms_dialect.dialect_id"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversion_category.category_id"), nullable=False
    )
    source_value: Mapped[str] = mapped_column(Text, nullable=False)
    target_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    match_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="EXACT",
        server_default=sa.text("'EXACT'"),
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default=sa.text("100"),
    )
    # The database column name is 'metadata'. 'metadata_' is used in Python
    # to avoid shadowing SQLAlchemy DeclarativeBase.metadata.
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=sa.func.now(),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=sa.func.now(),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    __table_args__ = (
        Index(
            "idx_mapping_lookup",
            "source_dialect_id",
            "target_dialect_id",
            "category_id",
            "is_active",
            "priority",
        ),
        UniqueConstraint(
            "source_dialect_id",
            "target_dialect_id",
            "category_id",
            "source_value",
            name="uq_conversion_mapping_rule",
        ),
    )

    # Relationships
    source_dialect: Mapped["RdbmsDialect"] = relationship(
        "RdbmsDialect",
        foreign_keys=[source_dialect_id],
        back_populates="source_mappings",
    )
    target_dialect: Mapped["RdbmsDialect"] = relationship(
        "RdbmsDialect",
        foreign_keys=[target_dialect_id],
        back_populates="target_mappings",
    )
    category: Mapped["ConversionCategory"] = relationship(
        "ConversionCategory", back_populates="mappings"
    )

    def __init__(self, **kwargs: Any) -> None:
        if "metadata" in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<ConversionMapping(id={self.mapping_id}, "
            f"source='{self.source_value}', target='{self.target_value}', "
            f"match_type='{self.match_type}', priority={self.priority})>"
        )


class SpMigrationHistory(Base):
    """Audit log and record of stored procedure migration jobs."""

    __tablename__ = "sp_migration_history"

    migration_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    source_dialect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rdbms_dialect.dialect_id"), nullable=False
    )
    target_dialect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rdbms_dialect.dialect_id"), nullable=False
    )
    procedure_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    converted_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default=sa.text("'PENDING'"),
    )
    issues: Mapped[List[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=sa.func.now(),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=sa.func.now(),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # Relationships
    source_dialect: Mapped["RdbmsDialect"] = relationship(
        "RdbmsDialect",
        foreign_keys=[source_dialect_id],
        back_populates="source_migrations",
    )
    target_dialect: Mapped["RdbmsDialect"] = relationship(
        "RdbmsDialect",
        foreign_keys=[target_dialect_id],
        back_populates="target_migrations",
    )

    def __repr__(self) -> str:
        return (
            f"<SpMigrationHistory(id={self.migration_id}, "
            f"procedure='{self.procedure_name}', status='{self.status}')>"
        )
