import logging
from typing import Dict, Any, List, Optional, Tuple
import uuid

from app.core.security import get_password_hash, generate_api_key
from app.db.connection import execute_query, execute_transaction

logger = logging.getLogger(__name__)


def get_merchants(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all merchants

    Parameters:
    - skip: Number of records to skip
    - limit: Maximum number of records to return

    Returns:
    - List of merchants
    """
    query = """
    SELECT 
        m.id, m.business_name, m.business_type, m.contact_phone,
        m.api_key, m.is_active, m.callback_url,
        m.min_deposit, m.max_deposit, m.min_withdrawal, m.max_withdrawal,
        m.created_at, m.updated_at,
        u.id as user_id, u.email, u.full_name
    FROM 
        merchants m
    JOIN 
        users u ON m.user_id = u.id
    ORDER BY 
        m.created_at DESC
    LIMIT %s OFFSET %s
    """

    merchants = execute_query(query, (limit, skip))

    # Format response
    result = []
    for merchant in merchants:
        result.append({
            "id": merchant["id"],
            "business_name": merchant["business_name"],
            "business_type": merchant["business_type"],
            "contact_phone": merchant["contact_phone"],
            "api_key": merchant["api_key"],
            "is_active": merchant["is_active"],
            "callback_url": merchant["callback_url"],
            "min_deposit": merchant["min_deposit"],
            "max_deposit": merchant["max_deposit"],
            "min_withdrawal": merchant["min_withdrawal"],
            "max_withdrawal": merchant["max_withdrawal"],
            "created_at": merchant["created_at"],
            "updated_at": merchant["updated_at"],
            "user": {
                "id": merchant["user_id"],
                "email": merchant["email"],
                "full_name": merchant["full_name"]
            }
        })

    return result


def get_merchant_details(merchant_id: str) -> Optional[Dict[str, Any]]:
    """
    Get merchant details

    Parameters:
    - merchant_id: Merchant ID

    Returns:
    - Merchant details
    """
    # Get merchant query]
    query = """
    SELECT 
        m.id, m.business_name, m.business_type, m.contact_phone,
        m.address, m.api_key, m.is_active, m.callback_url, m.commission_rate,
        m.min_deposit, m.max_deposit, m.min_withdrawal, m.max_withdrawal,
        m.created_at, m.updated_at,
        u.id as user_id, u.email, u.full_name
    FROM 
        merchants m
    JOIN 
        users u ON m.user_id = u.id
    WHERE 
        m.id = %s
    """

    merchant = execute_query(query, (merchant_id,), single=True)

    if not merchant:
        return None

    # Get bank details
    bank_query = """
    SELECT 
        id, bank_name, account_name, account_number, ifsc_code, is_active
    FROM 
        merchant_bank_details
    WHERE 
        merchant_id = %s
    """

    bank_details = execute_query(bank_query, (merchant_id,))

    # Get UPI details
    upi_query = """
    SELECT 
        id, upi_id, name, is_active
    FROM 
        merchant_upi_details
    WHERE 
        merchant_id = %s
    """

    upi_details = execute_query(upi_query, (merchant_id,))

    # Get IP whitelist
    ip_query = """
    SELECT 
        id, ip_address, description
    FROM 
        ip_whitelist
    WHERE 
        merchant_id = %s
    """

    ip_whitelist = execute_query(ip_query, (merchant_id,))

    # Get rate limits
    rate_limit_query = """
    SELECT 
        id, endpoint, requests_per_minute
    FROM 
        rate_limits
    WHERE 
        merchant_id = %s
    """

    # rate_limits = execute_query(rate_limit_query, (merchant_id,))

    # Format response
    result = {
        "id": merchant["id"],
        "business_name": merchant["business_name"],
        "business_type": merchant["business_type"],
        "contact_phone": merchant["contact_phone"],
        "address": merchant["address"],
        "api_key": merchant["api_key"],
        "is_active": merchant["is_active"],
        "callback_url": merchant["callback_url"],
        "min_deposit": merchant["min_deposit"],
        "max_deposit": merchant["max_deposit"],
        "min_withdrawal": merchant["min_withdrawal"],
        "max_withdrawal": merchant["max_withdrawal"],
        "created_at": merchant["created_at"],
        "updated_at": merchant["updated_at"],
        "user": {
            "id": merchant["user_id"],
            "email": merchant["email"],
            "full_name": merchant["full_name"]
        },
        "bank_details": bank_details,
        "upi_details": upi_details,
        "commission_rate": merchant["commission_rate"] if "commission_rate" in merchant else 0,
        "ip_whitelist": ip_whitelist
        # "rate_limits": rate_limits
    }

    return result


def create_merchant(merchant_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new merchant

    Parameters:
    - merchant_data: Merchant data

    Returns:
    - Created merchant
    """
    # Start a transaction
    queries = []

    # Create user
    email = merchant_data.get("email")
    password = merchant_data.get("password")
    full_name = merchant_data.get("business_name")

    if not email or not password:
        raise ValueError("Email and password are required")

    # Check if email already exists
    check_email_query = """
    SELECT id FROM users WHERE email = %s
    """

    email_exists = execute_query(check_email_query, (email,), single=True)

    if email_exists:
        raise ValueError("Email already exists")

    # Create user query
    hashed_password = get_password_hash(password)

    create_user_query = """
    INSERT INTO users (
        email, hashed_password, full_name, is_active, is_superuser
    ) VALUES (
        %s, %s, %s, TRUE, FALSE
    ) RETURNING id
    """

    create_user_params = (email, hashed_password, full_name)

    # Add to transaction
    queries.append((create_user_query, create_user_params))

    # Generate API key
    api_key = generate_api_key()

    # Create merchant query
    create_merchant_query = """
    INSERT INTO merchants (
        user_id, business_name, business_type, contact_phone, address,
        api_key, callback_url, is_active, min_deposit, max_deposit,
        min_withdrawal, max_withdrawal
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s
    ) RETURNING id
    """

    create_merchant_params = (
        "placeholder_user_id",  # Will be replaced with actual user ID
        merchant_data.get("business_name"),
        merchant_data.get("business_type"),
        merchant_data.get("contact_phone"),
        merchant_data.get("address"),
        api_key,
        merchant_data.get("callback_url"),
        merchant_data.get("min_deposit", 500),
        merchant_data.get("max_deposit", 300000),
        merchant_data.get("min_withdrawal", 1000),
        merchant_data.get("max_withdrawal", 1000000)
    )

    # Add bank details if provided
    bank_details = merchant_data.get("bank_details", [])
    if isinstance(bank_details, dict):
        bank_details = [bank_details]

    bank_queries = []
    for bank in bank_details:
        bank_query = """
        INSERT INTO merchant_bank_details (
            merchant_id, bank_name, account_name, account_number, ifsc_code, is_active
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        )
        """

        bank_params = (
            "placeholder_merchant_id",  # Will be replaced with actual merchant ID
            bank.get("bank_name"),
            bank.get("account_name"),
            bank.get("account_number"),
            bank.get("ifsc_code"),
            bank.get("is_active", True)
        )

        bank_queries.append((bank_query, bank_params))

    # Add UPI details if provided
    upi_details = merchant_data.get("upi_details", [])
    if isinstance(upi_details, dict):
        upi_details = [upi_details]

    upi_queries = []
    for upi in upi_details:
        upi_query = """
        INSERT INTO merchant_upi_details (
            merchant_id, upi_id, name, is_active
        ) VALUES (
            %s, %s, %s, %s
        )
        """

        upi_params = (
            "placeholder_merchant_id",  # Will be replaced with actual merchant ID
            upi.get("upi_id"),
            upi.get("name"),
            upi.get("is_active", True)
        )

        upi_queries.append((upi_query, upi_params))

    # Execute transaction
    try:
        # Create user
        user_result = execute_query(create_user_query, create_user_params, single=True)
        user_id = user_result["id"]

        # Update merchant params with user ID
        create_merchant_params = (user_id,) + create_merchant_params[1:]

        # Create merchant
        merchant_result = execute_query(create_merchant_query, create_merchant_params, single=True)
        merchant_id = merchant_result["id"]

        # Add bank details
        for i, (bank_query, bank_params) in enumerate(bank_queries):
            bank_params = (merchant_id,) + bank_params[1:]
            execute_query(bank_query, bank_params, fetch=False)

        # Add UPI details
        for i, (upi_query, upi_params) in enumerate(upi_queries):
            upi_params = (merchant_id,) + upi_params[1:]
            execute_query(upi_query, upi_params, fetch=False)

        # Get created merchant
        return get_merchant_details(merchant_id)

    except Exception as e:
        logger.error(f"Error creating merchant: {e}")
        raise


def update_merchant(merchant_id: str, merchant_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a merchant

    Parameters:
    - merchant_id: Merchant ID
    - merchant_data: Merchant data

    Returns:
    - Updated merchant
    """
    # Build update fields
    fields = []
    params = []

    if "business_name" in merchant_data:
        fields.append("business_name = %s")
        params.append(merchant_data["business_name"])

    if "business_type" in merchant_data:
        fields.append("business_type = %s")
        params.append(merchant_data["business_type"])

    if "contact_phone" in merchant_data:
        fields.append("contact_phone = %s")
        params.append(merchant_data["contact_phone"])

    if "address" in merchant_data:
        fields.append("address = %s")
        params.append(merchant_data["address"])

    if "callback_url" in merchant_data:
        fields.append("callback_url = %s")
        params.append(merchant_data["callback_url"])

    if "is_active" in merchant_data:
        fields.append("is_active = %s")
        params.append(merchant_data["is_active"])

    if "min_deposit" in merchant_data:
        fields.append("min_deposit = %s")
        params.append(merchant_data["min_deposit"])

    if "max_deposit" in merchant_data:
        fields.append("max_deposit = %s")
        params.append(merchant_data["max_deposit"])

    if "min_withdrawal" in merchant_data:
        fields.append("min_withdrawal = %s")
        params.append(merchant_data["min_withdrawal"])

    if "max_withdrawal" in merchant_data:
        fields.append("max_withdrawal = %s")
        params.append(merchant_data["max_withdrawal"])

    # If no fields to update, return current merchant
    if not fields:
        return get_merchant_details(merchant_id)

    # Build update query
    update_query = f"""
    UPDATE merchants
    SET {", ".join(fields)}
    WHERE id = %s
    """

    params.append(merchant_id)

    # Execute update
    execute_query(update_query, tuple(params), fetch=False)

    # Update bank details if provided
    bank_details = merchant_data.get("bank_details")
    if bank_details:
        # First, deactivate all existing bank details
        deactivate_query = """
        UPDATE merchant_bank_details
        SET is_active = FALSE
        WHERE merchant_id = %s
        """

        execute_query(deactivate_query, (merchant_id,), fetch=False)

        # Then, upsert new bank details
        if isinstance(bank_details, dict):
            bank_details = [bank_details]

        for bank in bank_details:
            if "id" in bank:
                # Update existing bank detail
                update_bank_query = """
                UPDATE merchant_bank_details
                SET 
                    bank_name = %s,
                    account_name = %s,
                    account_number = %s,
                    ifsc_code = %s,
                    is_active = %s
                WHERE 
                    id = %s AND merchant_id = %s
                """

                update_bank_params = (
                    bank.get("bank_name"),
                    bank.get("account_name"),
                    bank.get("account_number"),
                    bank.get("ifsc_code"),
                    bank.get("is_active", True),
                    bank["id"],
                    merchant_id
                )

                execute_query(update_bank_query, update_bank_params, fetch=False)
            else:
                # Insert new bank detail
                insert_bank_query = """
                INSERT INTO merchant_bank_details (
                    merchant_id, bank_name, account_name, account_number, ifsc_code, is_active
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
                """

                insert_bank_params = (
                    merchant_id,
                    bank.get("bank_name"),
                    bank.get("account_name"),
                    bank.get("account_number"),
                    bank.get("ifsc_code"),
                    bank.get("is_active", True)
                )

                execute_query(insert_bank_query, insert_bank_params, fetch=False)

    # Update UPI details if provided
    upi_details = merchant_data.get("upi_details")
    if upi_details:
        # First, deactivate all existing UPI details
        deactivate_query = """
        UPDATE merchant_upi_details
        SET is_active = FALSE
        WHERE merchant_id = %s
        """

        execute_query(deactivate_query, (merchant_id,), fetch=False)

        # Then, upsert new UPI details
        if isinstance(upi_details, dict):
            upi_details = [upi_details]

        for upi in upi_details:
            if "id" in upi:
                # Update existing UPI detail
                update_upi_query = """
                UPDATE merchant_upi_details
                SET 
                    upi_id = %s,
                    name = %s,
                    is_active = %s
                WHERE 
                    id = %s AND merchant_id = %s
                """

                update_upi_params = (
                    upi.get("upi_id"),
                    upi.get("name"),
                    upi.get("is_active", True),
                    upi["id"],
                    merchant_id
                )

                execute_query(update_upi_query, update_upi_params, fetch=False)
            else:
                # Insert new UPI detail
                insert_upi_query = """
                INSERT INTO merchant_upi_details (
                    merchant_id, upi_id, name, is_active
                ) VALUES (
                    %s, %s, %s, %s
                )
                """

                insert_upi_params = (
                    merchant_id,
                    upi.get("upi_id"),
                    upi.get("name"),
                    upi.get("is_active", True)
                )

                execute_query(insert_upi_query, insert_upi_params, fetch=False)

    # Return updated merchant
    return get_merchant_details(merchant_id)


def regenerate_api_key(merchant_id: str) -> str:
    """
    Regenerate API key for a merchant

    Parameters:
    - merchant_id: Merchant ID

    Returns:
    - New API key
    """
    # Generate new API key
    api_key = generate_api_key()

    # Update merchant
    update_query = """
    UPDATE merchants
    SET 
        api_key = %s
    WHERE 
        id = %s
    """

    execute_query(update_query, (api_key, merchant_id), fetch=False)

    return api_key