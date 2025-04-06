from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SMSPayload(BaseModel):
    """Schema for SMS data received from SMS forwarder"""
    sender: str = Field(..., description="SMS sender (usually bank number/name)")
    message: str = Field(..., description="SMS message content")
    timestamp: Optional[datetime] = Field(None, description="Time when SMS was received")
    device_id: Optional[str] = Field(None, description="ID of the device that forwarded the SMS")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sender": "SBIINB",
                "message": "Your a/c no. XX1234 is credited with Rs.5000.00 on 27-10-2022 by a/c linked to UPI UTIB0000456789101 (Ref no 123456789012).",
                "timestamp": "2022-10-27T17:10:00.000Z",
                "device_id": "SMS-FORWARDER-01"
            }
        }