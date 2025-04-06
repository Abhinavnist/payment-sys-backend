import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from app.db.connection import execute_query
from app.services.payment_service import verify_payment
from app.utils.validators import validate_utr_number

logger = logging.getLogger(__name__)

# Bank SMS patterns for different banks
BANK_PATTERNS = {
    # SBI pattern
    "SBI": {
        "credit": r"(?:.*credited with Rs\.|.*credited by Rs\.|.*deposited in your account)[\s]*([0-9,]+\.[0-9]+).*(?:UPI|UPI Ref no|Ref no)[:\s]*([A-Za-z0-9]{10,22})",
        "banks": ["SBIINB", "SBIATM", "SBI", "STBANKNG"],
    },
    # HDFC pattern
    "HDFC": {
        "credit": r"(?:.*credited to your A/c|.*Money Received)[\s]*(?:Rs\.|INR|Rs)[\s]*([0-9,]+\.[0-9]+).*(?:UPI Ref|Ref)[:\s]*([A-Za-z0-9]{10,22})",
        "banks": ["HDFCBK", "HDFC", "HDFCBANK"],
    },
    # ICICI pattern
    "ICICI": {
        "credit": r"(?:.*credited with INR|.*credited with Rs.)[\s]*([0-9,]+\.[0-9]+).*(?:UPI|UPI REF|REF)[:\s]*([A-Za-z0-9]{10,22})",
        "banks": ["ICICIB", "ICICI", "ICICIBANK"],
    },
    # Axis pattern
    "AXIS": {
        "credit": r"(?:.*credited with INR|.*credited by INR|.*Money received)[\s]*([0-9,]+\.[0-9]+).*(?:UPI Ref|UPI-Ref|Ref)[:\s]*([A-Za-z0-9]{10,22})",
        "banks": ["AXIS", "AXISBANK", "AxisBk"],
    },
    # Default pattern (generic attempt)
    "DEFAULT": {
        "credit": r"(?:.*credited|.*deposited|.*received)[\s]*(?:Rs|Rs\.|INR|Amount)?[\s]*([0-9,]+\.[0-9]+).*(?:UPI|UPI Ref|Ref|Reference|UTR)[:\s]*[\s]*([A-Za-z0-9]{10,22})",
        "banks": [],
    },
}

async def process_bank_sms(sender: str, message: str, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Process a bank SMS message, extract transaction details, and match with pending transactions
    
    Parameters:
    - sender: SMS sender (bank identification)
    - message: SMS content
    - timestamp: When SMS was received
    
    Returns:
    - Processing result details
    """
    # Standardize the message (remove extra spaces, newlines)
    message = re.sub(r'\s+', ' ', message).strip()
    
    # Try to identify the bank and extract transaction details
    bank_name, amount, utr = extract_transaction_details(sender, message)
    
    if not utr or not amount:
        logger.warning(f"Failed to extract transaction details from SMS: {message}")
        return {
            "success": False,
            "reason": "Could not extract transaction details",
            "message": message
        }

    # Convert amount string to float (remove commas)
    try:
        amount_value = float(amount.replace(',', ''))
        # Convert to integer (assuming the amount is stored as integer in database, e.g. 5000.00 -> 5000)
        amount_int = int(amount_value)
    except ValueError:
        logger.warning(f"Invalid amount format: {amount}")
        return {
            "success": False,
            "reason": f"Invalid amount format: {amount}",
            "utr": utr,
            "message": message
        }
    
    # Find matching pending transactions by amount
    matching_transactions = find_matching_transactions(amount_int)
    
    if not matching_transactions:
        logger.warning(f"No matching pending transactions found for amount: {amount_int}, UTR: {utr}")
        return {
            "success": False,
            "reason": "No matching transactions found",
            "amount": amount_int,
            "utr": utr
        }

    # Get the first matching transaction
    # In a production system, you might want a more sophisticated matching algorithm
    # or queue these for manual review if there are multiple matches
    transaction = matching_transactions[0]
    
    # Verify the payment
    try:
        payment_id = transaction["id"]
        # Use 'SYSTEM' as verifier or create a dedicated system user ID
        system_user_id = "00000000-0000-0000-0000-000000000000"
        
        # Verify the payment with the extracted UTR
        verify_result = verify_payment(
            payment_id=str(payment_id),
            utr_number=utr,
            verified_by=system_user_id,
            verification_method="SMS",
            remarks=f"Auto-verified via SMS from {bank_name}. Message: {message[:100]}..."
        )
        
        logger.info(f"Successfully verified payment {payment_id} with UTR {utr} from SMS")
        
        return {
            "success": True,
            "payment_id": str(payment_id),
            "merchant_id": str(transaction["merchant_id"]),
            "amount": amount_int,
            "utr": utr,
            "bank": bank_name,
            "status": "CONFIRMED"
        }
        
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return {
            "success": False,
            "reason": f"Verification error: {str(e)}",
            "payment_id": str(transaction["id"]),
            "amount": amount_int,
            "utr": utr
        }


def extract_transaction_details(sender: str, message: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Extract bank name, transaction amount and UTR from the SMS message
    
    Parameters:
    - sender: SMS sender
    - message: SMS message content
    
    Returns:
    - Tuple of (bank_name, amount, utr)
    """
    # Standardize sender
    sender = sender.upper().strip()
    
    # Try to identify the bank
    identified_bank = "DEFAULT"
    for bank, data in BANK_PATTERNS.items():
        if any(bank_code in sender for bank_code in data["banks"]):
            identified_bank = bank
            break
            
    # Get the appropriate regex pattern
    pattern = BANK_PATTERNS[identified_bank]["credit"]
    
    # Try to match the pattern
    match = re.search(pattern, message)
    
    if match:
        amount = match.group(1)
        utr = match.group(2)
        
        # Validate UTR
        if not validate_utr_number(utr):
            logger.warning(f"Invalid UTR format: {utr}")
            utr = None
            
        return identified_bank, amount, utr
    
    # If no match with specific bank pattern, try the default pattern
    if identified_bank != "DEFAULT":
        default_match = re.search(BANK_PATTERNS["DEFAULT"]["credit"], message)
        if default_match:
            amount = default_match.group(1)
            utr = default_match.group(2)
            
            # Validate UTR
            if not validate_utr_number(utr):
                logger.warning(f"Invalid UTR format: {utr}")
                utr = None
                
            return identified_bank, amount, utr
    
    # If still no match, try to find any amount and UTR-like string
    amount_match = re.search(r'(?:Rs\.?|INR)[\s]*([0-9,]+\.[0-9]+)', message)
    utr_match = re.search(r'(?:UPI Ref|UPI|Ref|Reference|UTR)[:\s]*[\s]*([A-Za-z0-9]{10,22})', message)
    
    amount = amount_match.group(1) if amount_match else None
    utr = utr_match.group(1) if utr_match else None
    
    # Validate UTR if found
    if utr and not validate_utr_number(utr):
        logger.warning(f"Invalid UTR format: {utr}")
        utr = None
    
    return identified_bank, amount, utr


def find_matching_transactions(amount: int) -> List[Dict[str, Any]]:
    """
    Find pending transactions matching the given amount
    
    Parameters:
    - amount: Transaction amount
    
    Returns:
    - List of matching transactions
    """
    query = """
    SELECT 
        id, merchant_id, reference, trxn_hash_key, payment_type, 
        payment_method, amount, status
    FROM 
        payments
    WHERE 
        status = 'PENDING' 
        AND payment_type = 'DEPOSIT'
        AND amount = %s
    ORDER BY
        created_at ASC
    """
    
    matching_transactions = execute_query(query, (amount,))
    return matching_transactions