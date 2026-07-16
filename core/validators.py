import re
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from pydantic_core import PydanticCustomError

STRIP_MAP = str.maketrans("", "", " \t\n\r\x0b\x0cDTdtNnRrUuSs")
PRICE_REGEX = re.compile(r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)")

def clean_currency(value: Any, handler: Callable[[Any], Any]) -> Decimal:
    """Fast/Slow path architecture for cleaning scraped prices."""
    if isinstance(value, (int, float, Decimal)):
        return handler(value)
    if not isinstance(value, str):
        raise PydanticCustomError('invalid_type', 'Expected string or number')
        
    fast_cleaned = value.translate(STRIP_MAP)
    
    if fast_cleaned:
        if "." in fast_cleaned and "," in fast_cleaned:
            fast_cleaned = fast_cleaned.replace(",", "")
        else:
            fast_cleaned = fast_cleaned.replace(",", ".")
            
        try:
            return handler(fast_cleaned)
        except (ValueError, InvalidOperation):
            pass 
            
    match = PRICE_REGEX.search(value)
    
    if match:
        slow_cleaned = match.group(1)
        if "." in slow_cleaned and "," in slow_cleaned:
            slow_cleaned = slow_cleaned.replace(",", "")
        else:
            slow_cleaned = slow_cleaned.replace(",", ".")
            
        try:
            return handler(slow_cleaned)
        except (ValueError, InvalidOperation):
            pass 
            
    raise PydanticCustomError('decimal_parse_error', f'Unrecoverable price format: {value}')
