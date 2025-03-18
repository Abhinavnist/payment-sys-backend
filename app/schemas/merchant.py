from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
import uuid

class BankDetailBase(BaseModel):
    """Base model for bank details"""
    bank_name: str = Field(..., description="Bank name")
    account_name: str = Field(..., description="Account holder name")
    account_number: str = Field(..., description="Bank account number")
    ifsc_code: str = Field(..., description="Bank IFSC code")
    is_active: bool = Field(True, description="Whether this bank detail is active")


class BankDetailCreate(BankDetailBase):
    """Create model for bank details"""
    pass


class BankDetailUpdate(BankDetailBase):
    """Update model for bank details"""
    bank_name: Optional[str] = Field(None, description="Bank name")
    account_name: Optional[str] = Field(None, description="Account holder name")
    account_number: Optional[str] = Field(None, description="Bank account number")
    ifsc_code: Optional[str] = Field(None, description="Bank IFSC code")
    is_active: Optional[bool] = Field(None, description="Whether this bank detail is active")


class BankDetail(BankDetailBase):
    """Response model for bank details"""
    id: uuid.UUID = Field(..., description="Unique ID")
    merchant_id: uuid.UUID = Field(..., description="Merchant ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        orm_mode = True


class UPIDetailBase(BaseModel):
    """Base model for UPI details"""
    upi_id: str = Field(..., description="UPI ID")
    name: str = Field(..., description="UPI display name")
    is_active: bool = Field(True, description="Whether this UPI detail is active")


class UPIDetailCreate(UPIDetailBase):
    """Create model for UPI details"""
    pass


class UPIDetailUpdate(UPIDetailBase):
    """Update model for UPI details"""
    upi_id: Optional[str] = Field(None, description="UPI ID")
    name: Optional[str] = Field(None, description="UPI display name")
    is_active: Optional[bool] = Field(None, description="Whether this UPI detail is active")


class UPIDetail(UPIDetailBase):
    """Response model for UPI details"""
    id: uuid.UUID = Field(..., description="Unique ID")
    merchant_id: uuid.UUID = Field(..., description="Merchant ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        orm_mode = True


class IPWhitelistBase(BaseModel):
    """Base model for IP whitelist"""
    ip_address: str = Field(..., description="IP address")
    description: Optional[str] = Field(None, description="Description")


class IPWhitelistCreate(IPWhitelistBase):
    """Create model for IP whitelist"""
    pass


class IPWhitelist(IPWhitelistBase):
    """Response model for IP whitelist"""
    id: uuid.UUID = Field(..., description="Unique ID")
    merchant_id: uuid.UUID = Field(..., description="Merchant ID")
    created_at: str = Field(..., description="Creation timestamp")

    class Config:
        orm_mode = True


class RateLimitBase(BaseModel):
    """Base model for rate limits"""
    endpoint: str = Field(..., description="API endpoint")
    requests_per_minute: int = Field(..., description="Requests per minute")


class RateLimitCreate(RateLimitBase):
    """Create model for rate limits"""
    pass


class RateLimit(RateLimitBase):
    """Response model for rate limits"""
    id: uuid.UUID = Field(..., description="Unique ID")
    merchant_id: uuid.UUID = Field(..., description="Merchant ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        orm_mode = True


class MerchantBase(BaseModel):
    """Base model for merchants"""
    business_name: str = Field(..., description="Business name")
    business_type: str = Field(..., description="Business type")
    contact_phone: str = Field(..., description="Contact phone number")
    address: Optional[str] = Field(None, description="Business address")
    callback_url: str = Field(..., description="Callback URL for payment notifications")
    is_active: bool = Field(True, description="Whether this merchant is active")
    min_deposit: int = Field(500, description="Minimum deposit amount")
    max_deposit: int = Field(300000, description="Maximum deposit amount")
    min_withdrawal: int = Field(1000, description="Minimum withdrawal amount")
    max_withdrawal: int = Field(1000000, description="Maximum withdrawal amount")


class MerchantCreate(MerchantBase):
    """Create model for merchants"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")
    bank_details: Optional[List[BankDetailCreate]] = Field(None, description="Bank details")
    upi_details: Optional[List[UPIDetailCreate]] = Field(None, description="UPI details")

    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        # Add more password complexity rules as needed
        return v


class MerchantUpdate(BaseModel):
    """Update model for merchants"""
    business_name: Optional[str] = Field(None, description="Business name")
    business_type: Optional[str] = Field(None, description="Business type")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    address: Optional[str] = Field(None, description="Business address")
    callback_url: Optional[str] = Field(None, description="Callback URL for payment notifications")
    is_active: Optional[bool] = Field(None, description="Whether this merchant is active")
    min_deposit: Optional[int] = Field(None, description="Minimum deposit amount")
    max_deposit: Optional[int] = Field(None, description="Maximum deposit amount")
    min_withdrawal: Optional[int] = Field(None, description="Minimum withdrawal amount")
    max_withdrawal: Optional[int] = Field(None, description="Maximum withdrawal amount")
    bank_details: Optional[List[BankDetailUpdate]] = Field(None, description="Bank details")
    upi_details: Optional[List[UPIDetailUpdate]] = Field(None, description="UPI details")


class MerchantResponse(MerchantBase):
    """Response model for merchants"""
    id: uuid.UUID = Field(..., description="Unique ID")
    user_id: uuid.UUID = Field(..., description="User ID")
    api_key: str = Field(..., description="API key")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    bank_details: List[BankDetail] = Field([], description="Bank details")
    upi_details: List[UPIDetail] = Field([], description="UPI details")
    ip_whitelist: List[IPWhitelist] = Field([], description="IP whitelist")
    rate_limits: List[RateLimit] = Field([], description="Rate limits")

    class Config:
        orm_mode = True


class MerchantProfileUpdate(BaseModel):
    """Update model for merchant profile"""
    business_name: Optional[str] = Field(None, description="Business name")
    business_type: Optional[str] = Field(None, description="Business type")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    callback_url: Optional[str] = Field(None, description="Callback URL for payment notifications")


class ChangePasswordRequest(BaseModel):
    """Request model for changing password"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")

    @validator('new_password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        # Add more password complexity rules as needed
        return v

class MerchantBase(BaseModel):
    # ... existing fields
    commission_rate: float = Field(2.5, description="Commission rate (%)")