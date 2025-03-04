from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from typing import Dict, Any, Optional, List
import uuid

from app.core.security import get_api_key_merchant
from app.services.payment_service import (
    create_payment_request,
    check_payment_request,
    verify_payment,
    decline_payment,
    create_payment_link
)
from app.schemas.payment import (
    PaymentRequest,
    PaymentResponse,
    CheckRequestResponse,
    VerifyPaymentRequest
)

router = APIRouter()


@router.post("/request", response_model=PaymentResponse)
async def api_create_payment_request(
        request: Request,
        payment_data: PaymentRequest = Body(...),
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Create a new payment request (deposit or withdrawal)
    """
    try:
        # Create payment request
        response = create_payment_request(merchant["id"], payment_data.dict())
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment request creation failed"
        )


@router.post("/check-request", response_model=CheckRequestResponse)
async def api_check_payment_request(
        trxn_hash_key: str = Body(..., embed=True),
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Check status of a payment request
    """
    try:
        # Check payment request
        response = check_payment_request(trxn_hash_key)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment check failed"
        )


@router.post("/verify-payment")
async def api_verify_payment(
        request: VerifyPaymentRequest,
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Verify a payment by submitting the UTR number (user side)
    """
    try:
        # Convert payment_id to UUID if it's a string
        payment_id = (
            uuid.UUID(request.payment_id)
            if isinstance(request.payment_id, str)
            else request.payment_id
        )

        # Verify payment
        result = verify_payment(
            payment_id=str(payment_id),
            utr_number=request.utr_number,
            verified_by=merchant["id"],
            verification_method="USER",
            remarks="Verified by user"
        )

        return {
            "message": "Payment verified successfully",
            "payment_id": str(payment_id),
            "status": "CONFIRMED"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment verification failed"
        )


@router.post("/create-payment-link")
async def api_create_payment_link(
        reference: str = Body(...),
        amount: int = Body(...),
        description: Optional[str] = Body(None),
        expires_in_hours: Optional[int] = Body(24),
        merchant: Dict[str, Any] = Depends(get_api_key_merchant)
):
    """
    Create a payment link for direct customer payment
    """
    try:
        # Create payment link
        result = create_payment_link(
            merchant_id=merchant["id"],
            reference=reference,
            amount=amount,
            description=description,
            expires_in_hours=expires_in_hours
        )

        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment link creation failed"
        )