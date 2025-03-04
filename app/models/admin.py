from datetime import datetime
from uuid import UUID
from typing import Optional, List

from app.models.user import User
from app.models.merchant import Merchant
from app.models.payment import Payment, BankStatement


class AdminDashboardStats:
    """Admin dashboard statistics model"""

    def __init__(
            self,
            total_merchants: int,
            active_merchants: int,
            total_transactions: int,
            successful_transactions: int,
            success_rate: float,
            total_deposit_amount: int,
            total_withdrawal_amount: int,
            pending_verification: int,
            days: int,
            daily_chart_data: List[dict] = None,
            merchant_chart_data: List[dict] = None
    ):
        self.total_merchants = total_merchants
        self.active_merchants = active_merchants
        self.total_transactions = total_transactions
        self.successful_transactions = successful_transactions
        self.success_rate = success_rate
        self.total_deposit_amount = total_deposit_amount
        self.total_withdrawal_amount = total_withdrawal_amount
        self.pending_verification = pending_verification
        self.days = days
        self.daily_chart_data = daily_chart_data or []
        self.merchant_chart_data = merchant_chart_data or []

    @classmethod
    def from_dict(cls, data: dict):
        """Create an AdminDashboardStats instance from a dictionary"""
        return cls(
            total_merchants=data.get("total_merchants", 0),
            active_merchants=data.get("active_merchants", 0),
            total_transactions=data.get("total_transactions", 0),
            successful_transactions=data.get("successful_transactions", 0),
            success_rate=data.get("success_rate", 0.0),
            total_deposit_amount=data.get("total_deposit_amount", 0),
            total_withdrawal_amount=data.get("total_withdrawal_amount", 0),
            pending_verification=data.get("pending_verification", 0),
            days=data.get("days", 30),
            daily_chart_data=data.get("daily_chart_data", []),
            merchant_chart_data=data.get("merchant_chart_data", [])
        )

    def to_dict(self):
        """Convert AdminDashboardStats instance to a dictionary"""
        return {
            "total_merchants": self.total_merchants,
            "active_merchants": self.active_merchants,
            "total_transactions": self.total_transactions,
            "successful_transactions": self.successful_transactions,
            "success_rate": self.success_rate,
            "total_deposit_amount": self.total_deposit_amount,
            "total_withdrawal_amount": self.total_withdrawal_amount,
            "pending_verification": self.pending_verification,
            "days": self.days,
            "daily_chart_data": self.daily_chart_data,
            "merchant_chart_data": self.merchant_chart_data
        }


class MerchantDashboardStats:
    """Merchant dashboard statistics model"""

    def __init__(
            self,
            total_transactions: int,
            successful_transactions: int,
            success_rate: float,
            total_deposit_amount: int,
            total_withdrawal_amount: int,
            pending_verification: int,
            days: int,
            daily_chart_data: List[dict] = None
    ):
        self.total_transactions = total_transactions
        self.successful_transactions = successful_transactions
        self.success_rate = success_rate
        self.total_deposit_amount = total_deposit_amount
        self.total_withdrawal_amount = total_withdrawal_amount
        self.pending_verification = pending_verification
        self.days = days
        self.daily_chart_data = daily_chart_data or []

    @classmethod
    def from_dict(cls, data: dict):
        """Create a MerchantDashboardStats instance from a dictionary"""
        return cls(
            total_transactions=data.get("total_transactions", 0),
            successful_transactions=data.get("successful_transactions", 0),
            success_rate=data.get("success_rate", 0.0),
            total_deposit_amount=data.get("total_deposit_amount", 0),
            total_withdrawal_amount=data.get("total_withdrawal_amount", 0),
            pending_verification=data.get("pending_verification", 0),
            days=data.get("days", 30),
            daily_chart_data=data.get("daily_chart_data", [])
        )

    def to_dict(self):
        """Convert MerchantDashboardStats instance to a dictionary"""
        return {
            "total_transactions": self.total_transactions,
            "successful_transactions": self.successful_transactions,
            "success_rate": self.success_rate,
            "total_deposit_amount": self.total_deposit_amount,
            "total_withdrawal_amount": self.total_withdrawal_amount,
            "pending_verification": self.pending_verification,
            "days": self.days,
            "daily_chart_data": self.daily_chart_data
        }