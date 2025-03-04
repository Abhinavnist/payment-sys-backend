"""
SQL queries for admin operations
"""

# Get dashboard statistics
# NOTE: Uses the report queries in report_queries.py

# Get pending payments
GET_PENDING_PAYMENTS = """
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
ORDER BY
    p.created_at DESC
"""

# Get pending payments by merchant
GET_PENDING_PAYMENTS_BY_MERCHANT = """
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
    AND p.merchant_id = %s
ORDER BY
    p.created_at DESC
"""

# Verify payment
ADMIN_VERIFY_PAYMENT = """
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

# Decline payment
ADMIN_DECLINE_PAYMENT = """
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

# Get bank statements
GET_BANK_STATEMENTS = """
SELECT 
    bs.id, bs.file_name, bs.processed, bs.matched_transactions,
    bs.uploaded_at, u.full_name as uploaded_by_name
FROM 
    bank_statements bs
JOIN 
    users u ON bs.uploaded_by = u.id
ORDER BY 
    bs.uploaded_at DESC
LIMIT %s OFFSET %s
"""

# Insert bank statement
INSERT_BANK_STATEMENT = """
INSERT INTO bank_statements (
    uploaded_by, file_name, file_path, processed, matched_transactions
) VALUES (
    %s, %s, %s, FALSE, 0
) RETURNING id
"""

# Update bank statement processed status
UPDATE_BANK_STATEMENT = """
UPDATE bank_statements
SET 
    processed = TRUE,
    matched_transactions = %s
WHERE 
    id = %s
"""

# Get export payments
EXPORT_PAYMENTS = """
SELECT 
    p.id, p.reference, p.trxn_hash_key, 
    p.payment_type, p.payment_method, p.amount, 
    p.currency, p.status, p.utr_number,
    p.account_name, p.account_number, p.bank, p.bank_ifsc,
    p.created_at, p.updated_at, 
    p.remarks, m.business_name as merchant_name
FROM 
    payments p
JOIN 
    merchants m ON p.merchant_id = m.id
WHERE 
    1=1
{filters}
ORDER BY 
    p.created_at DESC
"""

# List merchants
ADMIN_LIST_MERCHANTS = """
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

# Get merchant details
ADMIN_GET_MERCHANT = """
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

# Update merchant
ADMIN_UPDATE_MERCHANT = """
UPDATE merchants
SET {fields}, updated_at = NOW()
WHERE id = %s
"""

# Regenerate API key
ADMIN_REGENERATE_API_KEY = """
UPDATE merchants
SET api_key = %s
WHERE id = %s
RETURNING id, api_key
"""

# Check if IP already exists
ADMIN_CHECK_IP_EXISTS = """
SELECT COUNT(*) as count
FROM ip_whitelist
WHERE merchant_id = %s AND ip_address = %s
"""

# Add IP to whitelist
ADMIN_ADD_IP_WHITELIST = """
INSERT INTO ip_whitelist (
    merchant_id, ip_address, description
) VALUES (
    %s, %s, %s
) RETURNING id
"""

# Remove IP from whitelist
ADMIN_REMOVE_IP_WHITELIST = """
DELETE FROM ip_whitelist
WHERE id = %s AND merchant_id = %s
RETURNING ip_address
"""

# Upsert rate limit
ADMIN_UPSERT_RATE_LIMIT = """
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