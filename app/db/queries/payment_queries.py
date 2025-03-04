"""
SQL queries for payment operations
"""

# Create payment request
CREATE_PAYMENT = """
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

# Get active UPI details for merchant
GET_MERCHANT_UPI = """
SELECT 
    upi_id, name
FROM 
    merchant_upi_details
WHERE 
    merchant_id = %s AND is_active = TRUE
LIMIT 1
"""

# Check payment request status
CHECK_PAYMENT_STATUS = """
SELECT 
    id as transaction_id, reference, payment_type as type,
    status, remarks, created_at as requested_date
FROM 
    payments
WHERE 
    trxn_hash_key = %s
"""

# Verify payment (mark as CONFIRMED)
VERIFY_PAYMENT = """
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

# Get merchant callback URL
GET_MERCHANT_CALLBACK = """
SELECT 
    callback_url, webhook_secret
FROM 
    merchants
WHERE 
    id = %s
"""

# Mark callback as sent
UPDATE_CALLBACK_SENT = """
UPDATE payments
SET 
    callback_sent = TRUE,
    callback_attempts = 1
WHERE 
    id = %s
"""

# Decline payment
DECLINE_PAYMENT = """
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
"""

# Get pending payments with merchant filter
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
"""

# Create payment link
CREATE_PAYMENT_LINK = """
INSERT INTO payment_links (
    merchant_id, reference, amount, description, status, expires_at
) VALUES (
    %s, %s, %s, %s, 'ACTIVE', %s
) RETURNING id, reference, amount, status, expires_at
"""

# Get payment by ID
GET_PAYMENT_BY_ID = """
SELECT 
    id, merchant_id, reference, trxn_hash_key, payment_type,
    payment_method, amount, currency, status, utr_number,
    account_name, account_number, bank, bank_ifsc,
    created_at, updated_at
FROM 
    payments
WHERE 
    id = %s
"""

# Get payment by reference
GET_PAYMENT_BY_REFERENCE = """
SELECT 
    id, merchant_id, reference, trxn_hash_key, payment_type,
    payment_method, amount, currency, status, utr_number,
    account_name, account_number, bank, bank_ifsc,
    created_at, updated_at
FROM 
    payments
WHERE 
    reference = %s AND merchant_id = %s
"""

# Get payment by UTR number
GET_PAYMENT_BY_UTR = """
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

# Get payments for merchant
GET_MERCHANT_PAYMENTS = """
SELECT 
    id, reference, trxn_hash_key, payment_type, payment_method,
    amount, currency, status, utr_number, created_at, updated_at
FROM 
    payments
WHERE 
    merchant_id = %s
"""

# Get merchant payments with status filter
GET_MERCHANT_PAYMENTS_BY_STATUS = """
SELECT 
    id, reference, trxn_hash_key, payment_type, payment_method,
    amount, currency, status, utr_number, created_at, updated_at
FROM 
    payments
WHERE 
    merchant_id = %s AND status = %s
"""

# Get merchant payments with date range filter
GET_MERCHANT_PAYMENTS_DATE_RANGE = """
SELECT 
    id, reference, trxn_hash_key, payment_type, payment_method,
    amount, currency, status, utr_number, created_at, updated_at
FROM 
    payments
WHERE 
    merchant_id = %s AND created_at BETWEEN %s AND %s
"""

# Get merchant payments with multiple filters
GET_MERCHANT_PAYMENTS_FILTERED = """
SELECT 
    id, reference, trxn_hash_key, payment_type, payment_method,
    amount, currency, status, utr_number, created_at, updated_at
FROM 
    payments
WHERE 
    merchant_id = %s
"""

# Get payments with pagination
GET_PAYMENTS_PAGINATED = """
SELECT 
    id, reference, trxn_hash_key, payment_type, payment_method,
    amount, currency, status, utr_number, created_at, updated_at
FROM 
    payments
WHERE 
    merchant_id = %s
ORDER BY 
    created_at DESC
LIMIT %s OFFSET %s
"""

# Count total payments (for pagination)
COUNT_PAYMENTS = """
SELECT 
    COUNT(*) as count
FROM 
    payments
WHERE 
    merchant_id = %s
"""

# Get failed webhooks
GET_FAILED_WEBHOOKS = """
SELECT 
    p.id, p.merchant_id, p.reference, p.amount, p.status,
    p.callback_attempts, m.callback_url, m.webhook_secret
FROM 
    payments p
JOIN 
    merchants m ON p.merchant_id = m.id
WHERE 
    p.status IN ('CONFIRMED', 'DECLINED')
    AND (p.callback_sent = FALSE OR p.callback_attempts < %s)
    AND p.callback_attempts < %s
LIMIT 50
"""

# Update webhook response
UPDATE_WEBHOOK_RESPONSE = """
UPDATE payments
SET 
    callback_sent = TRUE,
    callback_response = %s,
    callback_attempts = %s
WHERE 
    id = %s
"""

# Update webhook attempts
UPDATE_WEBHOOK_ATTEMPTS = """
UPDATE payments
SET 
    callback_response = %s,
    callback_attempts = %s
WHERE 
    id = %s
"""