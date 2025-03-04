import logging
import re
from typing import Dict, Any, List, Optional, Tuple
import uuid

from app.db.connection import execute_query
from app.utils.validators import validate_utr_number

logger = logging.getLogger(__name__)


def verify_payment_with_utr(payment_id: str, utr_number: str, verified_by: str, remarks: Optional[str] = None) -> Dict[
    str, Any]:
    """
    Verify a payment with UTR number

    Parameters:
    - payment_id: Payment ID
    - utr_number: UTR number
    - verified_by: ID of the user who verified the payment
    - remarks: Additional remarks

    Returns:
    - Updated payment data
    """
    try:
        # Validate UTR number format
        if not validate_utr_number(utr_number):
            raise ValueError("Invalid UTR number format")

        # Check if UTR number is already used
        check_query = """
        SELECT 
            id, merchant_id, reference
        FROM 
            payments
        WHERE 
            utr_number = %s AND status = 'CONFIRMED'
        """

        existing_payment = execute_query(check_query, (utr_number,), single=True)

        if existing_payment:
            raise ValueError(f"UTR number already used for payment {existing_payment['reference']}")

        # Update payment status
        update_query = """
        UPDATE payments
        SET 
            status = 'CONFIRMED',
            utr_number = %s,
            verified_by = %s,
            verification_method = 'MANUAL',
            remarks = %s,
            updated_at = NOW()
        WHERE 
            id = %s AND status = 'PENDING'
        RETURNING id, merchant_id, reference, amount, currency, payment_type, status
        """

        payment = execute_query(
            update_query,
            (utr_number, verified_by, remarks, payment_id),
            single=True
        )

        if not payment:
            raise ValueError("Payment not found or already processed")

        return payment

    except Exception as e:
        logger.error(f"Error verifying payment with UTR: {e}")
        raise


def match_utr_from_bank_statement(utr_data: List[Dict[str, Any]], verified_by: str) -> Tuple[int, int]:
    """
    Match UTR numbers from bank statement with pending payments

    Parameters:
    - utr_data: List of UTR data (UTR number and amount)
    - verified_by: ID of the user who uploaded the bank statement

    Returns:
    - Tuple of (matched count, total count)
    """
    matched_count = 0
    total_count = len(utr_data)

    try:
        # Get all pending payments
        query = """
        SELECT 
            id, amount
        FROM 
            payments
        WHERE 
            status = 'PENDING'
            AND payment_type = 'DEPOSIT'
        """

        pending_payments = execute_query(query)

        # Create a lookup dictionary by amount
        payment_lookup = {}
        for payment in pending_payments:
            amount = payment["amount"]
            if amount not in payment_lookup:
                payment_lookup[amount] = []
            payment_lookup[amount].append(payment)

        # Match UTRs with payments
        for utr_item in utr_data:
            utr_number = utr_item["utr_number"]
            amount = utr_item["amount"]

            # Look for matching payment by amount
            if amount in payment_lookup and payment_lookup[amount]:
                payment = payment_lookup[amount].pop(0)

                try:
                    # Verify payment
                    verify_payment_with_utr(
                        payment_id=payment["id"],
                        utr_number=utr_number,
                        verified_by=verified_by,
                        remarks="Auto-verified via bank statement"
                    )

                    matched_count += 1
                except Exception as e:
                    logger.error(f"Error verifying payment {payment['id']} with UTR {utr_number}: {e}")

        return (matched_count, total_count)

    except Exception as e:
        logger.error(f"Error matching UTRs from bank statement: {e}")
        raise


def extract_utr_from_text(text: str) -> Optional[str]:
    """
    Extract UTR number from text

    Parameters:
    - text: Text to extract UTR number from

    Returns:
    - UTR number if found, None otherwise
    """
    # General pattern for UTR numbers
    pattern = r'(?:UTR|Ref\.?|Reference)\s*(?:No\.?|Number)?[:\s]*([A-Za-z0-9]{12,22})(?![0-9\-])'

    match = re.search(pattern, text)

    if match:
        utr_number = match.group(1)

        # Validate UTR number format
        if validate_utr_number(utr_number):
            return utr_number

    return None


def get_payment_by_utr(utr_number: str) -> Optional[Dict[str, Any]]:
    """
    Get payment by UTR number

    Parameters:
    - utr_number: UTR number

    Returns:
    - Payment data if found, None otherwise
    """
    try:
        query = """
        SELECT 
            id, merchant_id, reference, trxn_hash_key, payment_type,
            payment_method, amount, currency, status, utr_number,
            account_name, account_number, bank, bank_ifsc,
            created_at, updated_at
        FROM 
            payments
        WHERE 
            utr_number = %s
        """

        payment = execute_query(query, (utr_number,), single=True)

        return payment

    except Exception as e:
        logger.error(f"Error getting payment by UTR: {e}")
        return None