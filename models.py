from datetime import date
from decimal import Decimal
from typing import Annotated, Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, MetaData, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, WriteOnlyMapped

# Note: Adjust to core.time_utils if that was the correct import path in your project
from core.utils import get_utc_date


_POSTGRES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

_metadata = MetaData(naming_convention=_POSTGRES_NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = _metadata


# Reusable annotated type that maps to Numeric(10, 2) on the DB side.
money = Annotated[
    Decimal,
    mapped_column(Numeric(10, 2), nullable=False, comment="Enforces strict financial decimal precision"),
]


class Store(Base):
    """e.g., MyTek, TunisNet, Scoop"""
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    pricings: WriteOnlyMapped["ProductPricingHistory"] = relationship(
        back_populates="store",
        passive_deletes="all",
    )


class Product(Base):
    """e.g., MacBook Pro M3, iPhone 15 Pro"""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    pricings: WriteOnlyMapped["ProductPricingHistory"] = relationship(
        back_populates="product",
        passive_deletes="all",
    )


class ProductPricingHistory(Base):
    __tablename__ = "product_pricing_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), index=True
    )
    store_internal_id: Mapped[Optional[str]] = mapped_column(String(100))
    price: Mapped[money]
    date_extracted: Mapped[date] = mapped_column(Date, default=get_utc_date)

    product: Mapped["Product"] = relationship(back_populates="pricings")
    store: Mapped["Store"] = relationship(back_populates="pricings")

    __table_args__ = (
        UniqueConstraint("product_id", "store_id", "date_extracted", name="uq_product_store_date"),
        CheckConstraint("price > 0", name="ck_price_must_be_positive"),
    )
