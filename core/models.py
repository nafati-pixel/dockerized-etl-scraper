import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Annotated
from sqlalchemy import ForeignKey, String, Text, Numeric, DateTime, UniqueConstraint, MetaData, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, WriteOnlyMapped
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

# =====================================================================
# 1. DATABASE CONFIGURATION & CUSTOM TYPES
# =====================================================================

# [Design Pattern: Deterministic Naming]
# Ensures Alembic migrations are predictable and prevents "Constraint Not Found" crashes.
POSTGRES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
metadata_obj = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)

class Base(DeclarativeBase):
    metadata = metadata_obj

# [Design Principle: DRY (Don't Repeat Yourself) & Centralized Typing]
# Type aliases allow global schema changes (e.g., changing decimal precision) from a single line.
uuid_pk = Annotated[
    uuid.UUID, 
    mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
]
money = Annotated[
    Decimal, 
    mapped_column(Numeric(10, 2), nullable=False, comment="Enforces strict financial decimal precision")
]
db_timestamp = Annotated[
    datetime, 
    mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
]

# =====================================================================
# 2. DEFINITIONS (The Tables)
# =====================================================================

class Store(Base):
    """e.g., MyTek, TunisNet, Scoop"""
    __tablename__ = "stores"

    id: Mapped[uuid_pk]
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # [Design Pattern: Memory Protection via Write-Only Relationships]
    # Prevents OOM (Out Of Memory) crashes by refusing to implicitly load millions of child records.
    pricings: Mapped[WriteOnlyMapped["ProductPricingHistory"]] = relationship(
        back_populates="store", 
        passive_deletes="all" 
    )

class Product(Base):
    """e.g., MacBook Pro M3, iPhone 15 Pro"""
    __tablename__ = "products"

    id: Mapped[uuid_pk]
    sku: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    # [Design Pattern: Memory Protection via Write-Only Relationships]
    pricings: Mapped[WriteOnlyMapped["ProductPricingHistory"]] = relationship(
        back_populates="product", 
        passive_deletes="all"
    )

class ProductPricingHistory(Base):
    """The append-only historical price ledger table"""
    __tablename__ = "product_pricing_history"

    id: Mapped[uuid_pk]
    
    # [Design Pattern: Blast Radius Containment]
    # "RESTRICT" acts as an immutability lock. It physically blocks the database from 
    # cascade-deleting historical pricing ledgers if a parent Store or Product is removed.
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), index=True
    )
    
    store_internal_id: Mapped[Optional[str]] = mapped_column(String(100))
    price: Mapped[money]
    date_extracted: Mapped[db_timestamp]

    product: Mapped["Product"] = relationship(back_populates="pricings")
    store: Mapped["Store"] = relationship(back_populates="pricings")

    __table_args__ = (
        # [Design Pattern: Idempotency Barrier]
        # Guarantees that if the bot crashes and retries, duplicate data is rejected by the database.
        UniqueConstraint("product_id", "store_id", "date_extracted", name="uq_product_store_date"),
        
        # [Design Pattern: Defense in Depth]
        # Hardware-level constraint ensuring corrupt/negative calculations from the Python layer 
        # can never poison the permanent dataset.
        CheckConstraint("price > 0", name="ck_price_must_be_positive"),
    )
