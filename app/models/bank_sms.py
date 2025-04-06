from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any


class BankSMS:
    """Model representing a bank SMS message"""

    def __init__(
            self,
            id: UUID,
            sender: str,
            message: str,
            extracted_amount: Optional[float] = None,
            extracted_utr: Optional[str] = None,
            identified_bank: Optional[str] = None,
            payment_id: Optional[UUID] = None,
            matched: bool = False,
            verified: bool = False,
            received_at: datetime = None,
            processed_at: Optional[datetime] = None,
            processing_status: str = "PENDING",
            processing_remarks: Optional[str] = None,
            raw_data: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.sender = sender
        self.message = message
        self.extracted_amount = extracted_amount
        self.extracted_utr = extracted_utr
        self.identified_bank = identified_bank
        self.payment_id = payment_id
        self.matched = matched
        self.verified = verified
        self.received_at = received_at or datetime.now()
        self.processed_at = processed_at
        self.processing_status = processing_status
        self.processing_remarks = processing_remarks
        self.raw_data = raw_data

    @classmethod
    def from_dict(cls, data: dict):
        """Create a BankSMS instance from a dictionary"""
        return cls(
            id=data.get("id"),
            sender=data.get("sender"),
            message=data.get("message"),
            extracted_amount=data.get("extracted_amount"),
            extracted_utr=data.get("extracted_utr"),
            identified_bank=data.get("identified_bank"),
            payment_id=data.get("payment_id"),
            matched=data.get("matched", False),
            verified=data.get("verified", False),
            received_at=data.get("received_at"),
            processed_at=data.get("processed_at"),
            processing_status=data.get("processing_status", "PENDING"),
            processing_remarks=data.get("processing_remarks"),
            raw_data=data.get("raw_data")
        )

    def to_dict(self):
        """Convert BankSMS instance to a dictionary"""
        return {
            "id": str(self.id),
            "sender": self.sender,
            "message": self.message,
            "extracted_amount": self.extracted_amount,
            "extracted_utr": self.extracted_utr,
            "identified_bank": self.identified_bank,
            "payment_id": str(self.payment_id) if self.payment_id else None,
            "matched": self.matched,
            "verified": self.verified,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processing_status": self.processing_status,
            "processing_remarks": self.processing_remarks,
            "raw_data": self.raw_data
        }