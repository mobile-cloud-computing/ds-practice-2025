from dataclasses import dataclass
from typing import List, Any, Optional


@dataclass
class BillingInfo:
    """Data class for billing information."""

    city: str
    country: str


@dataclass
class CreditCardInfo:
    """Data class for credit card information."""

    number: str
    expiry_date: str


@dataclass
class UserInfo:
    """Data class for user information."""

    user_id: str
    email: str
    ip_address: str


@dataclass
class OrderInfo:
    """Data class for order information."""

    order_id: str
    book_tokens: List[str]
    amount: float
    payment_method: str = "Credit Card"


@dataclass
class ServiceResult:
    """Data class for storing service call results."""

    success: bool = False
    data: Any = None
    error: Optional[str] = None
