import uuid
import hashlib
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
import asyncio
import urllib.parse
from app.utils.validators import validate_utr_number
from app.core.config import settings
from app.db.connection import execute_query, execute_transaction
from app.services.webhook_service import send_webhook

logger = logging.getLogger(__name__)


def create_transaction_hash() -> str:
    """Generate a unique transaction hash key."""
    # Create a random UUID and hash it
    random_uuid = str(uuid.uuid4())
    hash_obj = hashlib.sha256(random_uuid.encode())
    # Return first 24 characters of the hash
    return hash_obj.hexdigest()[:24]


def create_payment_request(
        merchant_id: str,
        payment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new payment request

    Parameters:
    - merchant_id: ID of the merchant
    - payment_data: Payment request data

    Returns:
    - Created payment request data
    """
    # Validate amount limits based on payment type
    payment_type = payment_data.get("action")
    amount = payment_data.get("amount")

    # Get merchant's payment limits
    query = """
    SELECT 
        min_deposit, max_deposit, min_withdrawal, max_withdrawal
    FROM 
        merchants
    WHERE 
        id = %s
    """
    limits = execute_query(query, (merchant_id,), single=True)

    # Validate amount limits
    if payment_type == "DEPOSIT":
        if amount < limits["min_deposit"] or amount > limits["max_deposit"]:
            raise ValueError(
                f"Deposit amount must be between {limits['min_deposit']} and {limits['max_deposit']}"
            )
    elif payment_type == "WITHDRAWAL":
        if amount < limits["min_withdrawal"] or amount > limits["max_withdrawal"]:
            raise ValueError(
                f"Withdrawal amount must be between {limits['min_withdrawal']} and {limits['max_withdrawal']}"
            )
    else:
        raise ValueError("Invalid payment type. Must be DEPOSIT or WITHDRAWAL")

    # Generate transaction hash key
    trxn_hash_key = create_transaction_hash()

    # Prepare data for database insertion
    insert_data = {
        "merchant_id": merchant_id,
        "reference": payment_data.get("reference"),
        "trxn_hash_key": trxn_hash_key,
        "payment_type": payment_type,
        "payment_method": "UPI" if payment_data.get("ae_type") == "1" else "BANK_TRANSFER",
        "amount": amount,
        "currency": payment_data.get("currency", "INR"),
        "account_name": payment_data.get("account_name"),
        "account_number": payment_data.get("account_number"),
        "bank": payment_data.get("bank"),
        "bank_ifsc": payment_data.get("bank_ifsc"),
        "user_data": json.dumps(payment_data.get("user_data", {}))
    }

    # Create SQL query for inserting payment
    query = """
    INSERT INTO payments (
        merchant_id, reference, trxn_hash_key, payment_type, payment_method,
        amount, currency, account_name, account_number, bank, bank_ifsc,
        user_data
    ) VALUES (
        %(merchant_id)s, %(reference)s, %(trxn_hash_key)s, %(payment_type)s, %(payment_method)s,
        %(amount)s, %(currency)s, %(account_name)s, %(account_number)s, %(bank)s, %(bank_ifsc)s,
        %(user_data)s
    ) RETURNING id, created_at;
    """

    # Execute query and get the inserted ID and timestamp
    result = execute_query(query, insert_data, single=True)

    # Format response based on payment type
    if payment_type == "DEPOSIT":
        # Get active UPI details for the merchant
        upi_query = """
        SELECT 
            upi_id, name
        FROM 
            merchant_upi_details
        WHERE 
            merchant_id = %s AND is_active = TRUE
        LIMIT 1
        """
        upi_details = execute_query(upi_query, (merchant_id,), single=True)

        if not upi_details:
            raise ValueError("No active UPI payment method available")

        # Generate UPI payment link (frontend can generate QR code from this)
        upi_link = f"upi://pay?pa={urllib.parse.quote(upi_details['upi_id'])}&pn={urllib.parse.quote(upi_details['name'])}&am={amount}&cu=INR&tn={trxn_hash_key}"

        response = {
            "message": "Success",
            "status": 201,
            "response": {
                "paymentMethod": "UPI",
                "receiverInfo": {
                    "upi_id": upi_details["upi_id"],
                    "name": upi_details["name"]
                },
                "upiLink": upi_link,
                "trxnHashKey": trxn_hash_key,
                "amount": str(amount),
                "requestedDate": result["created_at"].isoformat()
            }
        }
    else:  # WITHDRAWAL
        response = {
            "message": "Success",
            "status": 201,
            "response": {
                "receiverBankInfo": {
                    "bank": insert_data["bank"],
                    "bank_ifsc": insert_data["bank_ifsc"],
                    "account_name": insert_data["account_name"],
                    "account_number": insert_data["account_number"],
                },
                "trxnHashKey": trxn_hash_key,
                "amount": str(amount),
                "requestedDate": result["created_at"].isoformat()
            }
        }

    return response


def check_payment_request(trxn_hash_key: str) -> Dict[str, Any]:
    """
    Check the status of a payment request

    Parameters:
    - trxn_hash_key: Transaction hash key

    Returns:
    - Payment request status data
    """
    query = """
    SELECT 
        id as transaction_id, reference, payment_type as type,
        status, remarks, created_at as requested_date
    FROM 
        payments
    WHERE 
        trxn_hash_key = %s
    """

    payment = execute_query(query, (trxn_hash_key,), single=True)

    if not payment:
        raise ValueError("Transaction hash key invalid")

    # Format the response
    response = {
        "message": "Success",
        "status": 200,
        "response": {
            "transactionId": payment["transaction_id"],
            "reference": payment["reference"],
            "type": payment["type"],
            "status": payment["status"],
            "remarks": payment["remarks"] or "",
            "requestedDate": payment["requested_date"].strftime("%Y-%m-%d %H:%M:%S")
        }
    }

    return response


def verify_payment(
        payment_id: str,
        utr_number: str,
        verified_by: str,
        verification_method: str = "MANUAL",
        remarks: str = None
) -> Dict[str, Any]:
    """
    Verify a payment (mark as CONFIRMED)

    Parameters:
    - payment_id: Payment ID
    - utr_number: UTR number
    - verified_by: ID of the user who verified the payment
    - verification_method: How was the payment verified (MANUAL/AUTO)
    - remarks: Additional remarks

    Returns:
    - Updated payment data
    """
    # Start a transaction
    queries = []

    # Update payment query
    update_query = """
    UPDATE payments
    SET 
        status = 'CONFIRMED',
        utr_number = %s,
        verified_by = %s,
        verification_method = %s,
        remarks = %s,
        updated_at = NOW()
    WHERE 
        id = %s AND status = 'PENDING'
    RETURNING id, merchant_id, reference, amount, currency, payment_type, status
    """

    # Add the update query to transaction
    queries.append((update_query, (utr_number, verified_by, verification_method, remarks, payment_id)))

    try:
        # Execute the transaction
        result = execute_query(update_query, (utr_number, verified_by, verification_method, remarks, payment_id),
                               single=True)

        if not result:
            raise ValueError("Payment not found or already processed")

        # Get merchant callback URL
        merchant_query = """
        SELECT 
            callback_url, webhook_secret
        FROM 
            merchants
        WHERE 
            id = %s
        """
        merchant = execute_query(merchant_query, (result["merchant_id"],), single=True)

        # Prepare callback data
        callback_data = {
            "reference_id": result["reference"],
            "status": 2,  # 2: Confirmed
            "remarks": remarks or "Payment processed successfully",
            "amount": str(result["amount"])
        }

        # Send webhook asynchronously
        asyncio.create_task(
            send_webhook(
                merchant["callback_url"],
                callback_data,
                merchant["webhook_secret"]
            )
        )

        # Mark callback as sent
        update_callback_query = """
        UPDATE payments
        SET 
            callback_sent = TRUE,
            callback_attempts = 1
        WHERE 
            id = %s
        """
        execute_query(update_callback_query, (payment_id,), fetch=False)

        return {
            "id": result["id"],
            "reference": result["reference"],
            "status": result["status"],
            "amount": result["amount"],
            "currency": result["currency"],
            "payment_type": result["payment_type"],
            "utr_number": utr_number,
            "verified_by": verified_by
        }

    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        raise


def decline_payment(
        payment_id: str,
        declined_by: str,
        remarks: str
) -> Dict[str, Any]:
    """
    Decline a payment

    Parameters:
    - payment_id: Payment ID
    - declined_by: ID of the user who declined the payment
    - remarks: Reason for declining

    Returns:
    - Updated payment data
    """
    update_query = """
    UPDATE payments
    SET 
        status = 'DECLINED',
        verified_by = %s,
        remarks = %s,
        updated_at = NOW()
    WHERE 
        id = %s AND status = 'PENDING'
    RETURNING id, merchant_id, reference, amount, currency, payment_type, status
    """

    result = execute_query(update_query, (declined_by, remarks, payment_id), single=True)

    if not result:
        raise ValueError("Payment not found or already processed")

    # Get merchant callback URL
    merchant_query = """
    SELECT 
        callback_url, webhook_secret
    FROM 
        merchants
    WHERE 
        id = %s
    """
    merchant = execute_query(merchant_query, (result["merchant_id"],), single=True)

    # Prepare callback data
    callback_data = {
        "reference_id": result["reference"],
        "status": 3,  # 3: Declined
        "remarks": remarks,
        "amount": str(result["amount"])
    }

    # Send webhook asynchronously
    asyncio.create_task(
        send_webhook(
            merchant["callback_url"],
            callback_data,
            merchant["webhook_secret"]
        )
    )

    # Mark callback as sent
    update_callback_query = """
    UPDATE payments
    SET 
        callback_sent = TRUE,
        callback_attempts = 1
    WHERE 
        id = %s
    """
    execute_query(update_callback_query, (payment_id,), fetch=False)

    return {
        "id": result["id"],
        "reference": result["reference"],
        "status": result["status"],
        "amount": result["amount"],
        "currency": result["currency"],
        "payment_type": result["payment_type"],
        "declined_by": declined_by,
        "remarks": remarks
    }


def get_pending_payments(
        merchant_id: Optional[str] = None,
        days: int = 7
) -> List[Dict[str, Any]]:
    """
    Get pending payments

    Parameters:
    - merchant_id: Filter by merchant ID (optional)
    - days: Number of days to look back

    Returns:
    - List of pending payments
    """
    query_params = []

    # Base query
    query = """
    SELECT 
        p.id, p.merchant_id, m.business_name, p.reference, p.trxn_hash_key,
        p.payment_type, p.payment_method, p.amount, p.currency,
        p.account_name, p.account_number, p.bank, p.bank_ifsc,
        p.created_at, p.updated_at
    FROM 
        payments p
    JOIN 
        merchants m ON p.merchant_id = m.id
    WHERE 
        p.status = 'PENDING'
        AND p.created_at >= %s
    """

    # Add days parameter
    query_params.append(datetime.now() - timedelta(days=days))

    # Add merchant filter if provided
    if merchant_id:
        query += " AND p.merchant_id = %s"
        query_params.append(merchant_id)

    # Add order by
    query += " ORDER BY p.created_at DESC"

    # Execute query
    payments = execute_query(query, tuple(query_params))

    return payments


def create_payment_link(
        merchant_id: str,
        reference: str,
        amount: int,
        description: str = None,
        expires_in_hours: int = 24
) -> Dict[str, Any]:
    """
    Create a payment link

    Parameters:
    - merchant_id: Merchant ID
    - reference: Payment reference
    - amount: Payment amount
    - description: Payment description
    - expires_in_hours: Link expiration time in hours

    Returns:
    - Created payment link data
    """
    # Calculate expiration time
    expires_at = datetime.now() + timedelta(hours=expires_in_hours)

    # Create payment link in the database
    query = """
    INSERT INTO payment_links (
        merchant_id, reference, amount, description, status, expires_at
    ) VALUES (
        %s, %s, %s, %s, 'ACTIVE', %s
    ) RETURNING id, reference, amount, status, expires_at
    """

    result = execute_query(
        query,
        (merchant_id, reference, amount, description, expires_at),
        single=True
    )

    # Generate the payment link
    payment_link_id = result["id"]
    payment_link = f"{settings.SERVER_HOST}:{settings.SERVER_PORT}/pay/{payment_link_id}"

    return {
        "id": payment_link_id,
        "reference": reference,
        "amount": amount,
        "currency": "INR",
        "status": "ACTIVE",
        "payment_link": payment_link,
        "expires_at": expires_at.isoformat()
    }


def store_payment_utr(
        payment_id: str,
        utr_number: str,
        submitted_by: str
) -> Dict[str, Any]:
    """
    Store a UTR number for a payment without verifying

    Parameters:
    - payment_id: Payment ID
    - utr_number: UTR number
    - submitted_by: ID of the user who submitted the UTR

    Returns:
    - Updated payment data
    """
    try:
        # Validate UTR number format
        if not validate_utr_number(utr_number):
            raise ValueError("Invalid UTR number format")

        # Store UTR but keep status as PENDING
        update_query = """
        UPDATE payments
        SET 
            utr_number = %s,
            updated_at = NOW()
        WHERE 
            id = %s AND status = 'PENDING'
        RETURNING id, merchant_id, reference, amount, currency, payment_type, status
        """

        payment = execute_query(
            update_query,
            (utr_number, payment_id),
            single=True
        )

        if not payment:
            raise ValueError("Payment not found or already processed")

        return payment

    except Exception as e:
        logger.error(f"Error storing payment UTR: {e}")
        raise