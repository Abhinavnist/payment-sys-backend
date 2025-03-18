from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union
import uuid


class PaymentRequest(BaseModel):
    api_key: str = Field(..., description="API Key provided by Rapid IT Solutions")
    service_type: int = Field(1, description="Defaulted by 1")
    currency: str = Field("INR", description="Currency Code (INR)")
    action: str = Field(..., description="DEPOSIT / WITHDRAWAL")
    reference: str = Field(..., description="Merchant's Back End Transaction ID")
    amount: int = Field(..., description="Amount (whole number)")
    account_name: Optional[str] = Field(None, description="Player's account name")
    account_number: Optional[str] = Field(None, description="Player's account number")
    bank: Optional[str] = Field(None, description="Player's preferred bank")
    bank_ifsc: Optional[str] = Field(None, description="Player's bank Ifsc")
    callback_url: str = Field(..., description="Merchant's callback URL")
    ae_type: str = Field("1", description="Defaulted by 1")
    user_data: Optional[Dict[str, Any]] = Field(None, description="Additional user data")

    @validator('currency')
    def currency_must_be_inr(cls, v):
        if v != "INR":
            raise ValueError("Only INR currency is supported")
        return v

    @validator('action')
    def action_must_be_valid(cls, v):
        if v not in ["DEPOSIT", "WITHDRAWAL"]:
            raise ValueError("Action must be DEPOSIT or WITHDRAWAL")
        return v

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class ReceiverUPIInfo(BaseModel):
    upi_id: str
    name: str


class ReceiverBankInfo(BaseModel):
    bank: str
    bank_ifsc: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None


class PaymentResponseData(BaseModel):
    paymentMethod: Optional[str] = None
    receiverInfo: Optional[ReceiverUPIInfo] = None
    receiverBankInfo: Optional[ReceiverBankInfo] = None
    upiLink: Optional[str] = None
    trxnHashKey: str
    amount: str
    requestedDate: str


class PaymentResponse(BaseModel):
    message: str
    status: int
    response: PaymentResponseData


class CheckRequestResponseData(BaseModel):
    transactionId: str
    reference: str
    type: str
    status: str
    remarks: str
    requestedDate: str


class CheckRequestResponse(BaseModel):
    message: str
    status: int
    response: CheckRequestResponseData


class VerifyPaymentRequest(BaseModel):
    payment_id: str = Field(..., description="Payment ID")
    utr_number: str = Field(..., description="UTR number for verification")


class VerifyPaymentResponse(BaseModel):
    message: str
    payment_id: str
    status: str


class CallbackData(BaseModel):
    reference_id: str = Field(..., description="Reference ID of the transaction request")
    status: int = Field(..., description="2: Confirmed, 3: Declined")
    remarks: str = Field(..., description="Remarks upon processed")
    amount: str = Field(..., description="Amount processed")

class FeeInfo(BaseModel):
    """Fee information for payment"""
    commission_rate: float = Field(..., description="Commission rate (%)")
    fee_amount: int = Field(..., description="Fee amount")
    final_amount: int = Field(..., description="Final amount after fee deduction")

# Then add this to your PaymentVerificationResponse class
class PaymentVerificationResponse(BaseModel):
    # ... existing fields
    fee_info: Optional[FeeInfo] = Field(None, description="Fee information")