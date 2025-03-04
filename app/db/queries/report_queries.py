"""
SQL queries for report operations
"""

# Get total merchants count
GET_TOTAL_MERCHANTS = """
SELECT COUNT(*) as count FROM merchants
"""

# Get active merchants count
GET_ACTIVE_MERCHANTS = """
SELECT COUNT(*) as count FROM merchants WHERE is_active = TRUE
"""

# Get total transactions count
GET_TOTAL_TRANSACTIONS = """
SELECT COUNT(*) as count 
FROM payments 
WHERE created_at >= %s
"""

# Get successful transactions count
GET_SUCCESSFUL_TRANSACTIONS = """
SELECT COUNT(*) as count 
FROM payments 
WHERE status = 'CONFIRMED' AND created_at >= %s
"""

# Get total deposit amount
GET_TOTAL_DEPOSIT = """
SELECT COALESCE(SUM(amount), 0) as total 
FROM payments 
WHERE payment_type = 'DEPOSIT' 
AND status = 'CONFIRMED' 
AND created_at >= %s
"""

# Get total withdrawal amount
GET_TOTAL_WITHDRAWAL = """
SELECT COALESCE(SUM(amount), 0) as total 
FROM payments 
WHERE payment_type = 'WITHDRAWAL' 
AND status = 'CONFIRMED' 
AND created_at >= %s
"""

# Get pending verification count
GET_PENDING_VERIFICATION = """
SELECT COUNT(*) as count 
FROM payments 
WHERE status = 'PENDING'
"""

# Get daily transaction counts
GET_DAILY_TRANSACTIONS = """
SELECT 
    DATE(created_at) as date,
    COUNT(*) as count,
    SUM(CASE WHEN status = 'CONFIRMED' THEN 1 ELSE 0 END) as confirmed
FROM 
    payments
WHERE 
    created_at >= %s
GROUP BY 
    DATE(created_at)
ORDER BY 
    date
"""

# Get merchant transaction counts
GET_MERCHANT_TRANSACTIONS = """
SELECT 
    m.business_name,
    COUNT(p.id) as count,
    SUM(CASE WHEN p.status = 'CONFIRMED' THEN 1 ELSE 0 END) as confirmed
FROM 
    merchants m
LEFT JOIN 
    payments p ON m.id = p.merchant_id AND p.created_at >= %s
GROUP BY 
    m.id, m.business_name
ORDER BY 
    count DESC
LIMIT 10
"""

# Get merchant's total transactions
GET_MERCHANT_TOTAL_TRANSACTIONS = """
SELECT COUNT(*) as count 
FROM payments 
WHERE merchant_id = %s AND created_at >= %s
"""

# Get merchant's successful transactions
GET_MERCHANT_SUCCESSFUL_TRANSACTIONS = """
SELECT COUNT(*) as count 
FROM payments 
WHERE merchant_id = %s AND status = 'CONFIRMED' AND created_at >= %s
"""

# Get merchant's total deposit amount
GET_MERCHANT_TOTAL_DEPOSIT = """
SELECT COALESCE(SUM(amount), 0) as total 
FROM payments 
WHERE merchant_id = %s AND payment_type = 'DEPOSIT' 
AND status = 'CONFIRMED' AND created_at >= %s
"""

# Get merchant's total withdrawal amount
GET_MERCHANT_TOTAL_WITHDRAWAL = """
SELECT COALESCE(SUM(amount), 0) as total 
FROM payments 
WHERE merchant_id = %s AND payment_type = 'WITHDRAWAL' 
AND status = 'CONFIRMED' AND created_at >= %s
"""

# Get merchant's pending verification count
GET_MERCHANT_PENDING_VERIFICATION = """
SELECT COUNT(*) as count 
FROM payments 
WHERE merchant_id = %s AND status = 'PENDING'
"""

# Get merchant's daily transaction counts
GET_MERCHANT_DAILY_TRANSACTIONS = """
SELECT 
    DATE(created_at) as date,
    COUNT(*) as count,
    SUM(CASE WHEN status = 'CONFIRMED' THEN 1 ELSE 0 END) as confirmed
FROM 
    payments
WHERE 
    merchant_id = %s AND created_at >= %s
GROUP BY 
    DATE(created_at)
ORDER BY 
    date
"""

# Get merchant reports with pagination
GET_MERCHANT_REPORTS = """
SELECT 
    p.id, p.reference, p.trxn_hash_key, p.payment_type,
    p.payment_method, p.amount, p.currency, p.status,
    p.utr_number, p.created_at, p.updated_at
FROM 
    payments p
WHERE 
    p.merchant_id = %s
{filters}
ORDER BY 
    p.created_at DESC
LIMIT %s OFFSET %s
"""

# Count merchant reports for pagination
COUNT_MERCHANT_REPORTS = """
SELECT 
    COUNT(*) as count
FROM 
    payments p
WHERE 
    p.merchant_id = %s
{filters}
"""

# Get payments for export
GET_PAYMENTS_EXPORT = """
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

# Update bank statement status
UPDATE_BANK_STATEMENT = """
UPDATE bank_statements
SET 
    processed = TRUE,
    matched_transactions = %s
WHERE 
    id = %s
"""