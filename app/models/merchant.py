from datetime import datetime
from uuid import UUID
from typing import Optional, List


class BankDetail:
    """Bank detail model representing a merchant's bank account"""

    def __init__(
            self,
            id: UUID,
            merchant_id: UUID,
            bank_name: str,
            account_name: str,
            account_number: str,
            ifsc_code: str,
            is_active: bool = True,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.merchant_id = merchant_id
        self.bank_name = bank_name
        self.account_name = account_name
        self.account_number = account_number
        self.ifsc_code = ifsc_code
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @classmethod
    def from_dict(cls, data: dict):
        """Create a BankDetail instance from a dictionary"""
        return cls(
            id=data.get("id"),
            merchant_id=data.get("merchant_id"),
            bank_name=data.get("bank_name"),
            account_name=data.get("account_name"),
            account_number=data.get("account_number"),
            ifsc_code=data.get("ifsc_code"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def to_dict(self):
        """Convert BankDetail instance to a dictionary"""
        return {
            "id": str(self.id),
            "merchant_id": str(self.merchant_id),
            "bank_name": self.bank_name,
            "account_name": self.account_name,
            "account_number": self.account_number,
            "ifsc_code": self.ifsc_code,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UPIDetail:
    """UPI detail model representing a merchant's UPI account"""

    def __init__(
            self,
            id: UUID,
            merchant_id: UUID,
            upi_id: str,
            name: str,
            is_active: bool = True,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.merchant_id = merchant_id
        self.upi_id = upi_id
        self.name = name
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @classmethod
    def from_dict(cls, data: dict):
        """Create a UPIDetail instance from a dictionary"""
        return cls(
            id=data.get("id"),
            merchant_id=data.get("merchant_id"),
            upi_id=data.get("upi_id"),
            name=data.get("name"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def to_dict(self):
        """Convert UPIDetail instance to a dictionary"""
        return {
            "id": str(self.id),
            "merchant_id": str(self.merchant_id),
            "upi_id": self.upi_id,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class IPWhitelist:
    """IP whitelist model representing a merchant's whitelisted IP"""

    def __init__(
            self,
            id: UUID,
            merchant_id: UUID,
            ip_address: str,
            description: Optional[str] = None,
            created_at: Optional[datetime] = None
    ):
        self.id = id
        self.merchant_id = merchant_id
        self.ip_address = ip_address
        self.description = description
        self.created_at = created_at or datetime.now()

    @classmethod
    def from_dict(cls, data: dict):
        """Create an IPWhitelist instance from a dictionary"""
        return cls(
            id=data.get("id"),
            merchant_id=data.get("merchant_id"),
            ip_address=data.get("ip_address"),
            description=data.get("description"),
            created_at=data.get("created_at")
        )

    def to_dict(self):
        """Convert IPWhitelist instance to a dictionary"""
        return {
            "id": str(self.id),
            "merchant_id": str(self.merchant_id),
            "ip_address": self.ip_address,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Merchant:
    """Merchant model representing a merchant in the system"""

    def __init__(
            self,
            id: UUID,
            user_id: UUID,
            business_name: str,
            business_type: str,
            contact_phone: str,
            address: Optional[str] = None,
            api_key: str = "",
            callback_url: str = "",
            webhook_secret: Optional[str] = None,
            is_active: bool = True,
            min_deposit: int = 500,
            max_deposit: int = 300000,
            min_withdrawal: int = 1000,
            max_withdrawal: int = 1000000,
            created_at: Optional[datetime] = None,
            updated_at: Optional[datetime] = None,
            bank_details: Optional[List[BankDetail]] = None,
            upi_details: Optional[List[UPIDetail]] = None,
            ip_whitelist: Optional[List[IPWhitelist]] = None
    ):
        self.id = id
        self.user_id = user_id
        self.business_name = business_name
        self.business_type = business_type
        self.contact_phone = contact_phone
        self.address = address
        self.api_key = api_key
        self.callback_url = callback_url
        self.webhook_secret = webhook_secret
        self.is_active = is_active
        self.min_deposit = min_deposit
        self.max_deposit = max_deposit
        self.min_withdrawal = min_withdrawal
        self.max_withdrawal = max_withdrawal
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.bank_details = bank_details or []
        self.upi_details = upi_details or []
        self.ip_whitelist = ip_whitelist or []

    @classmethod
    def from_dict(cls, data: dict):
        """Create a Merchant instance from a dictionary"""
        bank_details = []
        if "bank_details" in data and data["bank_details"]:
            bank_details = [BankDetail.from_dict(bd) for bd in data["bank_details"]]

        upi_details = []
        if "upi_details" in data and data["upi_details"]:
            upi_details = [UPIDetail.from_dict(ud) for ud in data["upi_details"]]

        ip_whitelist = []
        if "ip_whitelist" in data and data["ip_whitelist"]:
            ip_whitelist = [IPWhitelist.from_dict(ip) for ip in data["ip_whitelist"]]

        return cls(
            id=data.get("id"),
            user_id=data.get("user_id"),
            business_name=data.get("business_name"),
            business_type=data.get("business_type"),
            contact_phone=data.get("contact_phone"),
            address=data.get("address"),
            api_key=data.get("api_key", ""),
            callback_url=data.get("callback_url", ""),
            webhook_secret=data.get("webhook_secret"),
            is_active=data.get("is_active", True),
            min_deposit=data.get("min_deposit", 500),
            max_deposit=data.get("max_deposit", 300000),
            min_withdrawal=data.get("min_withdrawal", 1000),
            max_withdrawal=data.get("max_withdrawal", 1000000),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            bank_details=bank_details,
            upi_details=upi_details,
            ip_whitelist=ip_whitelist
        )

    def to_dict(self):
        """Convert Merchant instance to a dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "business_name": self.business_name,
            "business_type": self.business_type,
            "contact_phone": self.contact_phone,
            "address": self.address,
            "api_key": self.api_key,
            "callback_url": self.callback_url,
            "webhook_secret": self.webhook_secret,
            "is_active": self.is_active,
            "min_deposit": self.min_deposit,
            "max_deposit": self.max_deposit,
            "min_withdrawal": self.min_withdrawal,
            "max_withdrawal": self.max_withdrawal,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "bank_details": [bd.to_dict() for bd in self.bank_details],
            "upi_details": [ud.to_dict() for ud in self.upi_details],
            "ip_whitelist": [ip.to_dict() for ip in self.ip_whitelist]
        }