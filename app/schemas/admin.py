from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from app.schemas.merchant import MerchantResponse, BankDetail, UPIDetail, IPWhitelist


class UserBase(BaseModel):
    """Base model for users"""
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    is_active: bool = Field(True, description="Whether this user is active")
    is_superuser: bool = Field(False, description="Whether this user is a superuser")


class UserCreate(UserBase):
    """Create model for users"""
    password: str = Field(..., description="Password")

    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdate(BaseModel):
    """Update model for users"""
    email: Optional[EmailStr] = Field(None, description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    is_active: Optional[bool] = Field(None, description="Whether this user is active")
    is_superuser: Optional[bool] = Field(None, description="Whether this user is a superuser")
    password: Optional[str] = Field(None, description="Password")

    @validator('password')
    def password_must_be_strong(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class User(UserBase):
    """Response model for users"""
    id: uuid.UUID = Field(..., description="Unique ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        orm_mode = True


class PendingPayment(BaseModel):
    """Pending payment model for admin dashboard"""
    id: uuid.UUID = Field(..., description="Payment ID")
    merchant_id: uuid.UUID = Field(..., description="Merchant ID")
    business_name: str = Field(..., description="Merchant business name")
    reference: str = Field(..., description="Merchant reference")
    trxn_hash_key: str = Field(..., description="Transaction hash key")
    payment_type: str = Field(..., description="Payment type (DEPOSIT/WITHDRAWAL)")
    payment_method: str = Field(..., description="Payment method (UPI/BANK_TRANSFER)")
    amount: int = Field(..., description="Amount")
    currency: str = Field(..., description="Currency")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    account_name: Optional[str] = Field(None, description="Account name")
    account_number: Optional[str] = Field(None, description="Account number")
    bank: Optional[str] = Field(None, description="Bank name")
    bank_ifsc: Optional[str] = Field(None, description="Bank IFSC code")


class VerifyPaymentRequest(BaseModel):
    """Request model for verifying payment"""
    utr_number: str = Field(..., description="UTR number")
    remarks: Optional[str] = Field(None, description="Remarks")


class DeclinePaymentRequest(BaseModel):
    """Request model for declining payment"""
    remarks: str = Field(..., description="Remarks")


class PaymentVerificationResponse(BaseModel):
    """Response model for payment verification"""
    id: uuid.UUID = Field(..., description="Payment ID")
    reference: str = Field(..., description="Merchant reference")
    status: str = Field(..., description="Status (CONFIRMED/DECLINED)")
    amount: int = Field(..., description="Amount")
    currency: str = Field(..., description="Currency")
    payment_type: str = Field(..., description="Payment type (DEPOSIT/WITHDRAWAL)")
    utr_number: Optional[str] = Field(None, description="UTR number")
    verified_by: uuid.UUID = Field(..., description="User ID who verified the payment")
    remarks: Optional[str] = Field(None, description="Remarks")


class BankStatementUploadRequest(BaseModel):
    """Request model for uploading bank statement"""
    bank_name: str = Field(..., description="Bank name")


class BankStatementResponse(BaseModel):
    """Response model for bank statement upload"""
    message: str = Field(..., description="Success message")
    filename: str = Field(..., description="Filename")
    matched_transactions: int = Field(..., description="Number of matched transactions")
    processed_transactions: int = Field(..., description="Number of processed transactions")


class BankStatementListItem(BaseModel):
    """List item model for bank statements"""
    id: uuid.UUID = Field(..., description="Bank statement ID")
    file_name: str = Field(..., description="Filename")
    processed: bool = Field(..., description="Whether the statement has been processed")
    matched_transactions: int = Field(..., description="Number of matched transactions")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    uploaded_by_name: str = Field(..., description="Name of the user who uploaded the statement")


class DailyChartData(BaseModel):
    """Daily chart data for dashboard"""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    total: int = Field(..., description="Total transactions")
    confirmed: int = Field(..., description="Confirmed transactions")


class MerchantChartData(BaseModel):
    """Merchant chart data for admin dashboard"""
    merchant: str = Field(..., description="Merchant name")
    total: int = Field(..., description="Total transactions")
    confirmed: int = Field(..., description="Confirmed transactions")


class AdminDashboardStats(BaseModel):
    """Admin dashboard statistics"""
    total_merchants: int = Field(..., description="Total number of merchants")
    active_merchants: int = Field(..., description="Number of active merchants")
    total_transactions: int = Field(..., description="Total number of transactions")
    successful_transactions: int = Field(..., description="Number of successful transactions")
    success_rate: float = Field(..., description="Success rate percentage")
    total_deposit_amount: int = Field(..., description="Total deposit amount")
    total_withdrawal_amount: int = Field(..., description="Total withdrawal amount")
    pending_verification: int = Field(..., description="Number of pending verifications")
    days: int = Field(..., description="Number of days in the report")
    daily_chart_data: List[DailyChartData] = Field([], description="Daily chart data")
    merchant_chart_data: List[MerchartChartData] = Field([], description="Merchant chart data")


class AddIPRequest(BaseModel):
    """Request model for adding IP to whitelist"""
    ip_address: str = Field(..., description="IP address")
    description: Optional[str] = Field(None, description="Description")


class IPWhitelistResponse(BaseModel):
    """Response model for IP whitelist"""
    id: uuid.UUID = Field(..., description="IP whitelist ID")
    merchant_id: uuid.UUID = Field(..., description="Merchant ID")
    ip_address: str = Field(..., description="IP address")
    description: Optional[str] = Field(None, description="Description")


class UpdateRateLimitRequest(BaseModel):
    """Request model for updating rate limit"""
    endpoint: str = Field(..., description="API endpoint")
    requests_per_minute: int = Field(..., description="Requests per minute")


class RateLimitResponse(BaseModel):
    """Response model for rate limit"""
    merchant_id: uuid.UUID = Field(..., description="Merchant ID")
    endpoint: str = Field(..., description="API endpoint")
    requests_per_minute: int = Field(..., description="Requests per minute")


class RegenerateAPIKeyResponse(BaseModel):
    """Response model for regenerating API key"""
    id: uuid.UUID = Field(..., description="Merchant ID")
    api_key: str = Field(..., description="API key")