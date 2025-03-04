"""
SQL queries for merchant operations
"""

# Get all merchants
GET_MERCHANTS = """
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

# Get merchant by ID
GET_MERCHANT = """
SELECT 
    m.id, m.business_name, m.business_type, m.contact_phone,
    m.address, m.api_key, m.is_active, m.callback_url,
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

# Get merchant by API key
GET_MERCHANT_BY_API_KEY = """
SELECT 
    id, business_name, is_active, callback_url, webhook_secret,
    min_deposit, max_deposit, min_withdrawal, max_withdrawal
FROM 
    merchants
WHERE 
    api_key = %s
"""

# Get merchant by user ID
GET_MERCHANT_BY_USER = """
SELECT 
    id, business_name, business_type, contact_phone,
    address, api_key, is_active, callback_url,
    min_deposit, max_deposit, min_withdrawal, max_withdrawal,
    created_at, updated_at
FROM 
    merchants
WHERE 
    user_id = %s
"""

# Get merchant's bank details
GET_MERCHANT_BANK_DETAILS = """
SELECT 
    id, bank_name, account_name, account_number, ifsc_code, is_active
FROM 
    merchant_bank_details
WHERE 
    merchant_id = %s
"""

# Get merchant's UPI details
GET_MERCHANT_UPI_DETAILS = """
SELECT 
    id, upi_id, name, is_active
FROM 
    merchant_upi_details
WHERE 
    merchant_id = %s
"""

# Get merchant's IP whitelist
GET_MERCHANT_IP_WHITELIST = """
SELECT 
    id, ip_address, description
FROM 
    ip_whitelist
WHERE 
    merchant_id = %s
"""

# Get merchant's rate limits
GET_MERCHANT_RATE_LIMITS = """
SELECT 
    id, endpoint, requests_per_minute
FROM 
    rate_limits
WHERE 
    merchant_id = %s
"""

# Check if email exists
CHECK_EMAIL_EXISTS = """
SELECT id FROM users WHERE email = %s
"""

# Create user
CREATE_USER = """
INSERT INTO users (
    email, hashed_password, full_name, is_active, is_superuser
) VALUES (
    %s, %s, %s, TRUE, FALSE
) RETURNING id
"""

# Create merchant
CREATE_MERCHANT = """
INSERT INTO merchants (
    user_id, business_name, business_type, contact_phone, address,
    api_key, callback_url, is_active, min_deposit, max_deposit,
    min_withdrawal, max_withdrawal
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s
) RETURNING id
"""

# Create bank detail
CREATE_BANK_DETAIL = """
INSERT INTO merchant_bank_details (
    merchant_id, bank_name, account_name, account_number, ifsc_code, is_active
) VALUES (
    %s, %s, %s, %s, %s, %s
)
"""

# Create UPI detail
CREATE_UPI_DETAIL = """
INSERT INTO merchant_upi_details (
    merchant_id, upi_id, name, is_active
) VALUES (
    %s, %s, %s, %s
)
"""

# Update merchant
UPDATE_MERCHANT = """
UPDATE merchants
SET 
    {fields},
    updated_at = NOW()
WHERE id = %s
"""

# Deactivate all bank details
DEACTIVATE_BANK_DETAILS = """
UPDATE merchant_bank_details
SET is_active = FALSE
WHERE merchant_id = %s
"""

# Update bank detail
UPDATE_BANK_DETAIL = """
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

# Deactivate all UPI details
DEACTIVATE_UPI_DETAILS = """
UPDATE merchant_upi_details
SET is_active = FALSE
WHERE merchant_id = %s
"""

# Update UPI detail
UPDATE_UPI_DETAIL = """
UPDATE merchant_upi_details
SET 
    upi_id = %s,
    name = %s,
    is_active = %s
WHERE 
    id = %s AND merchant_id = %s
"""

# Regenerate API key
REGENERATE_API_KEY = """
UPDATE merchants
SET 
    api_key = %s
WHERE 
    id = %s
"""

# Check if IP already exists
CHECK_IP_EXISTS = """
SELECT COUNT(*) as count
FROM ip_whitelist
WHERE merchant_id = %s AND ip_address = %s
"""

# Add IP to whitelist
ADD_IP_WHITELIST = """
INSERT INTO ip_whitelist (
    merchant_id, ip_address, description
) VALUES (
    %s, %s, %s
) RETURNING id
"""

# Remove IP from whitelist
REMOVE_IP_WHITELIST = """
DELETE FROM ip_whitelist
WHERE id = %s AND merchant_id = %s
RETURNING ip_address
"""

# Upsert rate limit
UPSERT_RATE_LIMIT = """
INSERT INTO rate_limits (
    merchant_id, endpoint, requests_per_minute
) VALUES (
    %s, %s, %s
) ON CONFLICT (merchant_id, endpoint) 
DO UPDATE SET 
    requests_per_minute = EXCLUDED.requests_per_minute,
    updated_at = NOW()
RETURNING id, endpoint, requests_per_minute
"""

# Get user ID for merchant
GET_MERCHANT_USER_ID = """
SELECT user_id FROM merchants WHERE id = %s
"""

# Verify IP whitelist
VERIFY_IP_WHITELIST = """
SELECT 
    COUNT(*) as count
FROM 
    ip_whitelist
WHERE 
    merchant_id = %s AND ip_address = %s
"""