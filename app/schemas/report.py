from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

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
    merchant_chart_data: List[MerchantChartData] = Field([], description="Merchant chart data")


class MerchantDashboardStats(BaseModel):
    """Merchant dashboard statistics"""
    total_transactions: int = Field(..., description="Total number of transactions")
    successful_transactions: int = Field(..., description="Number of successful transactions")
    success_rate: float = Field(..., description="Success rate percentage")
    total_deposit_amount: int = Field(..., description="Total deposit amount")
    total_withdrawal_amount: int = Field(..., description="Total withdrawal amount")
    pending_verification: int = Field(..., description="Number of pending verifications")
    days: int = Field(..., description="Number of days in the report")
    daily_chart_data: List[DailyChartData] = Field([], description="Daily chart data")


class PaymentResponse(BaseModel):
    """Payment response for reports"""
    id: str = Field(..., description="Payment ID")
    reference: str = Field(..., description="Merchant reference")
    trxn_hash_key: str = Field(..., description="Transaction hash key")
    payment_type: str = Field(..., description="Payment type (DEPOSIT/WITHDRAWAL)")
    payment_method: str = Field(..., description="Payment method (UPI/BANK_TRANSFER)")
    amount: int = Field(..., description="Amount")
    currency: str = Field(..., description="Currency")
    status: str = Field(..., description="Status (PENDING/CONFIRMED/DECLINED)")
    utr_number: Optional[str] = Field(None, description="UTR number")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PaginatedPaymentResponse(BaseModel):
    """Paginated payment response for reports"""
    items: List[PaymentResponse] = Field(..., description="List of payments")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class BankStatementResponse(BaseModel):
    """Bank statement response"""
    id: str = Field(..., description="Bank statement ID")
    file_name: str = Field(..., description="File name")
    processed: bool = Field(..., description="Whether the statement has been processed")
    matched_transactions: int = Field(..., description="Number of matched transactions")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    uploaded_by_name: str = Field(..., description="Name of the uploader")


class CSVExportData(BaseModel):
    """CSV export data"""
    headers: List[str] = Field(..., description="CSV headers")
    rows: List[List[Any]] = Field(..., description="CSV rows")