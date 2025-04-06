from fastapi import APIRouter, Body, HTTPException, status, Depends, Request
from typing import Dict, Any, Optional
import logging

from app.schemas.sms import SMSPayload
from app.services.sms_service import process_bank_sms
from app.api.v1.dependencies import verify_sms_source

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process-sms")
async def process_sms(
    request: Request,
    sms_data: SMSPayload = Body(...),
    verified: bool = Depends(verify_sms_source)
):
    """
    Process a forwarded bank SMS message, extract transaction details,
    and update payment status if matched with a pending transaction.
    
    The SMS should contain information about the transaction such as:
    - UTR number
    - Amount
    - Transaction type (credit/debit)
    """
    try:
        # Process the SMS and update payment if matched
        result = await process_bank_sms(
            sender=sms_data.sender,
            message=sms_data.message,
            timestamp=sms_data.timestamp
        )
        
        return {
            "status": "success",
            "message": "SMS processed successfully",
            "details": result
        }
        
    except ValueError as e:
        logger.warning(f"SMS processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error processing SMS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process SMS message"
        )