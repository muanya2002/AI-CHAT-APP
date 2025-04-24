from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class PaymentStatus(str, Enum):
    CREATED = "created"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class PaymentIntent(BaseModel):
    amount: int  # in cents
    credits: int

class CreditPackage(BaseModel):
    package_id: str  # "basic", "standard", or "premium"

class PaymentResponse(BaseModel):
    id: str
    user_id: str
    amount: int
    credits: int
    status: PaymentStatus
    created_at: datetime
    payment_intent_id: Optional[str] = None
    checkout_session_id: Optional[str] = None
    package_id: Optional[str] = None

class PaymentInDB(BaseModel):
    id: str
    user_id: str
    amount: int
    credits: int
    status: PaymentStatus = PaymentStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    payment_intent_id: Optional[str] = None
    checkout_session_id: Optional[str] = None
    package_id: Optional[str] = None

class TransactionHistory(BaseModel):
    id: str
    amount: float  # in dollars
    credits: int
    status: PaymentStatus
    date: str

class CreditHistory(BaseModel):
    date: datetime
    description: str
    amount: int
    type: str

class CheckoutSessionResponse(BaseModel):
    checkout_url: str