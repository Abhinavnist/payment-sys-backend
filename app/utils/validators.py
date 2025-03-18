import re
from typing import Optional


def validate_upi_id(upi_id: str) -> bool:
    """
    Validate a UPI ID format

    Parameters:
    - upi_id: UPI ID to validate

    Returns:
    - True if valid, False otherwise
    """
    # Basic UPI ID validation pattern
    pattern = r'^[a-zA-Z0-9_.-]+@[a-zA-Z0-9]+$'
    return bool(re.match(pattern, upi_id))


def validate_ifsc_code(ifsc_code: str) -> bool:
    """
    Validate IFSC code format

    Parameters:
    - ifsc_code: IFSC code to validate

    Returns:
    - True if valid, False otherwise
    """
    # IFSC code format: 4 alphabets representing bank, 0 (reserved), 6 alphanumeric for branch
    pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
    return bool(re.match(pattern, ifsc_code))


def validate_account_number(account_number: str) -> bool:
    """
    Validate bank account number format

    Parameters:
    - account_number: Account number to validate

    Returns:
    - True if valid, False otherwise
    """
    # Basic validation: 9-18 digits
    pattern = r'^\d{9,18}$'
    return bool(re.match(pattern, account_number))


def validate_phone_number(phone_number: str) -> bool:
    """
    Validate phone number format

    Parameters:
    - phone_number: Phone number to validate

    Returns:
    - True if valid, False otherwise
    """
    # Indian phone number format: 10 digits optionally prefixed with +91 or 0
    pattern = r'^(?:\+91|0)?[6-9]\d{9}$'
    return bool(re.match(pattern, phone_number))


def validate_utr_number(utr_number: str) -> bool:
    """
    Validate UTR number format

    Parameters:
    - utr_number: UTR number to validate

    Returns:
    - True if valid, False otherwise
    """
    # Handle scientific notation if present
    if 'E+' in utr_number:
        try:
            utr_number = '{:.0f}'.format(float(utr_number))
        except ValueError:
            return False
    # UTR number format: 12-22 alphanumeric characters
    pattern = r'^[A-Za-z0-9]{12,22}$'
    return bool(re.match(pattern, utr_number))


def validate_ip_address(ip_address: str) -> bool:
    """
    Validate IP address format

    Parameters:
    - ip_address: IP address to validate

    Returns:
    - True if valid, False otherwise
    """
    # IPv4 pattern
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

    # IPv6 pattern (simplified)
    ipv6_pattern = r'^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$'

    return bool(re.match(ipv4_pattern, ip_address, re.IGNORECASE)) or bool(
        re.match(ipv6_pattern, ip_address, re.IGNORECASE))


def sanitize_string(value: Optional[str]) -> Optional[str]:
    """
    Sanitize a string by removing special characters and trimming

    Parameters:
    - value: String to sanitize

    Returns:
    - Sanitized string
    """
    if value is None:
        return None

    # Remove leading/trailing whitespace
    value = value.strip()

    # Remove potentially dangerous characters
    value = re.sub(r'[<>&\'"]', '', value)

    return value