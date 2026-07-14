from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Callable, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, WrapValidator
from pydantic_core import PydanticCustomError

# Optimization: Bypasses the regex engine. Uses C-level string translation
# to strip spaces and currency symbols instantly with zero memory allocation.
STRIP_MAP = str.maketrans("", "", " \t\n\r\x0b\x0cDTdtNnRrUuSs")


def _fast_currency_cleaner(value: Any, handler: Callable[[Any], Any]) -> Decimal:
    """
    Pre-cleans scraped string prices before passing them to Pydantic's Rust core.
    """
    if isinstance(value, (int, float, Decimal)):
        return handler(value)
    if not isinstance(value, str):
        raise PydanticCustomError('invalid_type', 'Expected string or number')
        
    cleaned = value.translate(STRIP_MAP)
    if not cleaned:
        raise PydanticCustomError('empty_value', 'No digits found')
        
    cleaned = cleaned.replace(",", "") if "." in cleaned and "," in cleaned else cleaned.replace(",", ".")
    
    try:
        return handler(cleaned)
    except (ValueError, InvalidOperation):
        raise PydanticCustomError('decimal_parse_error', f'Invalid format: {value}')


# Strict Rule: Reusable semantic type enforcing SQLAlchemy's Numeric(10,2) limits
StrictDinar = Annotated[
    Decimal,
    WrapValidator(_fast_currency_cleaner),
    Field(strict=True, ge=Decimal("0.00"), decimal_places=2)
]


class ScrapedItem(BaseModel):
    """
    Validates raw, chaotic data directly from the scraper pipeline.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,  # Optimization: Auto-cleans HTML whitespace
        frozen=True,                # Optimization: Thread-safe, hashable, faster lookups
        extra="forbid"              # Strict Rule: Hard crash on rogue/injected JSON fields
    )

    store_internal_id: str = Field(alias="id", max_length=100)
    name: str = Field(..., min_length=2)
    sku: Optional[str] = Field(default=None, max_length=100)
    
    price: StrictDinar = Field(alias="pricings")
    
    date_extracted: datetime = Field(
        alias="date_posted", 
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ProductSchema(BaseModel):
    """
    Maps perfectly back to the SQLAlchemy ORM objects for API responses.
    """
    model_config = ConfigDict(
        from_attributes=True,  # Strict Rule: Enables reading from SQLAlchemy models
        frozen=True            # Optimization: Read-only memory efficiency
    )

    id: UUID                   # Strict Rule: Maps to the database UUID constraint
    name: str
    sku: Optional[str] = None
    price: Decimal
    date_extracted: datetime = Field(alias="date_posted")
