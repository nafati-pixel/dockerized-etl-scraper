from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Text, Numeric, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pydantic import BaseModel, Field, ConfigDict

class Base(DeclarativeBase):
    pass

class Store(Base):

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    pricings: Mapped[List["ProductPricingHistory"]] = relationship(
        back_populates="store", 
        cascade="all, delete-orphan"
    )

class Product(Base):

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    pricings: Mapped[List["ProductPricingHistory"]] = relationship(
        back_populates="product", 
        cascade="all, delete-orphan"
    )

class ProductPricingHistory(Base):

    __tablename__ = "product_pricing_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), 
        index=True
    )
    
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), 
        index=True
    )
    
    store_internal_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), 
        nullable=False
    )
    
    date_extracted: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        index=True
    )

    product: Mapped["Product"] = relationship(back_populates="pricings")
    store: Mapped["Store"] = relationship(back_populates="pricings")

    __table_args__ = (
        UniqueConstraint(
            "product_id", "store_id", "date_extracted", 
            name="uq_product_store_date"
        ),
    )

class ProductSchema(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    price: float
    date_posted: datetime


class ScrapedItem(BaseModel):


    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    sku: str
    price: float = Field(alias="pricings")
    date_posted: str
